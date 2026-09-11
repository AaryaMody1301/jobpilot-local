from __future__ import annotations

import base64
from typing import Any

from jobpilot.app.phase3_controller import Phase3ApplicationController
from jobpilot.domain.states import SessionState
from jobpilot.model.phase4 import Phase4ModelManager
from jobpilot.resume.documents import sha256_file
from jobpilot.resume.tailoring_service import TailoringService
from jobpilot.resume.tailoring_store import TailoringStore


class Phase4ApplicationController(Phase3ApplicationController):
    """Manual-JD evidence tailoring. Discovery and employer applications remain disabled."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.models = Phase4ModelManager(self.paths, self.database)
        self.tailoring_store = TailoringStore(self.database, self.paths.root)
        self.tailoring = TailoringService(self.paths, self.resume_store, self.tailoring_store, self.models)
        self.database.record_foundation_activity(
            self.session_id,
            "phase4_ready",
            "Phase 4 manual-JD evidence-tailoring boundary loaded; no discovery or employer submission started",
        )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = super().snapshot()
            state["phase"] = 4
            state["tailoring"] = self._tailoring_snapshot()
            return state

    def import_manual_job_description(self, text: str, source_url: str | None = None) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            jd = self.tailoring.import_manual_jd(text, source_url)
            marker = "; instruction-like text detected and will remain untrusted data" if jd.get("instruction_like") else ""
            self.database.record_foundation_activity(
                self.session_id,
                "manual_jd",
                f"Stored local manual job description {jd['id']}{marker}",
            )
            return self.snapshot()

    def generate_tailored_resume(self, jd_id: str) -> dict[str, Any]:
        with self._lock:
            if self._state is not SessionState.IDLE:
                raise RuntimeError("resume tailoring is allowed only while the session is idle")
            cancel = self._begin_onboarding_operation("evidence-based resume tailoring")
        try:
            run = self.tailoring.generate(jd_id, cancel)
            with self._lock:
                self._require_open()
                self.database.record_foundation_activity(
                    self.session_id,
                    "tailoring",
                    f"Tailoring run {run['id']} finished as {run['status']}; no employer submission exists in Phase 4",
                )
            return run
        except Exception as exc:
            with self._lock:
                if not self._closed:
                    self.database.record_foundation_activity(self.session_id, "tailoring_failed", str(exc)[-1000:])
            raise
        finally:
            with self._lock:
                self._end_onboarding_operation()

    def approve_tailored_resume(self, run_id: str, note: str | None = None) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            result = self.tailoring.approve(run_id, note)
            gate = result["review_gate"]
            reset = "; previous approvals were reset because the validation context changed" if result.get("gate_reset") else ""
            self.database.record_foundation_activity(
                self.session_id,
                "tailoring_approved",
                f"Approved distinct tailored resume {run_id}; model review gate {gate['approved_distinct_resumes']}/5{reset}",
            )
            return self.snapshot()

    def reject_tailored_resume(self, run_id: str, note: str | None = None) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            self.tailoring.reject(run_id, note)
            self.database.record_foundation_activity(self.session_id, "tailoring_rejected", f"Rejected tailored resume {run_id}")
            return self.snapshot()

    def enable_automatic_tailoring(self, *, delete_previous_app_managed_weights: bool = False) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            state = self.models.store.model_state()
            model_install_id = str(state.get("selected_model_install_id") or "")
            if not model_install_id:
                raise RuntimeError("no selected model is awaiting the Phase 4 review gate")
            self.tailoring.require_review_gate_current(model_install_id)
            result = self.models.finalize_after_phase4_review_gate(
                model_install_id,
                delete_previous_app_managed_weights=bool(delete_previous_app_managed_weights),
            )
            self.database.record_foundation_activity(
                self.session_id,
                "auto_tailoring_enabled",
                "Enabled automatic local resume tailoring after five distinct persisted human approvals for the current validation context",
            )
            return result

    def tailored_pdf_data_uri(self, run_id: str) -> str:
        with self._lock:
            self._require_open()
            run = self.tailoring_store.get_run(run_id)
            if run is None:
                raise KeyError(run_id)
            relative = str(run.get("pdf_relpath") or "")
            if not relative:
                raise RuntimeError("tailoring run has no PDF artifact")
            path = self.tailoring_store.absolute_path(relative)
            if not path.is_file() or sha256_file(path) != str(run.get("pdf_sha256") or ""):
                raise RuntimeError("tailored PDF failed integrity verification")
            if path.stat().st_size > 10 * 1024 * 1024:
                raise RuntimeError("tailored PDF exceeds the local preview size limit")
            return "data:application/pdf;base64," + base64.b64encode(path.read_bytes()).decode("ascii")

    def _tailoring_snapshot(self) -> dict[str, Any]:
        self.tailoring.mark_stale_runs()
        runs = self.tailoring_store.list_runs(30)
        jds = []
        for jd in self.tailoring_store.list_jds(30):
            text = str(jd.pop("jd_text"))
            jd["preview"] = text[:600]
            jd["character_count"] = len(text)
            jds.append(jd)
        model_state = self.models.store.model_state()
        selected = model_state.get("selected_model_install_id")
        gate = self.models.store.review_gate(str(selected)) if selected else None
        return {
            "manual_jds": jds,
            "runs": runs,
            "selected_model_install_id": selected,
            "review_gate": gate,
            "auto_tailoring_enabled": self.tailoring.auto_tailoring_is_current(),
            "phase5_discovery_enabled": False,
            "employer_submission_enabled": False,
        }
