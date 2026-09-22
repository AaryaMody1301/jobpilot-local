from __future__ import annotations

from pathlib import Path
from typing import Any

from jobpilot.app.orchestration_controller import OrchestrationController
from jobpilot.applications import ApplicationWorker
from jobpilot.backup import BackupManager
from jobpilot.pilot import (
    PILOT_CONFIRMATION_PHRASE,
    PILOT_MAX_ARMED_PER_LAUNCH,
    PILOT_POLICY_REVISION,
    PilotApplicationJournal,
    PilotApplicationWorker,
)
from jobpilot.storage.database import utc_now_text
from jobpilot.version import __version__


class ProductController(OrchestrationController):
    """Current product controller: distribution, orchestration, and explicitly activated measured pilot."""

    def __init__(self, paths: Any, migrations_dir: Path, *args: Any, **kwargs: Any) -> None:
        self._restore_applied = BackupManager.apply_pending_restore(paths, migrations_dir)
        self._snapshot_read = False
        self._pilot_session_authorized = False
        self._pilot_armed_application_ids: set[str] = set()
        super().__init__(paths, migrations_dir, *args, **kwargs)
        self.applications = PilotApplicationJournal(self.database, self.tailoring)
        recovered = self.applications.recover_live_pre_submit()
        reset = self._reset_live_pilot_queue(
            "new launch requires explicit per-application real-pilot re-arming"
        )
        self.recovery["recovered_live_pre_submit"] = recovered
        self.recovery["reset_live_queue_for_rearm"] = reset
        self.backups = BackupManager(self.paths, migrations_dir)
        self.database.record_foundation_activity(
            self.session_id,
            "pilot_available",
            "Measured-pilot implementation is available but resets to inactive on every launch; real submissions require local activation, a fresh read-only inspection, and per-application arming",
        )

    def _require_open(self) -> None:
        super()._require_open()
        manager = getattr(self, "backups", None)
        if manager is not None and manager.request_file.is_file() and not self._snapshot_read:
            raise RuntimeError("a restore is staged; restart JobPilot before making more changes")

    def _reset_live_pilot_queue(self, reason: str) -> int:
        reset = self.applications.reset_live_queue_to_prepared(reason)
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE application_attempts
                   SET live_form_json='{}', live_form_checked_at=NULL, updated_at=?
                 WHERE controlled_fixture=0 AND state='prepared' AND package_id IS NOT NULL
                """,
                (utc_now_text(),),
            )
        return reset

    def _make_application_worker(self) -> ApplicationWorker:
        return PilotApplicationWorker(
            self.paths,
            self.applications,
            self.session_id,
            lambda: self._pilot_session_authorized,
            lambda: set(self._pilot_armed_application_ids),
        )

    def activate_real_application_pilot(self, confirmation: str) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            if str(confirmation or "").strip() != PILOT_CONFIRMATION_PHRASE:
                raise ValueError(f"type exactly: {PILOT_CONFIRMATION_PHRASE}")
            self._pilot_session_authorized = True
            self.database.record_foundation_activity(
                self.session_id,
                "pilot_activated",
                "Explicit per-launch real-application pilot activation recorded; each application still requires a fresh read-only inspection and separate arming",
            )
            return self.snapshot()

    def deactivate_real_application_pilot(self) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            reset = self._reset_live_pilot_queue(
                "pilot deactivation requires fresh inspection and explicit re-arming before any later real submission"
            )
            self._pilot_session_authorized = False
            self._pilot_armed_application_ids.clear()
            self.database.record_foundation_activity(
                self.session_id,
                "pilot_deactivated",
                f"Real-application pilot deactivated for this launch; {reset} queued live application(s) returned to prepared and live inspections were cleared",
            )
            return self.snapshot()

    def queue_prepared_pilot_application(self, application_id: str) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            if not self._pilot_session_authorized:
                raise RuntimeError("activate the measured real-application pilot for this launch before arming an application")
            if application_id not in self._pilot_armed_application_ids and len(self._pilot_armed_application_ids) >= PILOT_MAX_ARMED_PER_LAUNCH:
                raise RuntimeError(f"measured pilot is capped at {PILOT_MAX_ARMED_PER_LAUNCH} armed real applications per launch")
            attempt = self.applications.queue_prepared_live(application_id)
            self._pilot_armed_application_ids.add(application_id)
            self.database.record_foundation_activity(
                self.session_id,
                "pilot_application_armed",
                f"Explicitly armed one fresh {attempt.get('provider') or 'supported'} application for measured real submission: {application_id}",
            )
            return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            self._snapshot_read = True
            try:
                state = super().snapshot()
            finally:
                self._snapshot_read = False
            active = bool(self._pilot_session_authorized)
            state["applications"]["controlled_fixture_only"] = False
            state["applications"]["real_employer_submission_enabled"] = active
            state["orchestration"]["real_employer_submission_enabled"] = active
            state["orchestration"]["pilot_activation_required"] = not active
            state["distribution"] = {
                "app_version": __version__,
                "windows_x64_v1": True,
                "backup": self.backups.status(),
                "restore_applied_on_launch": self._restore_applied,
                "pilot_authorized": True,
                "pilot_policy_revision": PILOT_POLICY_REVISION,
                "pilot_activation_available": True,
                "pilot_session_active": active,
                "pilot_activation_resets_on_launch": True,
                "pilot_confirmation_phrase": PILOT_CONFIRMATION_PHRASE,
                "pilot_armed_this_launch": len(self._pilot_armed_application_ids),
                "pilot_arm_limit": PILOT_MAX_ARMED_PER_LAUNCH,
                "real_employer_submission_enabled": active,
                "pilot_boundary": "This build was explicitly authorized for a measured pilot. Every launch starts inactive; each real application needs a fresh read-only inspection and explicit arming; supported-provider blockers remain fail-closed; and only the existing single worker may submit.",
            }
            return state

    def create_local_backup(self, destination: Path) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            result = self.backups.create(self.database, destination)
            self.database.record_foundation_activity(
                self.session_id,
                "backup_created",
                "Created a verified portable local backup; machine-specific caches and browser/model state were excluded",
            )
            state = self.snapshot()
            state["distribution"]["last_backup_created"] = result
            return state

    def stage_local_restore(self, archive: Path) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            result = self.backups.stage_restore(archive)
            reset = self._reset_live_pilot_queue(
                "restore staging requires fresh inspection and explicit real-pilot re-arming after restart"
            )
            self._pilot_session_authorized = False
            self._pilot_armed_application_ids.clear()
            self.database.record_foundation_activity(
                self.session_id,
                "restore_staged",
                f"Verified and staged a portable backup restore; restart is required, pilot activation reset, and {reset} queued live application(s) returned to prepared",
            )
            state = self.snapshot()
            state["distribution"]["staged_restore"] = result
            return state
