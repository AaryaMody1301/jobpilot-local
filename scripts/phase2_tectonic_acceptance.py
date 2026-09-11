from __future__ import annotations

import json
import tempfile
from pathlib import Path

from jobpilot.app.controller import ApplicationController
from jobpilot.runtime.paths import ManagedPaths

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"
FIXTURE = ROOT / "tests" / "fixtures" / "phase2_resume.tex"
TEMPLATE_SHAPE = ROOT / "tests" / "fixtures" / "phase2_template_shape.tex"


def main() -> int:
    for fixture in (FIXTURE, TEMPLATE_SHAPE):
        if not fixture.is_file():
            raise RuntimeError(f"controlled resume fixture is missing: {fixture}")

    with tempfile.TemporaryDirectory(prefix="jobpilot-phase2-tectonic-") as temp_dir:
        paths = ManagedPaths(Path(temp_dir) / "JobPilotLocal")
        controller = ApplicationController(paths, MIGRATIONS, sample_item_seconds=0.05)
        try:
            controller.import_master_resume(FIXTURE)
            controller.install_tectonic()

            first = controller.compile_master_resume(allow_package_downloads=True)["resume"]["baseline"]
            if first["status"] != "compiled" or bool(first["offline_verified"]):
                raise RuntimeError("network-enabled cache population compile did not record the expected baseline state")

            second_state = controller.compile_master_resume(allow_package_downloads=False)["resume"]
            second = second_state["baseline"]
            if second["status"] != "compiled" or not bool(second["offline_verified"]):
                raise RuntimeError("cached-only Tectonic compile did not establish offline verification")
            if int(second["page_count"]) != 1:
                raise RuntimeError(f"controlled baseline expected one page, got {second['page_count']}")
            if not second.get("pdf_sha256") or not second.get("text_sha256"):
                raise RuntimeError("baseline PDF/text hashes were not recorded")

            region = second_state["regions"][0]
            controller.set_template_region_editable(str(region["id"]), True)
            controller.confirm_template_map()

            for fact in controller.snapshot()["resume"]["facts"]:
                if fact["current_status"] == "candidate":
                    controller.set_fact_status(str(fact["id"]), "approved")

            final_state = controller.snapshot()["resume"]
            if final_state["fact_counts"]["candidate"] != 0:
                raise RuntimeError("controlled onboarding left unresolved candidate facts")
            if not final_state["onboarding_ready"]:
                raise RuntimeError("controlled onboarding did not reach the ready gate after offline compile, mapping, and complete fact review")

            controller.import_master_resume(TEMPLATE_SHAPE)
            shape_first = controller.compile_master_resume(allow_package_downloads=True)["resume"]["baseline"]
            if shape_first["status"] != "compiled" or bool(shape_first["offline_verified"]):
                raise RuntimeError("template-shape cache population compile did not record the expected network-enabled state")
            shape_state = controller.compile_master_resume(allow_package_downloads=False)["resume"]
            shape_baseline = shape_state["baseline"]
            if shape_baseline["status"] != "compiled" or not bool(shape_baseline["offline_verified"]):
                raise RuntimeError("template-shape cached-only Tectonic compile did not establish offline verification")
            if int(shape_baseline["page_count"]) != 2:
                raise RuntimeError(f"template-shape baseline expected two pages, got {shape_baseline['page_count']}")
            if len(shape_state["regions"]) < 5:
                raise RuntimeError("template-shape fixture did not expose the expected editable bullet regions")

            result = {
                "tectonic_version": final_state["tectonic"]["version"],
                "tectonic_integrity": final_state["tectonic"]["integrity"],
                "page_count": final_state["baseline"]["page_count"],
                "offline_verified": bool(final_state["baseline"]["offline_verified"]),
                "template_map": final_state["template_map_status"],
                "approved_facts": final_state["fact_counts"]["approved"],
                "candidate_facts": final_state["fact_counts"]["candidate"],
                "onboarding_ready": bool(final_state["onboarding_ready"]),
                "template_shape_page_count": shape_baseline["page_count"],
                "template_shape_offline_verified": bool(shape_baseline["offline_verified"]),
            }
            print(json.dumps(result, sort_keys=True))
        finally:
            controller.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
