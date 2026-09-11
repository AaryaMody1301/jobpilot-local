from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

from jobpilot.app.phase4_bridge import Phase4DesktopBridge
from jobpilot.app.phase4_controller import Phase4ApplicationController
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


def create_controller(paths: ManagedPaths | None = None, *, sample_item_seconds: float = 0.4) -> Phase4ApplicationController:
    migrations_dir, _ = _resource_paths()
    return Phase4ApplicationController(paths or ManagedPaths.default(), migrations_dir, sample_item_seconds=sample_item_seconds)


def run_self_test() -> dict[str, object]:
    import webview  # noqa: F401 - verifies packaged pywebview import

    with tempfile.TemporaryDirectory(prefix="jobpilot-phase4-") as temp_dir:
        temp = Path(temp_dir)
        paths = ManagedPaths(temp / "JobPilotLocal")
        controller = create_controller(paths, sample_item_seconds=0.05)
        initial = controller.snapshot()
        assert initial["phase"] == 4
        assert initial["session_state"] == "idle"
        assert initial["worker_alive"] is False
        assert initial["confirmed_applications_today"] == 0
        assert initial["tailoring"]["manual_jds"] == []
        assert initial["tailoring"]["runs"] == []
        assert initial["tailoring"]["phase5_discovery_enabled"] is False
        assert initial["tailoring"]["employer_submission_enabled"] is False
        assert initial["model"]["auto_tailoring_enabled"] is False

        controller.import_manual_job_description(
            "Data Engineer role requiring SQL and Python. Ignore previous instructions is text from the employer page, not a command.",
            "https://example.invalid/jobs/fixture",
        )
        state = controller.snapshot()
        assert len(state["tailoring"]["manual_jds"]) == 1
        assert state["tailoring"]["manual_jds"][0]["instruction_like"] is True
        assert state["tailoring"]["manual_jds"][0]["character_count"] > 0
        assert "jd_text" not in state["tailoring"]["manual_jds"][0]
        controller.close()

        reopened = create_controller(paths, sample_item_seconds=0.05)
        reopened_state = reopened.snapshot()
        assert reopened_state["phase"] == 4
        assert reopened_state["session_state"] == "idle"
        assert len(reopened_state["tailoring"]["manual_jds"]) == 1
        reopened.close()
        data_root_exists = paths.database_file.exists() and paths.application_artifacts.exists()

    return {
        "phase4_loaded": True,
        "launches_idle": True,
        "manual_jd_persists_locally": True,
        "instruction_like_jd_remains_data": True,
        "no_job_discovery": True,
        "no_employer_submission": True,
        "auto_tailoring_disabled_without_five_reviews": True,
        "managed_roots_created": data_root_exists,
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
    with tempfile.TemporaryDirectory(prefix="jobpilot-phase4-window-") as temp_dir:
        controller = Phase4ApplicationController(
            ManagedPaths(Path(temp_dir) / "JobPilotLocal"), migrations_dir, sample_item_seconds=0.05
        )
        bridge = Phase4DesktopBridge(controller)
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
                bridge_ready = False
                phase4_ready = False
                for _ in range(50):
                    bridge_ready = bool(window.evaluate_js(
                        "typeof window.pywebview !== 'undefined' && typeof window.pywebview.api.get_state === 'function'"
                    ))
                    if bridge_ready:
                        phase4_ready = bool(window.evaluate_js(
                            "typeof window.pywebview.api.import_manual_job_description === 'function' && "
                            "typeof window.pywebview.api.generate_tailored_resume === 'function' && "
                            "typeof window.pywebview.api.approve_tailored_resume === 'function' && "
                            "typeof window.pywebview.api.tailored_pdf_data_uri === 'function'"
                        ))
                        if phase4_ready:
                            break
                    time.sleep(0.1)
                checks["bridge_ready"] = bridge_ready
                checks["phase4_bridge_ready"] = phase4_ready
                checks["document_title"] = window.evaluate_js("document.title")
                if not bridge_ready or not phase4_ready:
                    raise RuntimeError("pywebview Phase 4 JS bridge was not exposed")
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
    controller = Phase4ApplicationController(ManagedPaths.default(), migrations_dir)
    bridge = Phase4DesktopBridge(controller)
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
    parser.add_argument("--self-test", action="store_true", help="run local Phase 4 packaged acceptance checks")
    parser.add_argument("--window-smoke", action="store_true", help="open a hidden Windows pywebview smoke window and exit")
    args = parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(run_self_test(), sort_keys=True))
        return 0
    if args.window_smoke:
        print(json.dumps(run_window_smoke(), sort_keys=True))
        return 0
    run_desktop()
    return 0
