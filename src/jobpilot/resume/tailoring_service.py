from __future__ import annotations

import hashlib
import json
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Mapping

from jobpilot.model.phase4 import Phase4ModelManager
from jobpilot.resume.baseline import inspect_pdf
from jobpilot.resume.documents import sha256_file
from jobpilot.resume.jd import normalize_job_description, normalize_phrase
from jobpilot.resume.store import ResumeStore
from jobpilot.resume.tailoring import (
    TAILORING_SCHEMA,
    TailoringPlan,
    build_tailoring_messages,
    render_tailored_source,
    validate_tailoring_plan,
)
from jobpilot.resume.tailoring_store import TailoringStore
from jobpilot.resume.tectonic import TectonicCompiler
from jobpilot.resume.tooling import TectonicInstallService, resolve_tectonic_executable
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.runtime.process_supervisor import ProcessSupervisor

COMPILE_TIMEOUT_SECONDS = 120.0
OVERFLOW_RE = re.compile(r"Overfull \\(?:hbox|vbox)", re.IGNORECASE)


class TailoringService:
    def __init__(
        self,
        paths: ManagedPaths,
        resume_store: ResumeStore,
        tailoring_store: TailoringStore,
        models: Phase4ModelManager,
    ) -> None:
        self.paths = paths
        self.resume_store = resume_store
        self.store = tailoring_store
        self.models = models

    def import_manual_jd(self, text: str, source_url: str | None = None) -> dict[str, Any]:
        return self.store.register_jd(normalize_job_description(text, source_url))

    def generate(self, jd_id: str, cancel_event: threading.Event) -> dict[str, Any]:
        jd = self.store.get_jd(jd_id)
        if jd is None:
            raise KeyError(jd_id)
        master = self.resume_store.get_active_master()
        if master is None:
            raise RuntimeError("import and approve a master resume before tailoring")
        if not self._onboarding_ready(master):
            raise RuntimeError("resume onboarding must be fully ready before tailoring")

        model_state = self.models.store.model_state()
        model_install_id = str(model_state.get("selected_model_install_id") or "")
        runtime_install_id = str(model_state.get("selected_runtime_install_id") or "")
        device_id = str(model_state.get("selected_device_id") or "")
        if not model_install_id or not runtime_install_id or not device_id:
            raise RuntimeError("select a validated local model/configuration before tailoring")
        model = self.models.store.model_install(model_install_id)
        if model is None or model.get("status") != "validated":
            raise RuntimeError("selected model is not validated")

        approved_facts = self._approved_current_facts(master)
        if not approved_facts:
            raise RuntimeError("no current approved facts are available for tailoring")
        regions = self.resume_store.list_template_regions(str(master["id"]))
        editable = [region for region in regions if int(region.get("editable", 0)) == 1]
        if not editable:
            raise RuntimeError("confirmed template has no approved editable wording regions")

        fact_revision = self.resume_store.fact_bank_revision()
        resume_key = hashlib.sha256(
            "|".join(
                [str(master["sha256"]), str(jd["jd_sha256"]), model_install_id, runtime_install_id, device_id]
            ).encode("utf-8")
        ).hexdigest()
        run = self.store.create_run(
            jd_id=jd_id,
            master_document_id=str(master["id"]),
            master_sha256=str(master["sha256"]),
            fact_bank_revision=fact_revision,
            model_install_id=model_install_id,
            runtime_install_id=runtime_install_id,
            device_id=device_id,
            resume_key=resume_key,
        )
        run_id = str(run["id"])
        try:
            if cancel_event.is_set():
                raise RuntimeError("resume tailoring cancelled")
            messages = build_tailoring_messages(jd_text=str(jd["jd_text"]), editable_regions=editable, approved_facts=approved_facts)
            inference = self.models.infer_selected_structured(messages, TAILORING_SCHEMA, cancel_event, max_tokens=1000)
            plan = TailoringPlan.from_value(inference["value"])
            approved_by_id = {str(fact["id"]): fact for fact in approved_facts}
            editable_by_id = {str(region["id"]): region for region in editable}
            validated_edits = validate_tailoring_plan(
                plan,
                jd_text=str(jd["jd_text"]),
                editable_regions=editable_by_id,
                approved_facts=approved_by_id,
            )
            if not validated_edits:
                message = "local model proposed no evidence-backed wording change; original resume is preferred"
                self.store.fail_run(run_id, message, blocked=True)
                return self.store.get_run(run_id) or run

            master_path = self.resume_store.document_path(master)
            if not master_path.is_file() or sha256_file(master_path) != str(master["sha256"]):
                raise RuntimeError("master resume integrity changed before rendering")
            master_text = master_path.read_text(encoding="utf-8-sig")
            tailored_text, diffs = render_tailored_source(
                master_text,
                source_sha256=str(master["sha256"]),
                regions=regions,
                validated_edits=validated_edits,
            )
            package = self.paths.application_artifacts / "tailoring" / run_id
            package.mkdir(parents=True, exist_ok=False)
            source_path = package / "resume.tex"
            source_path.write_text(tailored_text, encoding="utf-8", newline="")
            (package / "jd.txt").write_text(str(jd["jd_text"]), encoding="utf-8")
            (package / "diff.json").write_text(json.dumps(diffs, ensure_ascii=False, indent=2), encoding="utf-8")
            mappings = [
                {"keyword": item.keyword, "fact_ids": list(item.fact_ids)} for item in plan.keyword_mappings
            ]
            (package / "keyword_mapping.json").write_text(json.dumps(mappings, ensure_ascii=False, indent=2), encoding="utf-8")
            fact_refs = self._fact_references(diffs, approved_by_id)
            (package / "fact_references.json").write_text(json.dumps(fact_refs, ensure_ascii=False, indent=2), encoding="utf-8")

            compile_result = self._compile_cached(source_path, package, cancel_event)
            validation = self._validate_compiled(
                master=master,
                tailored_text=tailored_text,
                pdf_path=compile_result["pdf_path"],
                log_path=compile_result["log_path"],
                diffs=diffs,
            )
            (package / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest = {
                "run_id": run_id,
                "jd_id": jd_id,
                "jd_sha256": jd["jd_sha256"],
                "master_document_id": master["id"],
                "master_sha256": master["sha256"],
                "fact_bank_revision": fact_revision,
                "model_install_id": model_install_id,
                "runtime_install_id": runtime_install_id,
                "device_id": device_id,
                "resume_key": resume_key,
                "validation_overall_pass": validation["overall_pass"],
            }
            (package / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            if not validation["overall_pass"]:
                message = "; ".join(str(reason) for reason in validation["failures"])
                return self.store.complete_run(
                    run_id,
                    status="blocked",
                    source_path=source_path,
                    pdf_path=compile_result["pdf_path"],
                    source_sha256=sha256_file(source_path),
                    pdf_sha256=sha256_file(compile_result["pdf_path"]),
                    diff=diffs,
                    keyword_mapping=mappings,
                    fact_refs=fact_refs,
                    validation=validation,
                    model_usage=self._model_usage(inference),
                    failure_message=message,
                )

            status = "auto_validated" if model_state.get("auto_tailoring_model_install_id") == model_install_id else "needs_review"
            return self.store.complete_run(
                run_id,
                status=status,
                source_path=source_path,
                pdf_path=compile_result["pdf_path"],
                source_sha256=sha256_file(source_path),
                pdf_sha256=sha256_file(compile_result["pdf_path"]),
                diff=diffs,
                keyword_mapping=mappings,
                fact_refs=fact_refs,
                validation=validation,
                model_usage=self._model_usage(inference),
            )
        except Exception as exc:
            current = self.store.get_run(run_id)
            if current and current.get("status") == "generating":
                self.store.fail_run(run_id, str(exc))
            raise

    def approve(self, run_id: str, note: str | None = None) -> dict[str, Any]:
        run = self._require_reviewable_fresh(run_id)
        model_id = str(run["model_install_id"])
        self.models.store.record_review_approval(model_id, str(run["resume_key"]))
        reviewed = self.store.set_review_status(run_id, "approved", note)
        return {"run": reviewed, "review_gate": self.models.store.review_gate(model_id)}

    def reject(self, run_id: str, note: str | None = None) -> dict[str, Any]:
        run = self.store.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        if run.get("status") not in {"needs_review", "approved"}:
            raise RuntimeError("only a reviewable tailored resume can be rejected")
        return self.store.set_review_status(run_id, "rejected", note)

    def mark_stale_runs(self) -> int:
        count = 0
        for run in self.store.list_runs(100):
            if run.get("status") not in {"needs_review", "auto_validated"}:
                continue
            if self._stale_reason(run):
                self.store.set_review_status(str(run["id"]), "stale", self._stale_reason(run))
                count += 1
        return count

    def _require_reviewable_fresh(self, run_id: str) -> dict[str, Any]:
        run = self.store.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        if run.get("status") != "needs_review":
            raise RuntimeError("tailored resume is not awaiting human review")
        if not bool((run.get("validation") or {}).get("overall_pass")):
            raise RuntimeError("tailored resume did not pass deterministic validation")
        if not run.get("diff"):
            raise RuntimeError("tailored resume contains no validated wording changes")
        stale = self._stale_reason(run)
        if stale:
            self.store.set_review_status(run_id, "stale", stale)
            raise RuntimeError(f"tailored resume is stale: {stale}")
        source_rel = str(run.get("source_relpath") or "")
        pdf_rel = str(run.get("pdf_relpath") or "")
        if not source_rel or not pdf_rel:
            raise RuntimeError("tailored resume artifacts are missing")
        source = self.store.absolute_path(source_rel)
        pdf = self.store.absolute_path(pdf_rel)
        if not source.is_file() or sha256_file(source) != str(run.get("source_sha256") or ""):
            raise RuntimeError("tailored LaTeX failed integrity verification")
        if not pdf.is_file() or sha256_file(pdf) != str(run.get("pdf_sha256") or ""):
            raise RuntimeError("tailored PDF failed integrity verification")
        return run

    def _stale_reason(self, run: Mapping[str, Any]) -> str | None:
        master = self.resume_store.get_active_master()
        if master is None or str(master["id"]) != str(run["master_document_id"]) or str(master["sha256"]) != str(run["master_sha256"]):
            return "master resume changed"
        if self.resume_store.fact_bank_revision() != int(run["fact_bank_revision"]):
            return "fact bank changed"
        state = self.models.store.model_state()
        if (
            str(state.get("selected_model_install_id") or "") != str(run["model_install_id"])
            or str(state.get("selected_runtime_install_id") or "") != str(run["runtime_install_id"])
            or str(state.get("selected_device_id") or "") != str(run["device_id"])
        ):
            return "selected model configuration changed"
        return None

    def _onboarding_ready(self, master: Mapping[str, Any]) -> bool:
        baseline = self.resume_store.get_baseline(str(master["id"]))
        facts = self._facts_in_active_scope(master)
        return bool(
            baseline
            and baseline.get("status") == "compiled"
            and baseline.get("offline_verified")
            and self.resume_store.template_map_status(str(master["id"])) == "confirmed"
            and facts
            and not any(str(fact["current_status"]) == "candidate" for fact in facts)
            and any(str(fact["current_status"]) == "approved" for fact in facts)
        )

    def _facts_in_active_scope(self, master: Mapping[str, Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for fact in self.resume_store.list_facts():
            source = self.resume_store.get_document(str(fact["source_document_id"]))
            if source is None:
                continue
            if str(source["id"]) == str(master["id"]) or str(source.get("kind")) == "supporting":
                result.append(fact)
        return result

    def _approved_current_facts(self, master: Mapping[str, Any]) -> list[dict[str, Any]]:
        approved: list[dict[str, Any]] = []
        for fact in self._facts_in_active_scope(master):
            if str(fact["current_status"]) != "approved":
                continue
            source = self.resume_store.get_document(str(fact["source_document_id"]))
            if source is None:
                raise RuntimeError("approved fact source is missing")
            path = self.resume_store.document_path(source)
            if not path.is_file() or sha256_file(path) != str(source["sha256"]):
                raise RuntimeError(f"approved fact {fact['id']} has stale or missing source evidence")
            approved.append(fact)
        return approved

    def _compile_cached(self, source_path: Path, package: Path, cancel_event: threading.Event) -> dict[str, Path]:
        tool = TectonicInstallService(self.paths).status()
        executable = resolve_tectonic_executable(self.paths)
        if not tool.get("installed") or tool.get("integrity") != "verified" or executable is None:
            raise RuntimeError("verified app-managed Tectonic is required for tailoring")
        compiler = TectonicCompiler(executable, self.paths.tectonic_cache)
        command = compiler.build_command(source_path, package, allow_package_downloads=False)
        supervisor = ProcessSupervisor()
        process = supervisor.spawn(command, cwd=package, env=compiler.environment())
        try:
            deadline = time.monotonic() + COMPILE_TIMEOUT_SECONDS
            while True:
                if cancel_event.is_set():
                    supervisor.terminate_owned()
                    raise RuntimeError("tailored resume compilation cancelled")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    supervisor.terminate_owned()
                    raise RuntimeError("tailored resume compilation timed out")
                try:
                    code = process.wait(timeout=min(0.2, remaining))
                    break
                except (TimeoutError, subprocess.TimeoutExpired):
                    continue
        finally:
            supervisor.close()
        pdf = package / f"{source_path.stem}.pdf"
        log = package / f"{source_path.stem}.log"
        if code != 0 or not pdf.is_file():
            tail = log.read_text(encoding="utf-8", errors="replace")[-4000:] if log.is_file() else ""
            raise RuntimeError(tail.strip() or f"Tectonic exited with code {code}")
        return {"pdf_path": pdf, "log_path": log}

    def _validate_compiled(
        self,
        *,
        master: Mapping[str, Any],
        tailored_text: str,
        pdf_path: Path,
        log_path: Path,
        diffs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        baseline = self.resume_store.get_baseline(str(master["id"]))
        if not baseline or not baseline.get("offline_verified"):
            raise RuntimeError("offline-verified master baseline is missing")
        pdf = inspect_pdf(pdf_path)
        failures: list[str] = []
        if int(pdf["page_count"]) != int(baseline["page_count"]):
            failures.append(f"page count changed from {baseline['page_count']} to {pdf['page_count']}")
        baseline_sizes = baseline.get("page_sizes") or []
        if len(baseline_sizes) != len(pdf["page_sizes"]):
            failures.append("page geometry count changed")
        else:
            for index, (before, after) in enumerate(zip(baseline_sizes, pdf["page_sizes"]), start=1):
                if abs(float(before["width"]) - float(after["width"])) > 0.5 or abs(float(before["height"]) - float(after["height"])) > 0.5:
                    failures.append(f"page {index} geometry changed")
        log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
        if OVERFLOW_RE.search(log_text):
            failures.append("Tectonic reported an overfull box")
        pdf_text = normalize_phrase(str(pdf["text"]))
        missing_edits: list[str] = []
        for diff in diffs:
            phrase = normalize_phrase(str(diff["after"]))
            if phrase and phrase not in pdf_text:
                missing_edits.append(str(diff["field_id"]))
        if missing_edits:
            failures.append("compiled PDF is missing tailored wording for: " + ", ".join(missing_edits))
        if not str(pdf["text"]).strip():
            failures.append("compiled PDF contains no extractable text")
        return {
            "overall_pass": not failures,
            "failures": failures,
            "page_count": pdf["page_count"],
            "baseline_page_count": baseline["page_count"],
            "page_sizes": pdf["page_sizes"],
            "pdf_text_sha256": pdf["text_sha256"],
            "overflow_detected": bool(OVERFLOW_RE.search(log_text)),
            "offline_compile": True,
            "edited_fields_present_in_pdf": not missing_edits,
            "source_sha256": hashlib.sha256(tailored_text.encode("utf-8")).hexdigest(),
        }

    @staticmethod
    def _fact_references(diffs: list[dict[str, Any]], approved: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
        ids: list[str] = []
        for diff in diffs:
            for fact_id in diff["fact_ids"]:
                if fact_id not in ids:
                    ids.append(fact_id)
        return [
            {
                "fact_id": fact_id,
                "version": approved[fact_id]["current_version"],
                "category": approved[fact_id]["current_category"],
                "source_document_id": approved[fact_id]["source_document_id"],
                "source_ref": approved[fact_id]["source_ref"],
            }
            for fact_id in ids
        ]

    @staticmethod
    def _model_usage(inference: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "model_install_id": inference["model_install_id"],
            "runtime_install_id": inference["runtime_install_id"],
            "device_id": inference["device_id"],
            "context_tokens": inference["context_tokens"],
            "usage": inference.get("usage") or {},
            "timings": inference.get("timings") or {},
            "pressure": inference.get("pressure") or {},
        }
