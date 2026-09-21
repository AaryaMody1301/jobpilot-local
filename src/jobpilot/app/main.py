from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

from jobpilot.app.bridge import DesktopBridge
from jobpilot.app.product_controller import ProductController
from jobpilot.runtime.paths import ManagedPaths


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resource_paths() -> tuple[Path, Path]:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        root = Path(frozen_root)
        return root / "migrations", root / "ui" / "index.html"
    root = _repository_root()
    return root / "migrations", root / "src" / "jobpilot" / "ui" / "index.html"


def _configure_browser_path() -> None:
    if getattr(sys, "frozen", False):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"


def create_controller(
    paths: ManagedPaths | None = None,
    *,
    sample_item_seconds: float = 0.4,
) -> ProductController:
    _configure_browser_path()
    migrations_dir, _ = _resource_paths()
    return ProductController(
        paths or ManagedPaths.default(),
        migrations_dir,
        sample_item_seconds=sample_item_seconds,
    )


def run_review_gate_report(paths: ManagedPaths | None = None) -> dict[str, object]:
    """Return a privacy-safe human-review gate report for the active local profile."""
    controller = create_controller(paths)
    try:
        state = controller.snapshot()
        tailoring = state["tailoring"]
        selected = tailoring.get("selected_model_install_id")
        raw_gate = tailoring.get("review_gate") or {}
        required = int(raw_gate.get("required_distinct_resumes") or 5)
        approved = int(raw_gate.get("approved_distinct_resumes") or 0)
        remaining = max(
            0,
            int(
                raw_gate.get("remaining")
                if raw_gate.get("remaining") is not None
                else required - approved
            ),
        )
        gate_current = False
        gate_reason: str | None = None
        if selected:
            try:
                controller.tailoring.require_review_gate_current(str(selected))
                gate_current = True
            except Exception as exc:
                gate_reason = str(exc)
        else:
            gate_reason = "no selected validated model/configuration is awaiting human review"

        resume = state["resume"]
        baseline = resume.get("baseline") or {}
        fact_counts = resume.get("fact_counts") or {}
        return {
            "selected_model_install_id": selected,
            "required_distinct_resumes": required,
            "approved_distinct_resumes": approved,
            "remaining": remaining,
            "persisted_gate_complete": bool(raw_gate.get("complete")),
            "current_review_context_complete": gate_current,
            "ready_to_close_review_gate": gate_current,
            "ready_to_close_phase4": gate_current,
            "automatic_tailoring_enabled": bool(tailoring.get("auto_tailoring_enabled")),
            "employer_submission_enabled": bool(tailoring.get("employer_submission_enabled")),
            "gate_reason": gate_reason,
            "resume_readiness": {
                "onboarding_ready": bool(resume.get("onboarding_ready")),
                "master_present": bool(resume.get("master")),
                "master_integrity_verified": resume.get("integrity") == "verified",
                "baseline_compiled": baseline.get("status") == "compiled",
                "offline_baseline_verified": bool(baseline.get("offline_verified")),
                "template_map_confirmed": resume.get("template_map_status") == "confirmed",
                "candidate_facts": int(fact_counts.get("candidate") or 0),
                "approved_facts": int(fact_counts.get("approved") or 0),
                "rejected_facts": int(fact_counts.get("rejected") or 0),
            },
        }
    finally:
        controller.close()


# Backward-compatible name retained for scripts/docs that predate the final product terminology.
run_phase4_gate_report = run_review_gate_report


