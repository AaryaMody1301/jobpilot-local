from __future__ import annotations

import argparse
import json
import os
import tempfile
import threading
import time
from pathlib import Path

from jobpilot.app.phase4_main import _resource_paths, run_phase4_gate_report
from jobpilot.app.phase6_main import _inject_phase6_ui
from jobpilot.app.phase8_bridge import Phase8DesktopBridge
from jobpilot.app.phase8_controller import Phase8ApplicationController
from jobpilot.applications import ControlledFixtureViolation
from jobpilot.runtime.paths import ManagedPaths


def create_controller(paths: ManagedPaths | None = None, *, sample_item_seconds: float = 0.4) -> Phase8ApplicationController:
    migrations_dir, _ = _resource_paths()
    return Phase8ApplicationController(paths or ManagedPaths.default(), migrations_dir, sample_item_seconds=sample_item_seconds)


def _inject_phase8_ui(window: object, ui_index: Path) -> None:
    _inject_phase6_ui(window, ui_index)
    script = ui_index.with_name("phase8.js").read_text(encoding="utf-8")
    window.evaluate_js(script)  # type: ignore[attr-defined]


def run_self_test() -> dict[str, object]:
    import webview  # noqa: F401 - verifies packaged pywebview import

    with tempfile.TemporaryDirectory(prefix="jobpilot-phase8-") as temp_dir:
        paths = ManagedPaths(Path(temp_dir) / "JobPilotLocal")
        controller = create_controller(paths, sample_item_seconds=0.05)
        try:
            for board in controller.job_store.boards():
                controller.set_job_board_enabled(str(board["id"]), False)
            controller.import_manual_job({
                "employer": "Self Test Co",
                "title": "Data Analyst",
                "location": "Remote",
                "workplace_type": "remote",
                "employment_type": "permanent_full_time",
                "source_url": "https://example.invalid/jobs/review",
                "apply_url": "https://example.invalid/jobs/review/apply",
                "description": "Permanent full-time data analyst role. Work remotely with the analytics team.",
            })
            controller.import_manual_job({
                "employer": "Self Test Co",
                "title": "Astronaut",
                "location": "Surat, India",
                "workplace_type": "onsite",
                "employment_type": "permanent_full_time",
                "source_url": "https://example.invalid/jobs/ineligible",
                "description": "Permanent full-time astronaut role in Surat.",
            })
            controller.run_orchestration_cycle(discover=False)
            controller.run_orchestration_cycle(discover=False)
            state = controller.snapshot()
            review = next(item for item in state["orchestration"]["history"] if item.get("title") == "Data Analyst")
            assert review["state"] == "needs_review"
            controller.resolve_application_eligibility(str(review["id"]), False, "controlled self-test review resolution")
            state = controller.snapshot()
            assert state["phase"] == 8
            assert state["session_state"] == "idle"
            assert state["orchestration"]["daily"]["target_confirmed"] == 50
            assert state["orchestration"]["daily"]["confirmed_real"] == 0
            assert state["orchestration"]["real_employer_submission_enabled"] is False
            assert all(item["state"] == "ineligible" for item in state["orchestration"]["history"] if item.get("discovered_job_id"))
            external_rejected = False
            try:
                controller.queue_controlled_application("real-target", "https://example.com/apply")
            except ControlledFixtureViolation:
                external_rejected = True
            assert external_rejected
        finally:
            controller.close()

    return {
        "phase8_loaded": True,
        "launches_idle": True,
        "discovery_matching_orchestration": True,
        "eligibility_attention_lane": True,
        "daily_target_visible": True,
        "real_employer_submission_disabled": True,
        "real_employer_target_rejected_by_controlled_worker": True,
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
    with tempfile.TemporaryDirectory(prefix="jobpilot-phase8-window-") as temp_dir:
        controller = Phase8ApplicationController(
            ManagedPaths(Path(temp_dir) / "JobPilotLocal"), migrations_dir, sample_item_seconds=0.05
        )
        bridge = Phase8DesktopBridge(controller)
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
                        "typeof window.pywebview.api.resolve_application_eligibility === 'function' && "
                        "typeof window.pywebview.api.inspect_prepared_application === 'function' && "
                        "typeof window.pywebview.api.queue_prepared_controlled_application === 'function'"
                    ))
                    if ready:
                        break
                    time.sleep(0.1)
                if not ready:
                    raise RuntimeError("pywebview Phase 8 JS bridge was not exposed")
                _inject_phase8_ui(window, ui_index)
                checks["phase8_bridge_ready"] = True
                checks["phase8_orchestration_ui"] = bool(window.evaluate_js("document.getElementById('phase8-orchestration') !== null"))
                checks["document_title"] = window.evaluate_js("document.title")
                if not checks["phase8_orchestration_ui"]:
                    raise RuntimeError("Phase 8 orchestration UI was not injected")
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
    controller = Phase8ApplicationController(ManagedPaths.default(), migrations_dir)
    bridge = Phase8DesktopBridge(controller)
    window = webview.create_window(
        "JobPilot Local", url=ui_index.resolve().as_uri(), js_api=bridge,
        width=1240, height=840, min_size=(960, 660), resizable=True,
        background_color="#f4f6f8", text_select=True,
    )
    bridge.bind_window(window)
    window.events.loaded += lambda: _inject_phase8_ui(window, ui_index)
    window.events.closing += lambda: bridge.close_for_window_event()
    window.events.closed += lambda: controller.close()
    webview.start(gui="edgechromium", debug=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="JobPilot Local desktop application")
    parser.add_argument("--self-test", action="store_true", help="run local Phase 8 packaged acceptance checks")
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
