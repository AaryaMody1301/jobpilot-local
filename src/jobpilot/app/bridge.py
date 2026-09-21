from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from jobpilot.app.phase9_controller import Phase9ApplicationController


class DesktopBridge:
    """Single narrow JS API for the current desktop product."""

    def __init__(self, controller: Phase9ApplicationController) -> None:
        self._controller = controller
        self._window: Any | None = None

    def bind_window(self, window: Any) -> None:
        self._window = window

    def get_state(self) -> dict[str, Any]:
        return self._controller.snapshot()

    def start(self) -> dict[str, Any]:
        return self._controller.start()

    def pause(self) -> dict[str, Any]:
        return self._controller.pause()

    def stop(self) -> dict[str, Any]:
        return self._controller.stop()

    def save_targeting(self, settings: Mapping[str, Any]) -> dict[str, Any]:
        return self._controller.save_targeting(settings)

    def choose_master_resume(self) -> dict[str, Any]:
        import webview

        selected = self._require_window().create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=("LaTeX resume (*.tex)",),
        )
        if not selected:
            return self._controller.snapshot()
        return self._controller.import_master_resume(Path(selected[0]))

    def choose_supporting_document(self) -> dict[str, Any]:
        import webview

        selected = self._require_window().create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=(
                "Supported evidence (*.pdf;*.txt;*.md;*.tex)",
                "PDF (*.pdf)",
                "Text (*.txt;*.md;*.tex)",
            ),
        )
        if not selected:
            return self._controller.snapshot()
        return self._controller.import_supporting_document(Path(selected[0]))

    def install_tectonic(self) -> dict[str, Any]:
        return self._controller.install_tectonic()

    def compile_master_resume(self, allow_package_downloads: bool = False) -> dict[str, Any]:
        return self._controller.compile_master_resume(allow_package_downloads=bool(allow_package_downloads))

    def set_template_region_editable(self, region_id: str, editable: bool) -> dict[str, Any]:
        return self._controller.set_template_region_editable(region_id, bool(editable))

    def confirm_template_map(self) -> dict[str, Any]:
        return self._controller.confirm_template_map()

    def create_fact(self, fact: Mapping[str, Any]) -> dict[str, Any]:
        return self._controller.create_fact(fact)

    def revise_fact(self, fact_id: str, value: str, category: str) -> dict[str, Any]:
        return self._controller.revise_fact(fact_id, value, category)

    def set_fact_status(self, fact_id: str, status: str) -> dict[str, Any]:
        return self._controller.set_fact_status(fact_id, status)

    def refresh_model_hardware(self) -> dict[str, Any]:
        return self._controller.refresh_model_hardware()

    def install_model_runtime(self, runtime_id: str) -> dict[str, Any]:
        self._controller.install_model_runtime(runtime_id)
        return self._controller.snapshot()

    def install_local_model(self, model_id: str) -> dict[str, Any]:
        self._controller.install_local_model(model_id)
        return self._controller.snapshot()

    def evaluate_local_model(
        self,
        model_install_id: str,
        runtime_install_id: str,
        device_id: str | None = None,
    ) -> dict[str, Any]:
        self._controller.evaluate_local_model(model_install_id, runtime_install_id, device_id)
        return self._controller.snapshot()

    def select_model_for_phase4_review(self, model_install_id: str) -> dict[str, Any]:
        return self._controller.select_model_for_phase4_review(model_install_id)

    def check_model_updates(self) -> dict[str, Any]:
        self._controller.check_model_updates()
        return self._controller.snapshot()

    def import_manual_job_description(self, text: str, source_url: str | None = None) -> dict[str, Any]:
        return self._controller.import_manual_job_description(text, source_url)

    def generate_tailored_resume(self, jd_id: str) -> dict[str, Any]:
        self._controller.generate_tailored_resume(jd_id)
        return self._controller.snapshot()

    def approve_tailored_resume(self, run_id: str, note: str | None = None) -> dict[str, Any]:
        return self._controller.approve_tailored_resume(run_id, note)

    def reject_tailored_resume(self, run_id: str, note: str | None = None) -> dict[str, Any]:
        return self._controller.reject_tailored_resume(run_id, note)

    def enable_automatic_tailoring(self, delete_previous_app_managed_weights: bool = False) -> dict[str, Any]:
        return self._controller.enable_automatic_tailoring(
            delete_previous_app_managed_weights=bool(delete_previous_app_managed_weights)
        )

    def tailored_pdf_data_uri(self, run_id: str) -> str:
        return self._controller.tailored_pdf_data_uri(run_id)

    def import_manual_job(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        return self._controller.import_manual_job(raw)

    def add_verified_job_board(self, provider: str, employer: str, token: str) -> dict[str, Any]:
        return self._controller.add_verified_job_board(provider, employer, token)

    def set_job_board_enabled(self, board_id: str, enabled: bool) -> dict[str, Any]:
        return self._controller.set_job_board_enabled(board_id, bool(enabled))

    def discover_jobs(self) -> dict[str, Any]:
        return self._controller.discover_jobs()

    def refresh_job_metadata(self, job_id: str) -> dict[str, Any]:
        return self._controller.refresh_job_metadata(job_id)

    def queue_controlled_application(self, job_identity: str, target_url: str) -> dict[str, Any]:
        return self._controller.queue_controlled_application(job_identity, target_url)

    def approve_application_question(self, question_id: str, answer: str) -> dict[str, Any]:
        return self._controller.approve_application_question(question_id, answer)

    def resolve_application_eligibility(self, application_id: str, eligible: bool, note: str) -> dict[str, Any]:
        return self._controller.resolve_application_eligibility(application_id, bool(eligible), note)

    def retry_application_tailoring(self, application_id: str) -> dict[str, Any]:
        return self._controller.retry_application_tailoring(application_id)

    def update_application_workspace(
        self,
        application_id: str,
        follow_up_at: str | None,
        notes: str,
        next_action: str,
    ) -> dict[str, Any]:
        return self._controller.update_application_workspace(
            application_id,
            follow_up_at,
            notes,
            next_action,
        )

    def queue_prepared_controlled_application(self, application_id: str, target_url: str) -> dict[str, Any]:
        return self._controller.queue_prepared_controlled_application(application_id, target_url)

    def inspect_prepared_application(self, application_id: str) -> dict[str, Any]:
        return self._controller.inspect_prepared_application(application_id)

    def choose_local_backup(self) -> dict[str, Any]:
        import webview

        selected = self._require_window().create_file_dialog(
            webview.FileDialog.SAVE,
            directory=str(self._controller.paths.backups),
            save_filename=f"jobpilot-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip",
            file_types=("JobPilot backup (*.zip)",),
        )
        if not selected:
            return self._controller.snapshot()
        return self._controller.create_local_backup(Path(selected[0]))

    def choose_local_restore(self) -> dict[str, Any]:
        import webview

        selected = self._require_window().create_file_dialog(
            webview.FileDialog.OPEN,
            directory=str(self._controller.paths.backups),
            allow_multiple=False,
            file_types=("JobPilot backup (*.zip)",),
        )
        if not selected:
            return self._controller.snapshot()
        return self._controller.stage_local_restore(Path(selected[0]))

    def activate_real_application_pilot(self, confirmation: str) -> dict[str, Any]:
        return self._controller.activate_real_application_pilot(confirmation)

    def deactivate_real_application_pilot(self) -> dict[str, Any]:
        return self._controller.deactivate_real_application_pilot()

    def queue_prepared_pilot_application(self, application_id: str) -> dict[str, Any]:
        return self._controller.queue_prepared_pilot_application(application_id)

    def close_for_window_event(self) -> bool:
        if self._controller.cancel_onboarding_operation():
            return False
        self._controller.close()
        return True

    def _require_window(self) -> Any:
        if self._window is None:
            raise RuntimeError("desktop window is not ready")
        return self._window
