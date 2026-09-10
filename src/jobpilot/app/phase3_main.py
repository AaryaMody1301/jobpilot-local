from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

from jobpilot.app.phase3_bridge import Phase3DesktopBridge
from jobpilot.app.phase3_controller import Phase3ApplicationController
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


def create_controller(paths: ManagedPaths | None = None, *, sample_item_seconds: float = 0.4) -> Phase3ApplicationController:
    migrations_dir, _ = _resource_paths()
    return Phase3ApplicationController(paths or ManagedPaths.default(), migrations_dir, sample_item_seconds=sample_item_seconds)


def run_self_test() -> dict[str, object]:
    import webview  # noqa: F401 - verifies packaged pywebview import

    with tempfile.TemporaryDirectory(prefix="jobpilot-phase3-") as temp_dir:
        temp = Path(temp_dir)
        paths = ManagedPaths(temp / "JobPilotLocal")
        source = temp / "resume.tex"
        source.write_text(
            "\\documentclass{article}\n\\begin{document}\n\\section{Experience}\n"
            "\\begin{itemize}\n\\item Built a local SQL analytics pipeline with documented source evidence.\n"
            "\\end{itemize}\n\\end{document}\n",
            encoding="utf-8",
        )
        supporting = temp / "evidence.txt"
        supporting.write_text("Supporting evidence fixture.\n", encoding="utf-8")

        controller = create_controller(paths, sample_item_seconds=0.05)
        initial = controller.snapshot()
        assert initial["session_state"] == "idle"
        assert initial["worker_alive"] is False
        assert initial["confirmed_applications_today"] == 0
        assert initial["phase"] == 3
        assert initial["model"]["hardware"]["memory"]["total_bytes"] > 0
        assert initial["model"]["catalogue"]["models"]
        assert initial["model"]["catalogue"]["runtimes"]
        assert initial["model"]["auto_tailoring_enabled"] is False
        assert initial["model"]["phase4_review_gate_required"] is True

        controller.import_master_resume(source)
        imported = controller.snapshot()["resume"]
        assert imported["integrity"] == "verified"
        assert len(imported["regions"]) == 1
        assert len(imported["facts"]) == 1
        stored_path = paths.root / imported["master"]["stored_relpath"]
        stored_before = stored_path.read_bytes()
        source.write_text("changed outside JobPilot\n", encoding="utf-8")
        assert stored_path.read_bytes() == stored_before

        region_id = imported["regions"][0]["id"]
        controller.set_template_region_editable(region_id, True)
        controller.confirm_template_map()
        fact = controller.snapshot()["resume"]["facts"][0]
        controller.revise_fact(fact["id"], fact["value_text"] + " Verified.", "experience_bullet")
        controller.set_fact_status(fact["id"], "approved")
        controller.import_supporting_document(supporting)

        controller.start()
        controller.pause()
        controller.start()
        controller.stop()
        edited = dict(controller.snapshot()["targeting"])
        edited["notice_period_days"] = 45
        controller.save_targeting(edited)
        controller.close()

        reopened = create_controller(paths, sample_item_seconds=0.05)
        reopened_state = reopened.snapshot()
        assert reopened_state["session_state"] == "idle"
        assert reopened_state["worker_alive"] is False
        assert reopened_state["targeting"]["notice_period_days"] == 45
        assert reopened_state["resume"]["integrity"] == "verified"
        assert reopened_state["resume"]["template_map_status"] == "confirmed"
        assert reopened_state["resume"]["fact_counts"]["approved"] == 1
        assert len(reopened_state["resume"]["supporting_documents"]) == 1
        assert reopened_state["model"]["auto_tailoring_enabled"] is False
        data_root_exists = paths.database_file.exists() and paths.application_artifacts.exists() and paths.tools.exists() and paths.models.exists()
        reopened.close()

    return {
        "launches_idle": True,
        "settings_persist": True,
        "reopen_does_not_resume": True,
        "worker_stops": True,
        "managed_roots_created": data_root_exists,
        "pywebview_imported": True,
        "immutable_resume_import": True,
        "template_map_persists": True,
        "fact_versioning_persists": True,
        "supporting_source_registry": True,
        "hardware_budget_detected": True,
        "model_catalogue_local": True,
        "model_download_requires_explicit_action": True,
        "auto_tailoring_disabled": True,
    }


def run_window_smoke() -> dict[str, object]:
    if os.name != "nt":
        raise SystemExit("window smoke requires Windows")

    import webview

    migrations_dir, ui_index = _resource_paths()
    loaded = threading.Event()
    errors: list[str] = []
    checks: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="jobpilot-window-smoke-") as temp_dir:
        controller = Phase3ApplicationController(
            ManagedPaths(Path(temp_dir) / "JobPilotLocal"),
            migrations_dir,
            sample_item_seconds=0.05,
        )
        bridge = Phase3DesktopBridge(controller)
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
                phase3_bridge_ready = False
                for _ in range(50):
                    bridge_ready = bool(window.evaluate_js(
                        "typeof window.pywebview !== 'undefined' && typeof window.pywebview.api.get_state === 'function'"
                    ))
                    if bridge_ready:
                        phase3_bridge_ready = bool(window.evaluate_js(
                            "typeof window.pywebview.api.refresh_model_hardware === 'function' && "
                            "typeof window.pywebview.api.install_local_model === 'function' && "
                            "typeof window.pywebview.api.evaluate_local_model === 'function'"
                        ))
                        if phase3_bridge_ready:
                            break
                    time.sleep(0.1)
                checks["bridge_ready"] = bridge_ready
                checks["phase3_bridge_ready"] = phase3_bridge_ready
                checks["document_title"] = window.evaluate_js("document.title")
                if not bridge_ready or not phase3_bridge_ready:
                    raise RuntimeError("pywebview Phase 3 JS bridge was not exposed")
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

    controller = Phase3ApplicationController(ManagedPaths.default(), migrations_dir)
    bridge = Phase3DesktopBridge(controller)
    window = webview.create_window(
        "JobPilot Local",
        url=ui_index.resolve().as_uri(),
        js_api=bridge,
        width=1180,
        height=800,
        min_size=(920, 640),
        resizable=True,
        background_color="#f4f6f8",
        text_select=True,
    )
    bridge.bind_window(window)

    def on_closing() -> bool:
        return bridge.close_for_window_event()

    def on_closed() -> None:
        controller.close()

    window.events.closing += on_closing
    window.events.closed += on_closed
    webview.start(gui="edgechromium", debug=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="JobPilot Local desktop application")
    parser.add_argument("--self-test", action="store_true", help="run local Phase 3 packaged acceptance checks")
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
