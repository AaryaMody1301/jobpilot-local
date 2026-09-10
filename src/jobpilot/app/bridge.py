from __future__ import annotations

from typing import Any, Mapping

from jobpilot.app.controller import ApplicationController


class DesktopBridge:
    """Narrow JS API; no network, shell, or arbitrary filesystem methods are exposed."""

    def __init__(self, controller: ApplicationController) -> None:
        self._controller = controller

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

    def close_for_window_event(self) -> bool:
        self._controller.close()
        return True
