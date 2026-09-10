from __future__ import annotations

import json
import threading
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from jobpilot.model.catalogue import CATALOGUE_VERSION, MODELS, RUNTIMES, get_model, get_runtime
from jobpilot.model.evaluation import ModelEvaluator
from jobpilot.model.hardware import HardwareProbe
from jobpilot.model.runtime import LlamaRuntimeSession
from jobpilot.model.store import ModelStore
from jobpilot.model.tooling import ModelInstallService, RuntimeInstallService
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.storage.database import Database, utc_now_text


class ModelManager:
    """Owns local model resources. No operation here enables employer automation."""

    def __init__(self, paths: ManagedPaths, database: Database) -> None:
        self.paths = paths
        self.store = ModelStore(database)
        self.hardware_probe = HardwareProbe(paths.root)
        self.runtime_installer = RuntimeInstallService(paths, self.store)
        self.model_installer = ModelInstallService(paths, self.store)
        self.evaluator = ModelEvaluator()
        self._operation_lock = threading.Lock()
        self._runtime_lock = threading.RLock()
        self._current_runtime: LlamaRuntimeSession | None = None
        self._active_models: set[str] = set()

    def refresh_hardware(self) -> dict[str, Any]:
        snapshot = self.hardware_probe.capture().to_dict()
        snapshot_id = self.store.record_hardware(snapshot)
        return {"id": snapshot_id, "captured_at": utc_now_text(), **snapshot}

    def snapshot(self) -> dict[str, Any]:
        hardware = self.store.latest_hardware()
        if hardware is None:
            hardware = self.refresh_hardware()
        state = self.store.model_state()
        return {
            "catalogue_version": CATALOGUE_VERSION,
            "hardware": hardware,
            "recommendation": self._recommend(hardware),
            "catalogue": {
                "models": [self._model_catalogue_status(item.to_dict()) for item in MODELS],
                "runtimes": [self._runtime_catalogue_status(item.to_dict()) for item in RUNTIMES],
            },
            "runtime_installs": self.store.list_runtime_installs(),
            "model_installs": self.store.list_model_installs(),
            "evaluations": self.store.list_evaluations(12),
            "selection": state,
            "update_check_due": self._update_check_due(state.get("last_catalogue_check_at")),
            "auto_tailoring_enabled": bool(state.get("auto_tailoring_model_install_id")),
            "phase4_review_gate_required": True,
        }

    def install_runtime(self, runtime_id: str, cancel_event: threading.Event) -> dict[str, Any]:
        artifact = get_runtime(runtime_id)
        with self._exclusive_operation("runtime installation"):
            return self.runtime_installer.install(artifact, cancel_event)

    def install_model(self, model_id: str, cancel_event: threading.Event) -> dict[str, Any]:
        artifact = get_model(model_id)
        hardware = self.store.latest_hardware() or self.refresh_hardware()
        disk_budget = int(hardware["budget"]["model_disk_budget_bytes"])
        if disk_budget < int(artifact.display_bytes * 1.15):
            raise RuntimeError("insufficient reserved model disk budget for this catalogue model")
        with self._exclusive_operation("model installation"):
            return self.model_installer.install(artifact, cancel_event)

    def evaluate(
        self,
        model_install_id: str,
        runtime_install_id: str,
        cancel_event: threading.Event,
    ) -> dict[str, Any]:
        with self._exclusive_operation("model evaluation"):
            hardware = self.refresh_hardware()
            budget = hardware["budget"]
            if budget["memory_pressure"] == "critical":
                raise RuntimeError("memory pressure is critical; local inference is blocked until resources recover")
            model_path = self.model_installer.require_verified_path(model_install_id)
            runtime_executable = self.runtime_installer.require_verified_executable(runtime_install_id)
            runtime_status = self.runtime_installer.status(runtime_install_id, verify_hash=True)
            runtime_catalogue = get_runtime(str(runtime_status["catalogue_id"]))
            model_row = self.store.model_install(model_install_id)
            if model_row is None:
                raise KeyError(model_install_id)
            model_catalogue = get_model(str(model_row["catalogue_id"]))
            if int(budget["model_ram_budget_bytes"]) < int(model_catalogue.display_bytes * 1.20):
                raise RuntimeError("current reserved RAM budget is too small for a safe evaluation")
            if cancel_event.is_set():
                raise RuntimeError("model evaluation cancelled")
            self.store.set_model_status(model_install_id, "evaluating")
            self._active_models.add(model_install_id)
            try:
                cpu = hardware["cpu"]
                logical = max(1, int(cpu.get("logical_cores") or 1))
                threads = max(1, min(logical - 1 if logical > 2 else logical, 8))
                session = LlamaRuntimeSession(
                    executable=runtime_executable,
                    model_path=model_path,
                    backend=runtime_catalogue.backend,
                    context_tokens=model_catalogue.tested_context_tokens,
                    threads=threads,
                )
                with self._runtime_lock:
                    self._current_runtime = session
                with session:
                    if session.pid is None:
                        raise RuntimeError("llama.cpp process did not expose a pid")
                    result = self.evaluator.run(
                        session.client,
                        server_pid=session.pid,
                        model_ram_budget_bytes=int(budget["model_ram_budget_bytes"]),
                        cancel_requested=cancel_event.is_set,
                    )
                payload = {
                    "id": result.id,
                    "model_install_id": model_install_id,
                    "runtime_install_id": runtime_install_id,
                    "suite_version": result.suite_version,
                    "backend": runtime_catalogue.backend,
                    "context_tokens": model_catalogue.tested_context_tokens,
                    "elapsed_ms": result.elapsed_ms,
                    "peak_rss_bytes": result.peak_rss_bytes,
                    "structured_pass": result.structured_pass,
                    "factual_pass": result.factual_pass,
                    "tailoring_pass": result.tailoring_pass,
                    "resource_pass": result.resource_pass,
                    "overall_pass": result.overall_pass,
                    "details": result.details,
                }
                self.store.record_evaluation(payload)
                self.store.set_model_status(model_install_id, "validated" if result.overall_pass else "failed", None if result.overall_pass else "controlled Phase 3 evaluation failed")
                return payload
            except Exception as exc:
                self.store.set_model_status(model_install_id, "failed", str(exc)[-1000:])
                raise
            finally:
                with self._runtime_lock:
                    self._current_runtime = None
                self._active_models.discard(model_install_id)

    def cancel_current(self) -> None:
        with self._runtime_lock:
            session = self._current_runtime
        if session is not None:
            session.close()

    def select_for_phase4_review(self, model_install_id: str, runtime_install_id: str) -> dict[str, Any]:
        model = self.store.model_install(model_install_id)
        runtime = self.store.runtime_install(runtime_install_id)
        if model is None or runtime is None:
            raise KeyError("model/runtime install is missing")
        if model["status"] != "validated" or runtime["status"] != "installed":
            raise RuntimeError("only a validated model with an installed runtime can be selected")
        evaluation = self.store.latest_evaluation(model_install_id, runtime_install_id)
        if not evaluation or not evaluation["overall_pass"]:
            raise RuntimeError("a passing local evaluation is required before selection")
        self.model_installer.require_verified_path(model_install_id)
        self.runtime_installer.require_verified_executable(runtime_install_id)
        self.store.select_for_review(model_install_id, runtime_install_id)
        return self.snapshot()

    def finalize_after_phase4_review_gate(
        self,
        model_install_id: str,
        *,
        review_gate_passed: bool,
        delete_previous_app_managed_weights: bool,
    ) -> dict[str, Any]:
        """Future Phase 4 call boundary. Deliberately not exposed to the Phase 3 JS bridge."""
        if not review_gate_passed:
            raise RuntimeError("five-resume review gate has not passed")
        model = self.store.model_install(model_install_id)
        if model is None or model["status"] != "validated":
            raise RuntimeError("replacement model is not validated")
        evaluation = self.store.latest_evaluation(model_install_id)
        if not evaluation or not evaluation["overall_pass"]:
            raise RuntimeError("replacement model does not have a passing evaluation")
        if model_install_id in self._active_models:
            raise RuntimeError("replacement model is currently in use")

        previous_id = self.store.activate_after_review_gate(model_install_id)
        if delete_previous_app_managed_weights and previous_id and previous_id != model_install_id:
            previous = self.store.model_install(previous_id)
            if previous is not None:
                previous_path = self.paths.root / str(previous["model_relpath"])
                safe_path = self.paths.require_model_descendant(previous_path)
                if previous_id in self._active_models:
                    self.store.set_cleanup_pending(str(safe_path.relative_to(self.paths.root)))
                else:
                    model_root = safe_path.parent
                    self.paths.delete_model_path(model_root)
                    self.store.set_model_status(previous_id, "retired")
                    self.store.set_cleanup_pending(None)
        return self.snapshot()

    def rollback_after_activation_failure(self, failed_model_install_id: str) -> dict[str, Any]:
        """Future recovery boundary; not exposed to Phase 3 UI."""
        if failed_model_install_id in self._active_models:
            self.cancel_current()
        state = self.store.model_state()
        previous_id = state.get("previous_auto_model_install_id")
        if not previous_id:
            raise RuntimeError("no previous validated model is available for rollback")
        previous = self.store.model_install(str(previous_id))
        if previous is None or previous["status"] != "validated":
            raise RuntimeError("previous model is not validated")
        self.model_installer.require_verified_path(str(previous_id))
        restored = self.store.rollback_auto_model(failed_model_install_id)
        self.store.set_cleanup_pending(None)
        return {"restored_model_install_id": restored, "failed_model_install_id": failed_model_install_id}

    def check_for_updates(self) -> dict[str, Any]:
        state = self.store.model_state()
        if not self._update_check_due(state.get("last_catalogue_check_at")):
            raw = state.get("last_catalogue_check_json")
            return json.loads(raw) if raw else {"checked": False, "reason": "weekly check not due"}
        with self._exclusive_operation("catalogue update check"):
            result: dict[str, Any] = {"checked": True, "catalogue_version": CATALOGUE_VERSION, "checked_at": utc_now_text()}
            result["llama_cpp"] = self._fetch_json("https://api.github.com/repos/ggml-org/llama.cpp/releases/latest").get("tag_name")
            model_meta = self._fetch_json("https://huggingface.co/api/models/ggml-org/Qwen3.5-0.8B-GGUF")
            result["qwen3_5_0_8b_upstream_revision"] = model_meta.get("sha")
            self.store.record_catalogue_check(result)
            return result

    def _recommend(self, hardware: dict[str, Any]) -> dict[str, Any]:
        total_ram = int(hardware["memory"]["total_bytes"])
        ram_budget = int(hardware["budget"]["model_ram_budget_bytes"])
        disk_budget = int(hardware["budget"]["model_disk_budget_bytes"])
        pressure = str(hardware["budget"]["memory_pressure"])
        candidates: list[tuple[int, Any]] = []
        for model in MODELS:
            fits = (
                total_ram >= model.min_total_ram_bytes
                and ram_budget >= int(model.display_bytes * 1.20)
                and disk_budget >= int(model.display_bytes * 1.15)
            )
            if fits:
                score = (2 if model.tier == "preferred" else 1) * 100 + model.display_bytes // 1_000_000
                candidates.append((score, model))
        if pressure == "critical" or not candidates:
            return {
                "model_id": None,
                "runtime_id": None,
                "reason": "critical memory pressure" if pressure == "critical" else "no catalogue model fits the current reserved RAM/disk budget",
                "requires_download_approval": False,
            }
        model = max(candidates, key=lambda item: item[0])[1]
        known_gpu_vram = [
            int(gpu["total_vram_bytes"])
            for gpu in hardware.get("gpus", [])
            if gpu.get("total_vram_bytes") is not None and "vulkan" in gpu.get("backend_candidates", [])
        ]
        runtime_id = "llama-b10809-win-vulkan-x64" if any(vram >= int(model.display_bytes * 1.20) for vram in known_gpu_vram) else "llama-b10809-win-cpu-x64"
        return {
            "model_id": model.id,
            "runtime_id": runtime_id,
            "reason": "highest-tier catalogue candidate that fits the conservative local resource budget",
            "requires_download_approval": True,
            "must_pass_device_evaluation": True,
            "phase4_five_resume_gate_required": True,
        }

    def _model_catalogue_status(self, item: dict[str, Any]) -> dict[str, Any]:
        row = self.store.model_install(str(item["id"]))
        return {**item, "install": row}

    def _runtime_catalogue_status(self, item: dict[str, Any]) -> dict[str, Any]:
        row = self.store.runtime_install(str(item["id"]))
        return {**item, "install": row}

    @staticmethod
    def _update_check_due(last_checked: object) -> bool:
        if not last_checked:
            return True
        try:
            parsed = datetime.fromisoformat(str(last_checked).replace("Z", "+00:00"))
        except ValueError:
            return True
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - parsed >= timedelta(days=7)

    @staticmethod
    def _fetch_json(url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers={"User-Agent": "jobpilot-local/phase3"})
        with urllib.request.urlopen(request, timeout=12) as response:
            value = json.loads(response.read().decode("utf-8"))
        if not isinstance(value, dict):
            raise RuntimeError("update endpoint returned unexpected data")
        return value

    class _ExclusiveOperation:
        def __init__(self, lock: threading.Lock, label: str) -> None:
            self.lock = lock
            self.label = label

        def __enter__(self) -> None:
            if not self.lock.acquire(blocking=False):
                raise RuntimeError(f"another local-model operation is already running; cannot start {self.label}")

        def __exit__(self, exc_type, exc, tb) -> None:
            self.lock.release()

    def _exclusive_operation(self, label: str) -> "ModelManager._ExclusiveOperation":
        return self._ExclusiveOperation(self._operation_lock, label)
