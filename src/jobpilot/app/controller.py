from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Any, Mapping

from jobpilot.app.sample_worker import SampleLifecycleWorker
from jobpilot.domain.states import SESSION_MACHINE, SessionState
from jobpilot.resume.baseline import ResumeBaselineService
from jobpilot.resume.documents import DocumentWorkspace
from jobpilot.resume.store import FACT_CATEGORIES, ResumeStore
from jobpilot.resume.tooling import TectonicInstallService
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.settings import TargetingSettings
from jobpilot.storage.database import Database


TARGETING_SETTING_KEY = "targeting"


class ApplicationController:
    """Thread-safe application lifecycle, onboarding, and local persistence boundary."""

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

        self.resume_store = ResumeStore(self.database, self.paths.root)
        self.documents = DocumentWorkspace(self.paths, self.resume_store)
        self.baselines = ResumeBaselineService(self.paths, self.resume_store)
        self.tectonic = TectonicInstallService(self.paths)

        self.session_id = str(uuid.uuid4())
        self.database.create_runtime_session(self.session_id)
        self._state = SessionState.IDLE
        self._sample_item_seconds = sample_item_seconds
        self._worker: SampleLifecycleWorker | None = None
        self._closed = False
        self._lock = threading.RLock()
        self._onboarding_busy: str | None = None
        self._onboarding_cancel: threading.Event | None = None
        self._onboarding_done = threading.Event()
        self._onboarding_done.set()
        self.database.record_foundation_activity(self.session_id, "launch", "Desktop session opened idle; no work scheduled")

    @property
    def state(self) -> SessionState:
        with self._lock:
            return self._state

    def start(self) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            if self._onboarding_busy is not None:
                raise RuntimeError(f"finish or cancel {self._onboarding_busy} before starting the session")
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
            self._require_idle_onboarding()
            self.database.reset_sample_work()
            self.database.record_foundation_activity(self.session_id, "reset", "Sample lifecycle items reset")
            return self.snapshot()

    def import_master_resume(self, source: Path) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            result = self.documents.import_master(source)
            self.database.record_foundation_activity(
                self.session_id,
                "resume_import",
                f"Imported immutable master resume {result['document_id']}",
            )
            return self.snapshot()

    def import_supporting_document(self, source: Path) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            result = self.documents.import_supporting(source)
            self.database.record_foundation_activity(
                self.session_id,
                "supporting_import",
                f"Registered immutable supporting source {result['document_id']}",
            )
            return self.snapshot()

    def install_tectonic(self) -> dict[str, Any]:
        with self._lock:
            cancel = self._begin_onboarding_operation("Tectonic installation")
        try:
            status = self.tectonic.install(cancel)
            with self._lock:
                self._require_open()
                self.database.record_foundation_activity(
                    self.session_id,
                    "tectonic_install",
                    f"Installed checksum-verified Tectonic {status.get('version')}",
                )
        finally:
            with self._lock:
                self._end_onboarding_operation()
        with self._lock:
            return self.snapshot()

    def compile_master_resume(self, *, allow_package_downloads: bool) -> dict[str, Any]:
        with self._lock:
            cancel = self._begin_onboarding_operation("resume baseline compilation")
        try:
            self.baselines.compile_active(allow_package_downloads=allow_package_downloads, cancel_event=cancel)
            with self._lock:
                self._require_open()
                self.database.record_foundation_activity(
                    self.session_id,
                    "resume_compile",
                    "Compiled immutable resume baseline" + (" with explicit package-cache network permission" if allow_package_downloads else " from cached packages only"),
                )
        except Exception as exc:
            with self._lock:
                if not self._closed:
                    self.database.record_foundation_activity(self.session_id, "resume_compile_failed", str(exc)[-1000:])
            raise
        finally:
            with self._lock:
                self._end_onboarding_operation()
        with self._lock:
            return self.snapshot()

    def set_template_region_editable(self, region_id: str, editable: bool) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            self.resume_store.set_region_editable(region_id, bool(editable))
            return self.snapshot()

    def confirm_template_map(self) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            master = self.resume_store.get_active_master()
            if master is None:
                raise RuntimeError("import a master resume before confirming the template map")
            self.resume_store.confirm_template_map(str(master["id"]))
            self.database.record_foundation_activity(self.session_id, "template_map", "Confirmed editable resume region mapping")
            return self.snapshot()

    def create_fact(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            document_id = str(raw.get("source_document_id", "")).strip()
            locator = str(raw.get("locator", "")).strip()
            if not locator or len(locator) > 300:
                raise ValueError("source locator must contain 1-300 characters")
            document = self.resume_store.get_document(document_id)
            if document is None:
                raise KeyError(document_id)
            self.resume_store.create_fact(
                value=str(raw.get("value", "")),
                category=str(raw.get("category", "other")),
                source_document_id=document_id,
                source_ref={
                    "kind": "user_locator",
                    "locator": locator,
                    "source_sha256": document["sha256"],
                },
            )
            return self.snapshot()

    def revise_fact(self, fact_id: str, value: str, category: str) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            self.resume_store.revise_fact(fact_id, value=value, category=category)
            return self.snapshot()

    def set_fact_status(self, fact_id: str, status: str) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            if status == "approved":
                fact = next((item for item in self.resume_store.list_facts() if item["id"] == fact_id), None)
                if fact is None:
                    raise KeyError(fact_id)
                source = self.resume_store.get_document(str(fact["source_document_id"]))
                if source is None:
                    raise RuntimeError("fact source document no longer exists")
                integrity = self.documents.verify_document(source)
                if integrity != "verified":
                    raise RuntimeError("cannot approve a fact whose source document failed integrity verification")
            self.resume_store.set_fact_status(fact_id, status)
            return self.snapshot()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            cancel = self._onboarding_cancel
            if cancel is not None:
                cancel.set()
        if cancel is not None:
            self._onboarding_done.wait()
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
                "phase": 2,
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
                "onboarding_busy": self._onboarding_busy,
                "resume": self._resume_snapshot(),
            }

    def _resume_snapshot(self) -> dict[str, Any]:
        master = self.resume_store.get_active_master()
        integrity = "missing"
        baseline = None
        regions: list[dict[str, Any]] = []
        mapping_status = "missing"
        if master is not None:
            integrity = self.documents.verify_document(master)
            master = self.resume_store.get_document(str(master["id"])) or master
            baseline = self.resume_store.get_baseline(str(master["id"]))
            regions = self.resume_store.list_template_regions(str(master["id"]))
            mapping_status = self.resume_store.template_map_status(str(master["id"]))

        active_master_id = str(master["id"]) if master is not None else None
        facts: list[dict[str, Any]] = []
        for fact in self.resume_store.list_facts():
            source = self.resume_store.get_document(str(fact["source_document_id"]))
            if source is None:
                continue
            if str(source["id"]) == active_master_id or str(source.get("kind")) == "supporting":
                facts.append(fact)

        fact_counts = {"candidate": 0, "approved": 0, "rejected": 0}
        for fact in facts:
            status = str(fact["current_status"])
            fact_counts[status] = fact_counts.get(status, 0) + 1
        ready = bool(
            master
            and integrity == "verified"
            and baseline
            and baseline.get("status") == "compiled"
            and bool(baseline.get("offline_verified"))
            and mapping_status == "confirmed"
            and fact_counts.get("candidate", 0) == 0
            and fact_counts.get("approved", 0) > 0
        )
        supporting_documents = self.resume_store.list_documents("supporting")
        return {
            "master": master,
            "integrity": integrity,
            "baseline": baseline,
            "template_map_status": mapping_status,
            "regions": regions,
            "facts": facts,
            "fact_counts": fact_counts,
            "fact_bank_revision": self.resume_store.fact_bank_revision(),
            "fact_categories": sorted(FACT_CATEGORIES),
            "supporting_documents": supporting_documents,
            "tectonic": self.tectonic.status(),
            "onboarding_ready": ready,
        }

    def _begin_onboarding_operation(self, label: str) -> threading.Event:
        self._require_idle_onboarding()
        if self._onboarding_busy is not None:
            raise RuntimeError(f"another onboarding operation is active: {self._onboarding_busy}")
        self._onboarding_busy = label
        self._onboarding_cancel = threading.Event()
        self._onboarding_done.clear()
        return self._onboarding_cancel

    def _end_onboarding_operation(self) -> None:
        self._onboarding_busy = None
        self._onboarding_cancel = None
        self._onboarding_done.set()

    def _require_idle_onboarding(self) -> None:
        self._require_open()
        if self._state is not SessionState.IDLE:
            raise RuntimeError("resume onboarding changes are allowed only while the session is idle")

    def _require_open(self) -> None:
        if self._closed or self._state is SessionState.EXITED:
            raise RuntimeError("application controller is closed")
