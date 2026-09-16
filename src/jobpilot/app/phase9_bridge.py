from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from jobpilot.app.phase8_bridge import Phase8DesktopBridge
from jobpilot.app.phase9_controller import Phase9ApplicationController


class Phase9DesktopBridge(Phase8DesktopBridge):
    def __init__(self, controller: Phase9ApplicationController) -> None:
        super().__init__(controller)
        self._phase9 = controller

    def choose_local_backup(self) -> dict[str, Any]:
        import webview

        window = self._require_window()
        selected = window.create_file_dialog(
            webview.FileDialog.SAVE,
            directory=str(self._phase9.paths.backups),
            save_filename=f"jobpilot-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip",
            file_types=("JobPilot backup (*.zip)",),
        )
        if not selected:
            return self._phase9.snapshot()
        return self._phase9.create_local_backup(Path(selected[0]))

    def choose_local_restore(self) -> dict[str, Any]:
        import webview

        window = self._require_window()
        selected = window.create_file_dialog(
            webview.FileDialog.OPEN,
            directory=str(self._phase9.paths.backups),
            allow_multiple=False,
            file_types=("JobPilot backup (*.zip)",),
        )
        if not selected:
            return self._phase9.snapshot()
        return self._phase9.stage_local_restore(Path(selected[0]))
