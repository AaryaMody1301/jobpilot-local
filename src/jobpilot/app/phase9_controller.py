from __future__ import annotations

from pathlib import Path
from typing import Any

from jobpilot.app.phase8_controller import Phase8ApplicationController
from jobpilot.backup import BackupManager
from jobpilot.version import __version__


class Phase9ApplicationController(Phase8ApplicationController):
    """Phase 9 distribution/recovery boundary; real-employer pilot stays locked."""

    def __init__(self, paths: Any, migrations_dir: Path, *args: Any, **kwargs: Any) -> None:
        self._phase9_restore_applied = BackupManager.apply_pending_restore(paths, migrations_dir)
        super().__init__(paths, migrations_dir, *args, **kwargs)
        self.backups = BackupManager(self.paths, migrations_dir)
        self.database.record_foundation_activity(
            self.session_id,
            "phase9_distribution_ready",
            "Phase 9 distribution/backup/restore loaded; real employer pilot activation remains locked",
        )

    def _require_open(self) -> None:
        super()._require_open()
        manager = getattr(self, "backups", None)
        if manager is not None and manager.request_file.is_file():
            raise RuntimeError("a restore is staged; restart JobPilot before making more changes")

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = super().snapshot()
            state["phase"] = 9
            state["applications"]["real_employer_submission_enabled"] = False
            state["orchestration"]["real_employer_submission_enabled"] = False
            state["distribution"] = {
                "app_version": __version__,
                "windows_x64_v1": True,
                "backup": self.backups.status(),
                "restore_applied_on_launch": self._phase9_restore_applied,
                "pilot_authorized": False,
                "pilot_activation_available": False,
                "real_employer_submission_enabled": False,
                "pilot_boundary": "A separate explicit user authorization is required before any real employer fill/submit path is implemented or enabled.",
            }
            return state

    def create_local_backup(self, destination: Path) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            result = self.backups.create(self.database, destination)
            self.database.record_foundation_activity(
                self.session_id,
                "phase9_backup_created",
                "Created a verified portable local backup; machine-specific caches and browser/model state were excluded",
            )
            state = self.snapshot()
            state["distribution"]["last_backup_created"] = result
            return state

    def stage_local_restore(self, archive: Path) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            result = self.backups.stage_restore(archive)
            self.database.record_foundation_activity(
                self.session_id,
                "phase9_restore_staged",
                "Verified and staged a portable backup restore; restart is required before the restore is applied",
            )
            state = self.snapshot()
            state["distribution"]["staged_restore"] = result
            return state
