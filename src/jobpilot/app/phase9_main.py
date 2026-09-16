from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

from jobpilot.app.phase4_main import _resource_paths, run_phase4_gate_report
from jobpilot.app.phase8_main import _inject_phase8_ui, run_self_test as run_phase8_self_test
from jobpilot.app.phase9_bridge import Phase9DesktopBridge
from jobpilot.app.phase9_controller import Phase9ApplicationController
from jobpilot.runtime.paths import ManagedPaths


def _configure_browser_path() -> None:
    if getattr(sys, "frozen", False):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"


def create_controller(paths: ManagedPaths | None = None, *, sample_item_seconds: float = 0.4) -> Phase9ApplicationController:
    _configure_browser_path()
    migrations_dir, _ = _resource_paths()
    return Phase9ApplicationController(paths or ManagedPaths.default(), migrations_dir, sample_item_seconds=sample_item_seconds)


def _inject_phase9_ui(window: object, ui_index: Path) -> None:
    _inject_phase8_ui(window, ui_index)
    script = ui_index.with_name("phase9.js").read_text(encoding="utf-8")
    window.evaluate_js(script)  # type: ignore[attr-defined]


def run_self_test() -> dict[str, object]:
    base = run_phase8_self_test()
    with tempfile.TemporaryDirectory(prefix="jobpilot-phase9-") as temp_dir:
        controller = create_controller(ManagedPaths(Path(temp_dir) / "JobPilotLocal"), sample_item_seconds=0.05)
        try:
            state = controller.snapshot()
            assert state["phase"] == 9
            assert state["session_state"] == "idle"
            assert state["distribution"]["pilot_authorized"] is False
            assert state["distribution"]["pilot_activation_available"] is False
            assert state["distribution"]["real_employer_submission_enabled"] is False
            assert state["distribution"]["backup"]["restore_pending"] is False
        finally:
            controller.close()
    return {
        **base,
        "phase9_loaded": True,
        "backup_restore_available": True,
        "real_application_pilot_locked": True,
    }


def run_browser_smoke() -> dict[str, object]:
    _configure_browser_path()
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        executable = Path(playwright.chromium.executable_path)
        if not executable.is_file():
            raise RuntimeError(f"Playwright Chromium executable is missing: {executable}")
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content("<title>JobPilot browser smoke</title><p>local</p>")
            if page.title() != "JobPilot browser smoke":
                raise RuntimeError("bundled Chromium did not render the controlled smoke page")
        finally:
            browser.close()
    return {
        "chromium_launch": True,
        "frozen": bool(getattr(sys, "frozen", False)),
        "playwright_browsers_path": os.environ.get("PLAYWRIGHT_BROWSERS_PATH"),
    }


def run_window_smoke() -> dict[str, object]:
    if os.name != "nt":
        raise SystemExit("window smoke requires Windows")

    import webview

    _configure_browser_path()
    migrations_dir, ui_index = _resource_paths()
    loaded = threading.Event()
    errors: list[str] = []
    checks: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="jobpilot-phase9-window-") as temp_dir:
        controller = Phase9ApplicationController(
            ManagedPaths(Path(temp_dir) / "JobPilotLocal"), migrations_dir, sample_item_seconds=0.05
        )
        bridge = Phase9DesktopBridge(controller)
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
                        "typeof window.pywebview.api.choose_local_backup === 'function' && "
                        "typeof window.pywebview.api.choose_local_restore === 'function' && "
                        "typeof window.pywebview.api.inspect_prepared_application === 'function'"
                    ))
                    if ready:
                        break
                    time.sleep(0.1)
                if not ready:
                    raise RuntimeError("pywebview Phase 9 JS bridge was not exposed")
                _inject_phase9_ui(window, ui_index)
                checks["phase9_bridge_ready"] = True
                checks["phase9_distribution_ui"] = bool(window.evaluate_js("document.getElementById('phase9-distribution') !== null"))
                checks["phase8_orchestration_ui"] = bool(window.evaluate_js("document.getElementById('phase8-orchestration') !== null"))
                checks["document_title"] = window.evaluate_js("document.title")
                if not checks["phase9_distribution_ui"] or not checks["phase8_orchestration_ui"]:
                    raise RuntimeError("Phase 9 or inherited Phase 8 UI was not injected")
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

    _configure_browser_path()
    migrations_dir, ui_index = _resource_paths()
    if not migrations_dir.exists() or not ui_index.exists():
        raise RuntimeError("packaged application resources are missing")
    controller = Phase9ApplicationController(ManagedPaths.default(), migrations_dir)
    bridge = Phase9DesktopBridge(controller)
    window = webview.create_window(
        "JobPilot Local", url=ui_index.resolve().as_uri(), js_api=bridge,
        width=1240, height=840, min_size=(960, 660), resizable=True,
        background_color="#f4f6f8", text_select=True,
    )
    bridge.bind_window(window)
    window.events.loaded += lambda: _inject_phase9_ui(window, ui_index)
    window.events.closing += lambda: bridge.close_for_window_event()
    window.events.closed += lambda: controller.close()
    webview.start(gui="edgechromium", debug=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="JobPilot Local desktop application")
    parser.add_argument("--self-test", action="store_true", help="run local Phase 9 packaged acceptance checks")
    parser.add_argument("--window-smoke", action="store_true", help="open a hidden Windows pywebview smoke window and exit")
    parser.add_argument("--browser-smoke", action="store_true", help="launch the packaged Playwright Chromium and exit")
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
    if args.browser_smoke:
        print(json.dumps(run_browser_smoke(), sort_keys=True))
        return 0
    run_desktop()
    return 0
