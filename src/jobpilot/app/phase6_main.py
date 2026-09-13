from __future__ import annotations

import argparse
import json
import os
import tempfile
import threading
import time
from pathlib import Path

from jobpilot.app.phase4_main import _resource_paths, run_phase4_gate_report
from jobpilot.app.phase5_main import _inject_phase5_ui
from jobpilot.app.phase6_bridge import Phase6DesktopBridge
from jobpilot.app.phase6_controller import Phase6ApplicationController
from jobpilot.applications import ControlledFixtureViolation
from jobpilot.runtime.paths import ManagedPaths


def create_controller(paths: ManagedPaths | None = None, *, sample_item_seconds: float = 0.4) -> Phase6ApplicationController:
    migrations_dir, _ = _resource_paths()
    return Phase6ApplicationController(paths or ManagedPaths.default(), migrations_dir, sample_item_seconds=sample_item_seconds)


def _inject_phase6_ui(window: object, ui_index: Path) -> None:
    _inject_phase5_ui(window, ui_index)
    script = ui_index.with_name("phase6.js").read_text(encoding="utf-8")
    window.evaluate_js(script)  # type: ignore[attr-defined]


def run_self_test() -> dict[str, object]:
    import webview  # noqa: F401 - verifies packaged pywebview import

    with tempfile.TemporaryDirectory(prefix="jobpilot-phase6-") as temp_dir:
        paths = ManagedPaths(Path(temp_dir) / "JobPilotLocal")
        controller = create_controller(paths, sample_item_seconds=0.05)
        state = controller.snapshot()
        assert state["phase"] == 6
        assert state["session_state"] == "idle"
        assert state["applications"]["controlled_fixture_only"] is True
        assert state["applications"]["real_employer_submission_enabled"] is False
        controller.queue_controlled_application("fixture-self-test", "http://127.0.0.1:65535/form")
        controller.queue_controlled_application("fixture-self-test", "http://127.0.0.1:65535/form")
        state = controller.snapshot()
        assert len(state["applications"]["attempts"]) == 1
        external_rejected = False
        try:
            controller.queue_controlled_application("real-target", "https://example.com/apply")
        except ControlledFixtureViolation:
            external_rejected = True
        assert external_rejected
        controller.close()

        reopened = create_controller(paths, sample_item_seconds=0.05)
        persisted = len(reopened.snapshot()["applications"]["attempts"]) == 1
        reopened.close()

    return {
        "phase6_loaded": True,
        "launches_idle": True,
        "controlled_fixture_only": True,
        "duplicate_prevention_persists": persisted,
        "real_employer_target_rejected": external_rejected,
        "real_employer_submission_disabled": True,
        "pywebview_imported": True,
    }


def run_window_smoke() -> dict[str, object]:
    if os.name != "nt":
        raise SystemExit("window smoke requires Windows")

    import webview

    migrations_dir, ui_index = _resource_paths()
    loaded = threading.Event()
    errors: list[str] = []
    checks: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="jobpilot-phase6-window-") as temp_dir:
        controller = Phase6ApplicationController(
            ManagedPaths(Path(temp_dir) / "JobPilotLocal"), migrations_dir, sample_item_seconds=0.05
        )
        bridge = Phase6DesktopBridge(controller)
        window = webview.create_window(
            "JobPilot Local Smoke", url=ui_index.resolve().as_uri(), js_api=bridge,
            width=960, height=680, hidden=True,
        )
        bridge.bind_window(window)
        window.events.loaded += lambda: loaded.set()
        window.events.closed += lambda: controller.close()

        def verify_window() -> None:
            try:
                if not loaded.wait(15):
                    raise TimeoutError("pywebview UI did not load")
                ready = False
                for _ in range(50):
                    ready = bool(window.evaluate_js(
                        "typeof window.pywebview !== 'undefined' && "
                        "typeof window.pywebview.api.queue_controlled_application === 'function' && "
                        "typeof window.pywebview.api.approve_application_question === 'function'"
                    ))
                    if ready:
                        break
                    time.sleep(0.1)
                if not ready:
                    raise RuntimeError("pywebview Phase 6 JS bridge was not exposed")
                _inject_phase6_ui(window, ui_index)
                checks["phase6_bridge_ready"] = True
                checks["phase6_application_ui"] = bool(window.evaluate_js("document.getElementById('application-queue-form') !== null"))
                checks["document_title"] = window.evaluate_js("document.title")
                if not checks["phase6_application_ui"]:
                    raise RuntimeError("Phase 6 controlled-application UI was not injected")
                if checks["document_title"] != "JobPilot Local":
                    raise RuntimeError("bundled UI did not load expected document")
            except Exception as exc:
                errors.append(str(exc))
            finally:
                window.destroy()

        webview.start(verify_window, gui="edgechromium", debug=False)
        controller.close()

    if errors:
        raise RuntimeError("; ".join(errors))
    return {"window_loaded": True, **checks}


def run_desktop() -> None:
    if os.name != "nt":
        raise SystemExit("jobpilot-local v1 desktop supports Windows 10/11 x64 only")

    import webview

    migrations_dir, ui_index = _resource_paths()
    if not migrations_dir.exists() or not ui_index.exists():
        raise RuntimeError("packaged application resources are missing")
    controller = Phase6ApplicationController(ManagedPaths.default(), migrations_dir)
    bridge = Phase6DesktopBridge(controller)
    window = webview.create_window(
        "JobPilot Local", url=ui_index.resolve().as_uri(), js_api=bridge,
        width=1240, height=840, min_size=(960, 660), resizable=True,
        background_color="#f4f6f8", text_select=True,
    )
    bridge.bind_window(window)
    window.events.loaded += lambda: _inject_phase6_ui(window, ui_index)
    window.events.closing += lambda: bridge.close_for_window_event()
    window.events.closed += lambda: controller.close()
    webview.start(gui="edgechromium", debug=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="JobPilot Local desktop application")
    parser.add_argument("--self-test", action="store_true", help="run local Phase 6 packaged acceptance checks")
    parser.add_argument("--window-smoke", action="store_true", help="open a hidden Windows pywebview smoke window and exit")
    parser.add_argument("--phase4-gate-report", action="store_true", help="print the privacy-safe Phase 4 human-gate report")
    args = parser.parse_args(argv)
    if args.phase4_gate_report:
        report = run_phase4_gate_report()
        print(json.dumps(report, sort_keys=True))
        return 0 if report["ready_to_close_phase4"] else 2
    if args.self_test:
        print(json.dumps(run_self_test(), sort_keys=True))
        return 0
    if args.window_smoke:
        print(json.dumps(run_window_smoke(), sort_keys=True))
        return 0
    run_desktop()
    return 0
