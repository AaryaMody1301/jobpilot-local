from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Any, Mapping

from jobpilot.app.sample_worker import SampleLifecycleWorker
from jobpilot.domain.states import SESSION_MACHINE, SessionState
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.settings import TargetingSettings
from jobpilot.storage.database import Database


TARGETING_SETTING_KEY = "targeting"


class ApplicationController:
    """Thread-safe application lifecycle and local persistence boundary."""

    def __init__(
        self,
        paths: ManagedPaths,
        migrations_dir: Path,
        *,
        sample_item_seconds: float = 0.4,
    ) -> None:
        self.paths = paths
        self.paths.create_all_roots()
        self.database = Database(paths.database_file, migrations_dir)
        self.database.apply_migrations()
        self.recovery = self.database.recover_interrupted_work()
        self.database.seed_sample_work()

        existing = self.database.get_json_setting(TARGETING_SETTING_KEY)
        self._targeting = TargetingSettings.from_mapping(existing) if existing else TargetingSettings()
        if existing is None:
            self.database.set_json_setting(TARGETING_SETTING_KEY, self._targeting.to_dict())

        self.session_id = str(uuid.uuid4())
        self.database.create_runtime_session(self.session_id)
        self._state = SessionState.IDLE
        self._sample_item_seconds = sample_item_seconds
        self._worker: SampleLifecycleWorker | None = None
        self._closed = False
        self._lock = threading.RLock()
        self.database.record_foundation_activity(self.session_id, "launch", "Desktop session opened idle; no work scheduled")

    @property
    def state(self) -> SessionState:
        with self._lock:
            return self._state

    def start(self) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            if self._state is SessionState.RUNNING:
                return self.snapshot()
            SESSION_MACHINE.require_transition(self._state, SessionState.RUNNING)
            if self._worker is None or not self._worker.status().alive:
                self._worker = SampleLifecycleWorker(
                    self.database,
                    self.session_id,
                    item_seconds=self._sample_item_seconds,
                )
                self._worker.start()
            else:
                self._worker.resume()
            self._state = SessionState.RUNNING
            self.database.set_runtime_session_state(self.session_id, self._state)
            self.database.record_foundation_activity(self.session_id, "start", "Sample lifecycle work started or resumed")
            return self.snapshot()

    def pause(self) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            if self._state is SessionState.PAUSED:
                return self.snapshot()
            SESSION_MACHINE.require_transition(self._state, SessionState.PAUSED)
            if self._worker is not None:
                self._worker.pause()
            self._state = SessionState.PAUSED
            self.database.set_runtime_session_state(self.session_id, self._state)
            self.database.record_foundation_activity(self.session_id, "pause", "No new sample work will be scheduled")
            return self.snapshot()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            if self._state is SessionState.IDLE:
                return self.snapshot()
            SESSION_MACHINE.require_transition(self._state, SessionState.STOPPING)
            self._state = SessionState.STOPPING
            self.database.set_runtime_session_state(self.session_id, self._state)
            if self._worker is not None:
                self._worker.stop()
            self._worker = None
            self.database.requeue_owned_sample_work(self.session_id)
            SESSION_MACHINE.require_transition(self._state, SessionState.IDLE)
            self._state = SessionState.IDLE
            self.database.set_runtime_session_state(self.session_id, self._state)
            self.database.record_foundation_activity(self.session_id, "stop", "Sample lifecycle work stopped; app remains open")
            return self.snapshot()

    def save_targeting(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        targeting = TargetingSettings.from_mapping(raw)
        with self._lock:
            self._require_open()
            self.database.set_json_setting(TARGETING_SETTING_KEY, targeting.to_dict())
            self._targeting = targeting
            self.database.record_foundation_activity(self.session_id, "settings", "Targeting settings saved locally")
            return self.snapshot()

    def reset_sample_work(self) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            if self._state is not SessionState.IDLE:
                raise RuntimeError("sample work can only be reset while idle")
            self.database.reset_sample_work()
            self.database.record_foundation_activity(self.session_id, "reset", "Sample lifecycle items reset")
            return self.snapshot()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            if self._state is not SessionState.CLOSING:
                SESSION_MACHINE.require_transition(self._state, SessionState.CLOSING)
                self._state = SessionState.CLOSING
                self.database.set_runtime_session_state(self.session_id, self._state)
            if self._worker is not None:
                self._worker.stop()
            self._worker = None
            self.database.requeue_owned_sample_work(self.session_id)
            SESSION_MACHINE.require_transition(self._state, SessionState.EXITED)
            self._state = SessionState.EXITED
            self.database.record_foundation_activity(self.session_id, "close", "Desktop session exited cleanly")
            self.database.finish_runtime_session(self.session_id)
            self.database.close()
            self._closed = True

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            worker_status = self._worker.status() if self._worker is not None else None
            sample = self.database.list_sample_work()
            counts = {"pending": 0, "running": 0, "done": 0, "failed": 0, "blocked": 0}
            for item in sample:
                state = str(item["state"])
                counts[state] = counts.get(state, 0) + 1
            return {
                "phase": 1,
                "development_mode": True,
                "session_id": self.session_id,
                "session_state": self._state.value,
                "worker_alive": bool(worker_status and worker_status.alive),
                "target_confirmed_applications": 50,
                "confirmed_applications_today": 0,
                "targeting": self._targeting.to_dict(),
                "sample_work": sample,
                "sample_counts": counts,
                "recovery": dict(self.recovery),
                "activity": self.database.recent_foundation_activity(12),
                "data_root": str(self.paths.root),
            }

    def _require_open(self) -> None:
        if self._closed or self._state is SessionState.EXITED:
            raise RuntimeError("application controller is closed")
