from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import webview

from jobpilot.domain.states import ApplicationState
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.runtime.shutdown import ShutdownPolicy


HTML = """<!doctype html><html><body><h1>JobPilot Phase 0 Probe</h1><p>No application automation is enabled.</p></body></html>"""


def self_test() -> int:
    with tempfile.TemporaryDirectory() as temp:
        paths = ManagedPaths(Path(temp) / "JobPilotLocal")
        paths.create_phase0_roots()
        plan = ShutdownPolicy().plan(ApplicationState.FILLING)
        result = {
            "pywebview_imported": bool(webview),
            "managed_roots_created": paths.models.is_dir() and paths.browsers.is_dir(),
            "pre_submit_close_waits": plan.waits_for_confirmation,
            "schedules_new_work_on_close": plan.schedule_new_work,
        }
        print(json.dumps(result, sort_keys=True))
        return 0 if all([result["pywebview_imported"], result["managed_roots_created"], not result["pre_submit_close_waits"], not result["schedules_new_work_on_close"]]) else 1


def show_probe_window() -> int:
    window = webview.create_window("JobPilot Phase 0 Probe", html=HTML)

    def on_closing() -> bool:
        # Phase 1 replaces this probe with the real closing screen/coordinator.
        return True

    window.events.closing += on_closing
    webview.start()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    return self_test() if args.self_test else show_probe_window()


if __name__ == "__main__":
    raise SystemExit(main())
