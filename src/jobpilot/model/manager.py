from __future__ import annotations

import json
import threading
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from jobpilot.model.catalogue import CATALOGUE_VERSION, MODELS, RUNTIMES, get_model, get_runtime
from jobpilot.model.evaluation import ModelEvaluator
from jobpilot.model.hardware import HardwareProbe, ResourcePressureWatcher
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
        self._runtime_devices: dict[str, list[dict[str, Any]]] = {}

    def refresh_hardware(self) -> dict[str, Any]:
        snapshot = self.hardware_probe.capture().to_dict()
        snapshot_id = self.store.record_hardware(snapshot)
        self._runtime_devices = self._discover_installed_runtime_devices()
        return {
            "id": snapshot_id,
            "captured_at": utc_now_text(),
            **snapshot,
            "runtime_devices": dict(self._runtime_devices),
        }

    def snapshot(self) -> dict[str, Any]:
        hardware = self.store.latest_hardware()
        if hardware is None:
            hardware = self.refresh_hardware()
        else:
            if not self._runtime_devices and self.store.list_runtime_installs():
                self._runtime_devices = self._discover_installed_runtime_devices()
            hardware = {**hardware, "runtime_devices": dict(self._runtime_devices)}
        state = self.store.model_state()
        selected_id = state.get("selected_model_install_id")
        review_gate = self.store.review_gate(str(selected_id)) if selected_id else None
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
            "evaluations": self.store.list_evaluations(24),
            "selection": state,
            "review_gate": review_gate,
            "update_check_due": self._update_check_due(state.get("last_catalogue_check_at")),
            "auto_tailoring_enabled": bool(state.get("auto_tailoring_model_install_id")),
            "phase4_review_gate_required": True,
        }

    def install_runtime(self, runtime_id: str, cancel_event: threading.Event) -> dict[str, Any]:
        artifact = get_runtime(runtime_id)
        with self._exclusive_operation("runtime installation"):
            result = self.runtime_installer.install(artifact, cancel_event)
            self._runtime_devices = self._discover_installed_runtime_devices()
            return {**result, "devices": self._runtime_devices.get(runtime_id, [])}

    def install_model(self, model_id: str, cancel_event: threading.Event) -> dict[str, Any]:
        artifact = get_model(model_id)
        hardware = self.store.latest_hardware() or self.refresh_hardware()
        disk_budget = int(hardware["budget"]["model_disk_budget_bytes"])
        if disk_budget < int(artifact.bytes * 1.15):
            raise RuntimeError("insufficient reserved model disk budget for this catalogue model")
        with self._exclusive_operation("model installation"):
            return self.model_installer.install(artifact, cancel_event)

    def evaluate(
        self,
        model_install_id: str,
        runtime_install_id: str,
        cancel_event: threading.Event,
        device_id: str | None = None,
    ) -> dict[str, Any]:
        with self._exclusive_operation("model evaluation"):
            hardware = self.refresh_hardware()
            budget = hardware["budget"]
            pressure_at_start = str(budget["memory_pressure"])
            if pressure_at_start == "critical":
                raise RuntimeError("memory pressure is critical; local inference is blocked until resources recover")
            model_install_id = self._resolve_model_install_id(model_install_id)
            model_path = self.model_installer.require_verified_path(model_install_id)
            runtime_executable = self.runtime_installer.require_verified_executable(runtime_install_id)
            runtime_status = self.runtime_installer.status(runtime_install_id, verify_hash=True)
            runtime_catalogue = get_runtime(str(runtime_status["catalogue_id"]))
            model_row = self.store.model_install(model_install_id)
            if model_row is None:
                raise KeyError(model_install_id)
            model_catalogue = get_model(str(model_row["catalogue_id"]))
            if str(model_row["source_revision"]) != model_catalogue.source_revision:
                raise RuntimeError("installed model revision is no longer the active tested catalogue revision")

            resolved_device = self._resolve_device(runtime_install_id, runtime_catalogue.backend, device_id)
            context_tokens = model_catalogue.tested_context_tokens
            resource_adjustment = "none"
            if pressure_at_start == "constrained":
                context_tokens = max(2048, context_tokens // 2)
                resource_adjustment = "context reduced because memory pressure was constrained at start"
            reference_peak = int(model_catalogue.reference_cpu_peak_rss_bytes or 0)
            evidence_floor = int(reference_peak * (1.0 if context_tokens < model_catalogue.tested_context_tokens else 1.10))
            required_budget = max(int(model_catalogue.bytes * 1.20), evidence_floor)
            if int(budget["model_ram_budget_bytes"]) < required_budget:
                raise RuntimeError(
                    "current reserved RAM budget is below the evidence-backed Phase 3 evaluation floor; "
                    "close other applications or use a smaller future catalogue candidate rather than risking memory exhaustion"
                )
            if cancel_event.is_set():
                raise RuntimeError("model evaluation cancelled")

            self.store.set_model_status(model_install_id, "evaluating")
            self._active_models.add(model_install_id)
            session: LlamaRuntimeSession | None = None
            watcher: ResourcePressureWatcher | None = None
            try:
                cpu = hardware["cpu"]
                logical = max(1, int(cpu.get("logical_cores") or 1))
                threads = max(1, min(logical - 1 if logical > 2 else logical, 8))
                session = LlamaRuntimeSession(
                    executable=runtime_executable,
                    model_path=model_path,
                    backend=runtime_catalogue.backend,
                    context_tokens=context_tokens,
                    threads=threads,
                    device_id=resolved_device,
                )
                watcher = ResourcePressureWatcher(on_critical=session.close)
                with self._runtime_lock:
                    self._current_runtime = session
                watcher.start()
                with session:
                    if session.pid is None:
                        raise RuntimeError("llama.cpp process did not expose a pid")
                    result = self.evaluator.run(
                        session.client,
                        server_pid=session.pid,
                        model_ram_budget_bytes=int(budget["model_ram_budget_bytes"]),
                        cancel_requested=lambda: cancel_event.is_set() or bool(watcher and watcher.critical),
                    )
                pressure_evidence = watcher.stop()
                watcher = None
                resource_pass = bool(result.resource_pass and not pressure_evidence["critical_triggered"])
                overall_pass = bool(
                    result.structured_pass
                    and result.factual_pass
                    and result.tailoring_pass
                    and resource_pass
                )
                configuration = {
                    "backend": runtime_catalogue.backend,
                    "device_id": resolved_device,
                    "context_tokens": context_tokens,
                    "threads": threads,
                    "resource_adjustment": resource_adjustment,
                    "pressure_at_start": pressure_at_start,
                }
                payload = {
                    "id": result.id,
                    "model_install_id": model_install_id,
                    "runtime_install_id": runtime_install_id,
                    "suite_version": result.suite_version,
                    "backend": runtime_catalogue.backend,
                    "device_id": resolved_device,
                    "context_tokens": context_tokens,
                    "elapsed_ms": result.elapsed_ms,
                    "peak_rss_bytes": result.peak_rss_bytes,
                    "generation_tokens_per_second": result.generation_tokens_per_second,
                    "prompt_tokens_per_second": result.prompt_tokens_per_second,
                    "structured_pass": result.structured_pass,
                    "factual_pass": result.factual_pass,
                    "tailoring_pass": result.tailoring_pass,
                    "resource_pass": resource_pass,
                    "overall_pass": overall_pass,
                    "configuration": configuration,
                    "pressure": pressure_evidence,
                    "details": result.details,
                }
                self.store.record_evaluation(payload)
                self.store.set_model_status(
                    model_install_id,
                    "validated" if overall_pass else "failed",
                    None if overall_pass else "controlled Phase 3 evaluation failed",
                )
                return payload
            except Exception as exc:
                retryable_resource_event = cancel_event.is_set() or bool(watcher and watcher.critical)
                self.store.set_model_status(
                    model_install_id,
                    "installed" if retryable_resource_event else "failed",
                    str(exc)[-1000:],
                )
                raise
            finally:
                if watcher is not None:
                    watcher.stop()
                if session is not None:
                    session.close()
                with self._runtime_lock:
                    self._current_runtime = None
                self._active_models.discard(model_install_id)

    def cancel_current(self) -> None:
        with self._runtime_lock:
            session = self._current_runtime
        if session is not None:
            session.close()

    def select_for_phase4_review(self, model_install_id: str) -> dict[str, Any]:
        model_install_id = self._resolve_model_install_id(model_install_id)
        model = self.store.model_install(model_install_id)
        if model is None or model["status"] != "validated":
            raise RuntimeError("only a validated model can be selected")
        best = self.store.best_passing_evaluation(model_install_id)
        if best is None:
            raise RuntimeError("a passing local evaluation is required before selection")
        runtime_id = str(best["runtime_install_id"])
        device_id = str(best["device_id"])
        runtime = self.store.runtime_install(runtime_id)
        if runtime is None or runtime["status"] != "installed":
            raise RuntimeError("the fastest passing configuration no longer has an installed runtime")
        self.model_installer.require_verified_path(model_install_id)
        self.runtime_installer.require_verified_executable(runtime_id)

        previous_state = self.store.model_state()
        existing_gate = self.store.review_gate(model_install_id)
        if (
            previous_state.get("selected_model_install_id") == model_install_id
            and existing_gate.get("approved_distinct_resumes", 0)
            and (
                previous_state.get("selected_runtime_install_id") != runtime_id
                or previous_state.get("selected_device_id") != device_id
            )
        ):
            self.store.invalidate_review_gate(model_install_id, "selected inference configuration changed")
        self.store.select_for_review(model_install_id, runtime_id, device_id)
        return self.snapshot()

    def finalize_after_phase4_review_gate(
        self,
        model_install_id: str,
        *,
        delete_previous_app_managed_weights: bool,
    ) -> dict[str, Any]:
        """Future Phase 4 boundary. Not exposed to the Phase 3 JS bridge."""
        model_install_id = self._resolve_model_install_id(model_install_id)
        model = self.store.model_install(model_install_id)
        if model is None or model["status"] != "validated":
            raise RuntimeError("replacement model is not validated")
        state = self.store.model_state()
        if state.get("selected_model_install_id") != model_install_id:
            raise RuntimeError("replacement model is not the selected Phase 4 review candidate")
        gate = self.store.review_gate(model_install_id)
        if not gate["complete"]:
            raise RuntimeError("five-distinct-resume review gate has not passed")
        evaluation = self.store.best_passing_evaluation(model_install_id)
        if not evaluation:
            raise RuntimeError("replacement model does not have a passing evaluation")
        self.model_installer.require_verified_path(model_install_id)
        if model_install_id in self._active_models:
            raise RuntimeError("replacement model is currently in use")

        previous_id = self.store.activate_after_review_gate(model_install_id)
        if delete_previous_app_managed_weights and previous_id and previous_id != model_install_id:
            previous = self.store.model_install(previous_id)
            if previous is not None:
                if not bool(previous.get("app_managed")):
                    raise RuntimeError("previous model is not app-managed; JobPilot will not delete shared weights")
                previous_path = self.paths.require_model_descendant(self.paths.root / str(previous["model_relpath"]))
                new_path = self.paths.require_model_descendant(self.paths.root / str(model["model_relpath"]))
                version_root = previous_path.parent
                if version_root == new_path.parent:
                    raise RuntimeError("replacement cleanup would target the active model revision")
                self.store.set_cleanup_pending(str(version_root.relative_to(self.paths.root)))
                if previous_id not in self._active_models:
                    self.paths.delete_model_path(version_root)
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
            result: dict[str, Any] = {
                "checked": True,
                "catalogue_version": CATALOGUE_VERSION,
                "checked_at": utc_now_text(),
            }
            latest_runtime = self._fetch_json(
                "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
            ).get("tag_name")
            model_meta = self._fetch_json("https://huggingface.co/api/models/ggml-org/Qwen3-4B-GGUF")
            upstream_revision = model_meta.get("sha")
            pinned_model = MODELS[0]
            result["llama_cpp"] = {
                "pinned_version": RUNTIMES[0].version,
                "latest_release": latest_runtime,
                "same_as_pin": latest_runtime == f"v{RUNTIMES[0].version}",
            }
            result["qwen3_4b"] = {
                "pinned_revision": pinned_model.source_revision,
                "upstream_revision": upstream_revision,
                "same_as_pin": upstream_revision == pinned_model.source_revision,
            }
            result["action"] = "metadata only; a newer revision is never downloaded or trusted automatically"
            self.store.record_catalogue_check(result)
            return result

    def _recommend(self, hardware: dict[str, Any]) -> dict[str, Any]:
        total_ram = int(hardware["memory"]["total_bytes"])
        ram_budget = int(hardware["budget"]["model_ram_budget_bytes"])
        disk_budget = int(hardware["budget"]["model_disk_budget_bytes"])
        pressure = str(hardware["budget"]["memory_pressure"])
        candidates: list[Any] = []
        for model in MODELS:
            reference_floor = int((model.reference_cpu_peak_rss_bytes or model.bytes * 1.2) * 1.10)
            fits = (
                total_ram >= model.min_total_ram_bytes
                and ram_budget >= max(int(model.bytes * 1.20), reference_floor)
                and disk_budget >= int(model.bytes * 1.15)
            )
            if fits:
                candidates.append(model)
        if pressure == "critical" or not candidates:
            return {
                "model_id": None,
                "model_install_id": None,
                "runtime_id": None,
                "reason": "critical memory pressure" if pressure == "critical" else "no tested catalogue model fits the current evidence-backed reserved RAM/disk budget",
                "requires_download_approval": False,
            }
        model = max(candidates, key=lambda item: item.bytes)
        discovered_vulkan = [
            device
            for devices in hardware.get("runtime_devices", {}).values()
            for device in devices
            if str(device.get("id", "")).casefold().startswith("vulkan")
        ]
        return {
            "model_id": model.id,
            "model_install_id": model.install_id,
            "runtime_id": "llama-b10809-win-cpu-x64",
            "alternative_runtime_id": "llama-b10809-win-vulkan-x64" if hardware.get("gpus") else None,
            "discovered_vulkan_devices": [device["id"] for device in discovered_vulkan],
            "reason": (
                "accepted catalogue candidate fits the conservative local budget; CPU is the compatibility baseline. "
                "Vulkan is only considered after the pinned runtime reports a concrete device and that configuration passes the same evaluation."
            ),
            "requires_download_approval": True,
            "must_pass_device_evaluation": True,
            "phase4_five_resume_gate_required": True,
        }

    def _model_catalogue_status(self, item: dict[str, Any]) -> dict[str, Any]:
        row = self.store.find_model_install(str(item["id"]), str(item["source_revision"]))
        hardware = self.store.latest_hardware()
        suitability = "unknown"
        if hardware:
            model = get_model(str(item["id"]))
            ram = int(hardware["budget"]["model_ram_budget_bytes"])
            disk = int(hardware["budget"]["model_disk_budget_bytes"])
            reference_floor = int((model.reference_cpu_peak_rss_bytes or model.bytes * 1.2) * 1.10)
            suitability = "fits" if ram >= max(int(model.bytes * 1.2), reference_floor) and disk >= int(model.bytes * 1.15) else "insufficient_reserved_budget"
        return {**item, "install": row, "suitability": suitability}

    def _runtime_catalogue_status(self, item: dict[str, Any]) -> dict[str, Any]:
        runtime_id = str(item["id"])
        row = self.store.runtime_install(runtime_id)
        return {**item, "install": row, "devices": self._runtime_devices.get(runtime_id, [])}

    def _discover_installed_runtime_devices(self) -> dict[str, list[dict[str, Any]]]:
        discovered: dict[str, list[dict[str, Any]]] = {}
        for runtime in self.store.list_runtime_installs():
            if runtime.get("status") != "installed":
                continue
            runtime_id = str(runtime["id"])
            try:
                result = self.runtime_installer.list_devices(runtime_id)
            except Exception:
                continue
            if result.get("ok"):
                discovered[runtime_id] = list(result.get("devices", []))
        return discovered

    def _resolve_device(self, runtime_id: str, backend: str, requested: str | None) -> str:
        if backend == "cpu":
            if requested not in (None, "", "none"):
                raise RuntimeError("CPU runtime configuration must use device 'none'")
            return "none"
        result = self.runtime_installer.list_devices(runtime_id)
        if not result.get("ok"):
            raise RuntimeError("llama.cpp could not enumerate devices for the selected runtime")
        devices = [device for device in result.get("devices", []) if str(device.get("id", "")).casefold().startswith("vulkan")]
        ids = {str(device["id"]) for device in devices}
        requested_id = (requested or "").strip()
        if requested_id:
            if requested_id not in ids:
                raise RuntimeError("requested Vulkan device was not reported by the installed llama.cpp runtime")
            return requested_id
        if len(ids) == 1:
            return next(iter(ids))
        if not ids:
            raise RuntimeError("installed Vulkan runtime reported no usable Vulkan device")
        raise RuntimeError("multiple Vulkan devices are available; choose an explicit discovered device before evaluation")

    def _resolve_model_install_id(self, value: str) -> str:
        if self.store.model_install(value) is not None:
            return value
        try:
            artifact = get_model(value)
        except KeyError:
            raise KeyError(value) from None
        if self.store.model_install(artifact.install_id) is None:
            raise KeyError(artifact.install_id)
        return artifact.install_id

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
