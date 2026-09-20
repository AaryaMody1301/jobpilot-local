from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from jobpilot.app.main import create_controller
from jobpilot.runtime.paths import ManagedPaths


def main() -> int:
    with TemporaryDirectory(prefix="jobpilot-phase9-acceptance-") as temp_dir:
        root = Path(temp_dir)
        paths = ManagedPaths(root / "JobPilotLocal")
        archive = root / "jobpilot-portable.zip"
        controller = create_controller(paths, sample_item_seconds=0.01)
        try:
            initial = controller.snapshot()
            assert initial["distribution"]["pilot_authorized"] is True
            assert initial["distribution"]["pilot_activation_available"] is True
            assert initial["distribution"]["pilot_session_active"] is False
            assert initial["distribution"]["real_employer_submission_enabled"] is False
            controller.database.set_json_setting("phase9_acceptance", {"value": "before"})
            (paths.master_documents / "phase9.tex").write_text("portable source", encoding="utf-8")
            state = controller.create_local_backup(archive)
            assert archive.is_file()
            assert state["distribution"]["last_backup_created"]["sha256"]
            controller.database.set_json_setting("phase9_acceptance", {"value": "after"})
            (paths.models / "machine-specific.bin").write_bytes(b"preserve")
            state = controller.stage_local_restore(archive)
            assert state["distribution"]["backup"]["restore_pending"] is True
            assert state["distribution"]["pilot_session_active"] is False
            assert state["distribution"]["real_employer_submission_enabled"] is False
            try:
                controller.start()
            except RuntimeError as exc:
                assert "restore is staged" in str(exc)
            else:
                raise AssertionError("staged restore must block new session work until restart")
        finally:
            controller.close()

        restored = create_controller(paths, sample_item_seconds=0.01)
        try:
            state = restored.snapshot()
            assert state["phase"] == 9
            assert state["distribution"]["restore_applied_on_launch"]["applied"] is True
            assert state["distribution"]["backup"]["restore_pending"] is False
            assert state["distribution"]["pilot_activation_available"] is True
            assert state["distribution"]["pilot_session_active"] is False
            assert state["distribution"]["real_employer_submission_enabled"] is False
            assert restored.database.get_json_setting("phase9_acceptance") == {"value": "before"}
            assert (paths.models / "machine-specific.bin").read_bytes() == b"preserve"
            assert (paths.master_documents / "phase9.tex").read_text(encoding="utf-8") == "portable source"
            assert list(paths.backups.glob("pre-restore-*.zip"))
        finally:
            restored.close()

    print("Phase 9 distribution backup/restore acceptance passed; authorized pilot remains inactive by default")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
