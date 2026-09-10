from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from jobpilot.app.phase3_controller import Phase3ApplicationController
from jobpilot.runtime.paths import ManagedPaths

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"
RUNTIME_ID = "llama-b10809-win-cpu-x64"
MODEL_ID = "qwen3.5-0.8b-q4_0"


def main() -> int:
    if os.name != "nt":
        raise RuntimeError("Phase 3 real-model acceptance requires Windows")
    with tempfile.TemporaryDirectory(prefix="jobpilot-phase3-model-") as temp_dir:
        controller = Phase3ApplicationController(ManagedPaths(Path(temp_dir) / "JobPilotLocal"), MIGRATIONS, sample_item_seconds=0.01)
        try:
            before = controller.snapshot()
            if before["model"]["auto_tailoring_enabled"]:
                raise RuntimeError("auto-tailoring must be disabled before Phase 4 review")
            runtime = controller.install_model_runtime(RUNTIME_ID)
            if runtime["status"] != "installed" or not runtime["present"] or runtime["integrity"] != "verified":
                raise RuntimeError("checksum-verified llama.cpp runtime did not install")
            model = controller.install_local_model(MODEL_ID)
            if model["status"] != "installed" or model["integrity"] != "verified":
                raise RuntimeError("checksum-verified model did not install")
            evaluation = controller.evaluate_local_model(MODEL_ID, RUNTIME_ID)
            if not evaluation["overall_pass"]:
                raise RuntimeError(f"controlled model evaluation failed: {evaluation}")
            controller.select_model_for_phase4_review(MODEL_ID, RUNTIME_ID)
            final = controller.snapshot()
            if final["model"]["selection"]["selected_model_install_id"] != MODEL_ID:
                raise RuntimeError("validated model was not selected for future review")
            if final["model"]["auto_tailoring_enabled"]:
                raise RuntimeError("Phase 3 must not enable automatic tailoring")
            print(json.dumps({"runtime":RUNTIME_ID,"model":MODEL_ID,"structured_pass":evaluation["structured_pass"],"factual_pass":evaluation["factual_pass"],"tailoring_pass":evaluation["tailoring_pass"],"resource_pass":evaluation["resource_pass"],"overall_pass":evaluation["overall_pass"],"elapsed_ms":evaluation["elapsed_ms"],"peak_rss_bytes":evaluation["peak_rss_bytes"],"selected_for_phase4_review":True,"auto_tailoring_enabled":False}, sort_keys=True))
        finally:
            controller.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
