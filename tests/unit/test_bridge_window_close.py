from jobpilot.app.bridge import DesktopBridge


class _FakeController:
    def __init__(self) -> None:
        self.busy = True
        self.closed = False

    def cancel_onboarding_operation(self) -> bool:
        if not self.busy:
            return False
        self.busy = False
        return True

    def close(self) -> None:
        self.closed = True


def test_window_close_first_cancels_active_onboarding() -> None:
    controller = _FakeController()
    bridge = DesktopBridge(controller)  # type: ignore[arg-type]

    assert bridge.close_for_window_event() is False
    assert controller.closed is False

    assert bridge.close_for_window_event() is True
    assert controller.closed is True