def run_self_test() -> dict[str, object]:
    import webview  # noqa: F401 - verifies packaged pywebview import

    with tempfile.TemporaryDirectory(prefix="jobpilot-self-test-") as temp_dir:
        controller = create_controller(
            ManagedPaths(Path(temp_dir) / "JobPilotLocal"),
            sample_item_seconds=0.05,
        )
        try:
            state = controller.snapshot()
            assert state["session_state"] == "idle"
            assert state["distribution"]["pilot_session_active"] is False
            assert state["distribution"]["real_employer_submission_enabled"] is False
            assert state["distribution"]["backup"]["restore_pending"] is False
            phrase = str(state["distribution"]["pilot_confirmation_phrase"])
            assert controller.activate_real_application_pilot(phrase)["distribution"]["pilot_session_active"] is True
            assert controller.deactivate_real_application_pilot()["distribution"]["pilot_session_active"] is False
        finally:
            controller.close()
    return {
        "launches_idle": True,
        "backup_restore_available": True,
        "real_application_pilot_activation_available": True,
        "real_application_pilot_active_by_default": False,
        "pywebview_imported": True,
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
    with tempfile.TemporaryDirectory(prefix="jobpilot-window-") as temp_dir:
        controller = ProductController(
            ManagedPaths(Path(temp_dir) / "JobPilotLocal"),
            migrations_dir,
            sample_item_seconds=0.05,
        )
        bridge = DesktopBridge(controller)
        window = webview.create_window(
            "JobPilot Local Smoke",
            url=ui_index.resolve().as_uri(),
            js_api=bridge,
            width=960,
            height=680,
            hidden=True,
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
                    ready = bool(
                        window.evaluate_js(
                            "typeof window.pywebview !== 'undefined' && "
                            "typeof window.pywebview.api.get_state === 'function' && "
                            "typeof window.pywebview.api.choose_local_backup === 'function' && "
                            "typeof window.pywebview.api.inspect_prepared_application === 'function' && "
                            "typeof window.pywebview.api.job_workspace_detail === 'function' && "
                            "typeof window.pywebview.api.application_workspace_detail === 'function' && "
                            "typeof window.pywebview.api.refresh_job_metadata === 'function' && "
                            "typeof window.pywebview.api.update_application_workspace === 'function' && "
                            "typeof window.pywebview.api.activate_real_application_pilot === 'function'"
                        )
                    )
                    if ready:
                        break
                    time.sleep(0.1)
                if not ready:
                    raise RuntimeError("pywebview product JS bridge was not exposed")
                checks["bridge_ready"] = True
                checks["distribution_ui"] = bool(
                    window.evaluate_js("document.getElementById('distribution-panel') !== null")
                )
                checks["orchestration_ui"] = bool(
                    window.evaluate_js("document.getElementById('orchestration-panel') !== null")
                )
                checks["document_title"] = window.evaluate_js("document.title")
                if not checks["distribution_ui"] or not checks["orchestration_ui"]:
                    raise RuntimeError("current product UI was not injected")
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
    controller = ProductController(ManagedPaths.default(), migrations_dir)
    bridge = DesktopBridge(controller)
    window = webview.create_window(
        "JobPilot Local",
        url=ui_index.resolve().as_uri(),
        js_api=bridge,
        width=1240,
        height=840,
        min_size=(960, 660),
        resizable=True,
        background_color="#f4f6f8",
        text_select=True,
    )
    bridge.bind_window(window)
    window.events.closing += lambda: bridge.close_for_window_event()
    window.events.closed += lambda: controller.close()
    webview.start(gui="edgechromium", debug=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="JobPilot Local desktop application")
    parser.add_argument("--self-test", action="store_true", help="run local packaged acceptance checks")
    parser.add_argument("--window-smoke", action="store_true", help="open a hidden Windows pywebview smoke window and exit")
    parser.add_argument("--browser-smoke", action="store_true", help="launch the packaged Playwright Chromium and exit")
    parser.add_argument("--review-gate-report", "--phase4-gate-report", dest="review_gate_report", action="store_true", help="print the privacy-safe five-resume human-review gate report")
    args = parser.parse_args(argv)
    if args.review_gate_report:
        report = run_review_gate_report()
        print(json.dumps(report, sort_keys=True))
        return 0 if report["ready_to_close_review_gate"] else 2
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


if __name__ == "__main__":
    raise SystemExit(main())
