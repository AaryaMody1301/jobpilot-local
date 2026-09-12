from __future__ import annotations

import threading
from typing import Any, Mapping, Sequence

from jobpilot.model.catalogue import get_runtime
from jobpilot.model.hardware import ResourcePressureWatcher
from jobpilot.model.llama_server import StructuredJsonResponse
from jobpilot.model.manager import ModelManager
from jobpilot.model.runtime import LlamaRuntimeSession


class Phase4ModelManager(ModelManager):
    """Phase 3 model manager plus one fail-closed selected-model inference path."""

    def infer_selected_structured(
        self,
        messages: Sequence[Mapping[str, str]],
        schema: Mapping[str, Any],
        cancel_event: threading.Event,
        *,
        max_tokens: int = 900,
    ) -> dict[str, Any]:
        with self._exclusive_operation("resume tailoring"):
            state = self.store.model_state()
            model_install_id = str(state.get("selected_model_install_id") or "")
            runtime_install_id = str(state.get("selected_runtime_install_id") or "")
            device_id = str(state.get("selected_device_id") or "")
            if not model_install_id or not runtime_install_id or not device_id:
                raise RuntimeError("select a validated local model/configuration before tailoring")

            model = self.store.model_install(model_install_id)
            if model is None or model.get("status") != "validated":
                raise RuntimeError("selected local model is not validated")
            runtime = self.store.runtime_install(runtime_install_id)
            if runtime is None or runtime.get("status") != "installed":
                raise RuntimeError("selected llama.cpp runtime is not installed")
            evaluation = self.store.best_passing_evaluation(model_install_id)
            if evaluation is None:
                raise RuntimeError("selected local model has no passing Phase 3 evaluation")
            if str(evaluation["runtime_install_id"]) != runtime_install_id or str(evaluation["device_id"]) != device_id:
                raise RuntimeError("selected inference configuration no longer matches its passing evaluation")

            hardware = self.refresh_hardware()
            budget = hardware["budget"]
            if str(budget["memory_pressure"]) == "critical":
                raise RuntimeError("memory pressure is critical; resume generation is paused until resources recover")
            measured_peak = int(evaluation.get("peak_rss_bytes") or 0)
            if measured_peak and int(budget["model_ram_budget_bytes"]) < int(measured_peak * 1.05):
                raise RuntimeError("reserved RAM is below the measured passing configuration; close other applications before tailoring")
            if cancel_event.is_set():
                raise RuntimeError("resume tailoring cancelled")

            model_path = self.model_installer.require_verified_path(model_install_id)
            executable = self.runtime_installer.require_verified_executable(runtime_install_id)
            runtime_catalogue = get_runtime(str(runtime["catalogue_id"]))
            if runtime_catalogue.backend == "cpu" and device_id != "none":
                raise RuntimeError("selected CPU configuration must use device none")
            if runtime_catalogue.backend == "vulkan":
                available = {str(item["id"]) for item in self.runtime_installer.list_devices(runtime_install_id).get("devices", [])}
                if device_id not in available:
                    raise RuntimeError("selected Vulkan device is no longer reported by the verified runtime")

            configuration = dict(evaluation.get("configuration") or {})
            context_tokens = int(evaluation.get("context_tokens") or configuration.get("context_tokens") or 4096)
            threads = int(configuration.get("threads") or 1)
            session = LlamaRuntimeSession(
                executable=executable,
                model_path=model_path,
                backend=runtime_catalogue.backend,
                context_tokens=context_tokens,
                threads=max(1, threads),
                device_id=device_id,
            )
            watcher = ResourcePressureWatcher(on_critical=session.close)
            self._active_models.add(model_install_id)
            with self._runtime_lock:
                self._current_runtime = session
            try:
                watcher.start()
                with session:
                    if cancel_event.is_set():
                        raise RuntimeError("resume tailoring cancelled")
                    response: StructuredJsonResponse = session.client.request_structured(
                        messages,
                        schema,
                        timeout_seconds=120,
                        max_tokens=max_tokens,
                    )
                pressure = watcher.stop()
                if cancel_event.is_set():
                    raise RuntimeError("resume tailoring cancelled")
                if pressure["critical_triggered"]:
                    raise RuntimeError("local inference was cancelled because memory pressure became critical")
                return {
                    "value": response.value,
                    "usage": response.usage,
                    "timings": response.timings,
                    "model_install_id": model_install_id,
                    "runtime_install_id": runtime_install_id,
                    "device_id": device_id,
                    "context_tokens": context_tokens,
                    "pressure": pressure,
                }
            finally:
                watcher.stop()
                session.close()
                with self._runtime_lock:
                    self._current_runtime = None
                self._active_models.discard(model_install_id)
