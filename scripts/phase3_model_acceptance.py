from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from jobpilot.app.phase3_controller import Phase3ApplicationController
from jobpilot.model.catalogue import get_model
from jobpilot.runtime.paths import ManagedPaths

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"
RUNTIME_ID = "llama-b10809-win-cpu-x64"
MODEL_ID = "qwen3-4b-q4_k_m"


def main() -> int:
    if os.name != "nt":
        raise RuntimeError("Phase 3 real-model acceptance requires Windows")
    with tempfile.TemporaryDirectory(prefix="jobpilot-phase3-model-") as temp_dir:
        controller = Phase3ApplicationController(
            ManagedPaths(Path(temp_dir) / "JobPilotLocal"), MIGRATIONS, sample_item_seconds=0.01
        )
        try:
            before = controller.snapshot()
            if before["model"]["auto_tailoring_enabled"]:
                raise RuntimeError("auto-tailoring must be disabled before Phase 4 review")
            runtime = controller.install_model_runtime(RUNTIME_ID)
            if runtime["status"] != "installed" or not runtime["present"] or runtime["integrity"] != "verified":
                raise RuntimeError("checksum-verified llama.cpp runtime did not install")

            model = controller.install_local_model(MODEL_ID)
            expected_install_id = get_model(MODEL_ID).install_id
            if model["status"] != "installed" or model["integrity"] != "verified":
                raise RuntimeError("checksum-verified model did not install")
            if model["id"] != expected_install_id:
                raise RuntimeError("model revision was not installed under its revision-specific identity")

            evaluation = controller.evaluate_local_model(model["id"], RUNTIME_ID, "none")
            if not evaluation["overall_pass"]:
                raise RuntimeError(f"controlled model evaluation failed: {evaluation}")
            if evaluation["device_id"] != "none":
                raise RuntimeError("CPU evaluation was not pinned to device none")
            if not evaluation.get("generation_tokens_per_second"):
                raise RuntimeError("controlled model evaluation did not record generation throughput")

            controller.select_model_for_phase4_review(model["id"])
            final = controller.snapshot()
            model_state = final["model"]
            gate = model_state["review_gate"] or {}
            if model_state["selection"]["selected_model_install_id"] != model["id"]:
                raise RuntimeError("validated model revision was not selected for future review")
            if gate.get("complete") or gate.get("approved_distinct_resumes") != 0 or gate.get("remaining") != 5:
                raise RuntimeError("Phase 3 must create an empty persisted five-distinct-resume review gate")
            if model_state["auto_tailoring_enabled"]:
                raise RuntimeError("Phase 3 must not enable automatic tailoring")

            print(json.dumps({
                "runtime": RUNTIME_ID,
                "model": MODEL_ID,
                "model_install_id": model["id"],
                "device_id": evaluation["device_id"],
                "context_tokens": evaluation["context_tokens"],
                "structured_pass": evaluation["structured_pass"],
                "factual_pass": evaluation["factual_pass"],
                "tailoring_pass": evaluation["tailoring_pass"],
                "resource_pass": evaluation["resource_pass"],
                "overall_pass": evaluation["overall_pass"],
                "elapsed_ms": evaluation["elapsed_ms"],
                "generation_tokens_per_second": evaluation["generation_tokens_per_second"],
                "peak_rss_bytes": evaluation["peak_rss_bytes"],
                "pressure": evaluation["pressure"],
                "review_gate_remaining": gate.get("remaining"),
                "selected_for_phase4_review": True,
                "auto_tailoring_enabled": False,
            }, sort_keys=True))
        finally:
            controller.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
