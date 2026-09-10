from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from jobpilot.app.controller import ApplicationController


class DesktopBridge:
    """Narrow JS API; filesystem access is limited to explicit native file selections."""

    def __init__(self, controller: ApplicationController) -> None:
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

    def reset_sample_work(self) -> dict[str, Any]:
        return self._controller.reset_sample_work()

    def choose_master_resume(self) -> dict[str, Any]:
        import webview

        window = self._require_window()
        selected = window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=("LaTeX resume (*.tex)",),
        )
        if not selected:
            return self._controller.snapshot()
        return self._controller.import_master_resume(Path(selected[0]))

    def choose_supporting_document(self) -> dict[str, Any]:
        import webview

        window = self._require_window()
        selected = window.create_file_dialog(
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

    def close_for_window_event(self) -> bool:
        self._controller.close()
        return True

    def _require_window(self) -> Any:
        if self._window is None:
            raise RuntimeError("desktop window is not ready")
        return self._window
