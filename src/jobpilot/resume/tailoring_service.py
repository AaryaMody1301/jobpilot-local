from __future__ import annotations

from collections import Counter
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
from jobpilot.settings import TargetingSettings

COMPILE_TIMEOUT_SECONDS = 120.0
OVERFLOW_RE = re.compile(r"Overfull \\(?:hbox|vbox)", re.IGNORECASE)
PDF_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+#./-]*")
AUDIT_COMPONENTS = (
    "resume.tex",
    "resume.pdf",
    "resume.log",
    "jd.txt",
    "jd.json",
    "diff.json",
    "keyword_mapping.json",
    "fact_references.json",
    "validation.json",
    "model.json",
    "model_usage.json",
)


def _stable_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _pdf_tokens(value: str) -> list[str]:
    return [token.casefold() for token in PDF_TOKEN_RE.findall(normalize_phrase(value))]


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

        context = self._dependency_context(master, model_install_id, runtime_install_id, device_id)
        fact_revision = int(context["fact_bank_revision"])
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
            template_map_sha256=str(context["template_map_sha256"]),
            baseline_sha256=str(context["baseline_sha256"]),
            profile_sha256=str(context["profile_sha256"]),
            review_context_sha256=str(context["review_context_sha256"]),
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
            (package / "jd.json").write_text(
                json.dumps(
                    {
                        "id": jd["id"],
                        "source_url": jd.get("source_url"),
                        "jd_sha256": jd["jd_sha256"],
                        "instruction_like": bool(jd.get("instruction_like")),
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            (package / "diff.json").write_text(json.dumps(diffs, ensure_ascii=False, indent=2), encoding="utf-8")
            mappings = [
                {"keyword": item.keyword, "fact_ids": list(item.fact_ids)} for item in plan.keyword_mappings
            ]
            (package / "keyword_mapping.json").write_text(json.dumps(mappings, ensure_ascii=False, indent=2), encoding="utf-8")
            fact_refs = self._fact_references(diffs, approved_by_id)
            (package / "fact_references.json").write_text(json.dumps(fact_refs, ensure_ascii=False, indent=2), encoding="utf-8")
            model_evidence = self._model_evidence(model_install_id, runtime_install_id, device_id)
            (package / "model.json").write_text(json.dumps(model_evidence, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
            model_usage = self._model_usage(inference)
            (package / "model_usage.json").write_text(json.dumps(model_usage, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

            compile_result = self._compile_cached(source_path, package, cancel_event)
            validation = self._validate_compiled(
                master=master,
                tailored_text=tailored_text,
                pdf_path=compile_result["pdf_path"],
                log_path=compile_result["log_path"],
                diffs=diffs,
            )
            (package / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

            components = {
                name: {"sha256": sha256_file(package / name), "bytes": (package / name).stat().st_size}
                for name in AUDIT_COMPONENTS
                if (package / name).is_file()
            }
            manifest = {
                "schema_version": 2,
                "run_id": run_id,
                "jd_id": jd_id,
                "jd_sha256": jd["jd_sha256"],
                "jd_source_url": jd.get("source_url"),
                "master_document_id": master["id"],
                "master_sha256": master["sha256"],
                "fact_bank_revision": fact_revision,
                "template_map_sha256": context["template_map_sha256"],
                "baseline_sha256": context["baseline_sha256"],
                "profile_sha256": context["profile_sha256"],
                "review_context_sha256": context["review_context_sha256"],
                "model_install_id": model_install_id,
                "runtime_install_id": runtime_install_id,
                "device_id": device_id,
                "resume_key": resume_key,
                "validation_overall_pass": validation["overall_pass"],
                "components": components,
            }
            manifest_path = package / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
            manifest_sha256 = sha256_file(manifest_path)

            current_context = self._dependency_context(master, model_install_id, runtime_install_id, device_id)
            if current_context["review_context_sha256"] != context["review_context_sha256"]:
                validation = dict(validation)
                validation["overall_pass"] = False
                validation["failures"] = [*validation.get("failures", []), "resume/profile/model validation context changed during generation"]
                (package / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
                components["validation.json"] = {"sha256": sha256_file(package / "validation.json"), "bytes": (package / "validation.json").stat().st_size}
                manifest["validation_overall_pass"] = False
                manifest["components"] = components
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
                manifest_sha256 = sha256_file(manifest_path)

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
                    model_usage=model_usage,
                    failure_message=message,
                    manifest_path=manifest_path,
                    manifest_sha256=manifest_sha256,
                )

            status = "auto_validated" if self._auto_tailoring_current(model_install_id, str(context["review_context_sha256"])) else "needs_review"
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
                model_usage=model_usage,
                manifest_path=manifest_path,
                manifest_sha256=manifest_sha256,
            )
        except Exception as exc:
            current = self.store.get_run(run_id)
            if current and current.get("status") == "generating":
                self.store.fail_run(run_id, str(exc))
            raise

    def approve(self, run_id: str, note: str | None = None) -> dict[str, Any]:
        run = self._require_reviewable_fresh(run_id)
        model_id = str(run["model_install_id"])
        result = self.store.approve_with_review_gate(
            run_id,
            model_install_id=model_id,
            resume_key=str(run["resume_key"]),
            review_context_sha256=str(run["review_context_sha256"]),
            note=note,
        )
        return {
            "run": result["run"],
            "gate_reset": result["gate_reset"],
            "review_gate": self.models.store.review_gate(model_id),
        }

    def reject(self, run_id: str, note: str | None = None) -> dict[str, Any]:
        run = self.store.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        if run.get("status") == "approved":
            return self.store.reject_with_review_gate(run_id, note)
        if run.get("status") != "needs_review":
            raise RuntimeError("only a pending or approved tailored resume can be rejected")
        return self.store.set_review_status(run_id, "rejected", note)

    def mark_stale_runs(self) -> int:
        count = 0
        for run in self.store.list_runs(100):
            if run.get("status") not in {"needs_review", "auto_validated"}:
                continue
            reason = self._stale_reason(run)
            if reason:
                self.store.set_review_status(str(run["id"]), "stale", reason)
                count += 1
        return count

    def require_review_gate_current(self, model_install_id: str) -> dict[str, Any]:
        state = self.models.store.model_state()
        if str(state.get("selected_model_install_id") or "") != model_install_id:
            raise RuntimeError("selected model changed before automatic tailoring activation")
        master = self.resume_store.get_active_master()
        if master is None or not self._onboarding_ready(master):
            raise RuntimeError("resume onboarding is no longer ready")
        context = self._dependency_context(
            master,
            model_install_id,
            str(state.get("selected_runtime_install_id") or ""),
            str(state.get("selected_device_id") or ""),
        )
        gate = self.models.store.review_gate(model_install_id)
        if not gate.get("complete"):
            raise RuntimeError("five-distinct-resume review gate has not passed")
        if str(gate.get("review_context_sha256") or "") != str(context["review_context_sha256"]):
            raise RuntimeError("five-resume approvals are stale because resume/fact/profile/template validation context changed")
        return context

    def auto_tailoring_is_current(self) -> bool:
        state = self.models.store.model_state()
        model_id = str(state.get("auto_tailoring_model_install_id") or "")
        if not model_id or model_id != str(state.get("selected_model_install_id") or ""):
            return False
        master = self.resume_store.get_active_master()
        if master is None or not self._onboarding_ready(master):
            return False
        try:
            context = self._dependency_context(
                master,
                model_id,
                str(state.get("selected_runtime_install_id") or ""),
                str(state.get("selected_device_id") or ""),
            )
        except Exception:
            return False
        return self._auto_tailoring_current(model_id, str(context["review_context_sha256"]))

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
        self._verify_run_artifacts(run)
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
        try:
            self._approved_current_facts(master)
            self.models.model_installer.require_verified_path(str(run["model_install_id"]))
            self.models.runtime_installer.require_verified_executable(str(run["runtime_install_id"]))
            context = self._dependency_context(
                master,
                str(run["model_install_id"]),
                str(run["runtime_install_id"]),
                str(run["device_id"]),
            )
        except Exception as exc:
            return f"validation evidence changed or failed integrity verification: {str(exc)[:300]}"
        if str(run.get("template_map_sha256") or "") != str(context["template_map_sha256"]):
            return "confirmed template map changed"
        if str(run.get("baseline_sha256") or "") != str(context["baseline_sha256"]):
            return "offline resume baseline changed"
        if str(run.get("profile_sha256") or "") != str(context["profile_sha256"]):
            return "targeting/profile changed"
        if str(run.get("review_context_sha256") or "") != str(context["review_context_sha256"]):
            return "resume/fact/profile/template/model validation context changed"
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
        baseline_rel = str(baseline.get("pdf_relpath") or "")
        baseline_hash = str(baseline.get("pdf_sha256") or "")
        if not baseline_rel or not baseline_hash:
            raise RuntimeError("offline baseline PDF evidence is incomplete")
        baseline_path = (self.paths.root / baseline_rel).resolve(strict=False)
        root = self.paths.root.resolve(strict=False)
        if baseline_path == root or not baseline_path.is_relative_to(root):
            raise RuntimeError("baseline PDF path escaped app-managed storage")
        if not baseline_path.is_file() or sha256_file(baseline_path) != baseline_hash:
            raise RuntimeError("baseline PDF failed integrity verification")

        baseline_pdf = inspect_pdf(baseline_path)
        if baseline.get("text_sha256") and str(baseline_pdf["text_sha256"]) != str(baseline["text_sha256"]):
            raise RuntimeError("baseline PDF extracted-text evidence changed")
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
        if not str(pdf["text"]).strip():
            failures.append("compiled PDF contains no extractable text")

        expected = Counter(_pdf_tokens(str(baseline_pdf["text"])))
        for diff in diffs:
            before = Counter(_pdf_tokens(str(diff["before"])))
            for token, count in before.items():
                expected[token] = max(0, expected[token] - count)
            expected.update(_pdf_tokens(str(diff["after"])))
        actual = Counter(_pdf_tokens(str(pdf["text"])))
        missing = expected - actual
        if missing:
            sample = ", ".join(f"{token}×{count}" for token, count in list(sorted(missing.items()))[:15])
            failures.append("compiled PDF is missing expected baseline/tailored content tokens: " + sample)

        return {
            "overall_pass": not failures,
            "failures": failures,
            "page_count": pdf["page_count"],
            "baseline_page_count": baseline["page_count"],
            "page_sizes": pdf["page_sizes"],
            "pdf_text_sha256": pdf["text_sha256"],
            "baseline_pdf_sha256": baseline_hash,
            "baseline_text_sha256": baseline_pdf["text_sha256"],
            "overflow_detected": bool(OVERFLOW_RE.search(log_text)),
            "offline_compile": True,
            "expected_content_tokens_present": not bool(missing),
            "missing_content_tokens": dict(missing),
            "source_sha256": hashlib.sha256(tailored_text.encode("utf-8")).hexdigest(),
        }

    def _dependency_context(
        self,
        master: Mapping[str, Any],
        model_install_id: str,
        runtime_install_id: str,
        device_id: str,
    ) -> dict[str, Any]:
        if not model_install_id or not runtime_install_id or not device_id:
            raise RuntimeError("selected model configuration is incomplete")
        template_map_sha = self._template_map_fingerprint(str(master["id"]))
        baseline_sha = self._baseline_fingerprint(str(master["id"]))
        profile_sha = self._profile_fingerprint()
        fact_revision = self.resume_store.fact_bank_revision()
        model_evidence = self._model_evidence(model_install_id, runtime_install_id, device_id)
        context = {
            "master_document_id": master["id"],
            "master_sha256": master["sha256"],
            "fact_bank_revision": fact_revision,
            "template_map_sha256": template_map_sha,
            "baseline_sha256": baseline_sha,
            "profile_sha256": profile_sha,
            "model_evidence_sha256": _stable_sha256(model_evidence),
            "model_install_id": model_install_id,
            "runtime_install_id": runtime_install_id,
            "device_id": device_id,
        }
        return {**context, "review_context_sha256": _stable_sha256(context)}

    def _template_map_fingerprint(self, document_id: str) -> str:
        status = self.resume_store.template_map_status(document_id)
        if status != "confirmed":
            raise RuntimeError("template map is no longer confirmed")
        regions = self.resume_store.list_template_regions(document_id)
        payload = {
            "status": status,
            "regions": [
                {
                    "id": item["id"],
                    "ordinal": item["ordinal"],
                    "section_name": item["section_name"],
                    "line_start": item["line_start"],
                    "line_end": item["line_end"],
                    "raw_sha256": item["raw_sha256"],
                    "editable": int(item["editable"]),
                }
                for item in regions
            ],
        }
        return _stable_sha256(payload)

    def _baseline_fingerprint(self, document_id: str) -> str:
        baseline = self.resume_store.get_baseline(document_id)
        if not baseline or baseline.get("status") != "compiled" or not baseline.get("offline_verified"):
            raise RuntimeError("offline-verified resume baseline is no longer ready")
        payload = {
            key: baseline.get(key)
            for key in (
                "status",
                "compiler_version",
                "page_count",
                "page_sizes",
                "pdf_sha256",
                "text_sha256",
                "source_metrics",
                "offline_verified",
                "last_compile_used_network",
            )
        }
        return _stable_sha256(payload)

    def _profile_fingerprint(self) -> str:
        raw = self.resume_store.database.get_json_setting("targeting")
        profile = raw if raw is not None else TargetingSettings().to_dict()
        return _stable_sha256(profile)

    def _model_evidence(self, model_install_id: str, runtime_install_id: str, device_id: str) -> dict[str, Any]:
        model = self.models.store.model_install(model_install_id)
        runtime = self.models.store.runtime_install(runtime_install_id)
        evaluation = self.models.store.best_passing_evaluation(model_install_id)
        if model is None or model.get("status") != "validated":
            raise RuntimeError("selected model validation evidence is missing")
        if runtime is None or runtime.get("status") != "installed":
            raise RuntimeError("selected runtime validation evidence is missing")
        if evaluation is None or not evaluation.get("overall_pass"):
            raise RuntimeError("selected model has no passing evaluation")
        if str(evaluation.get("runtime_install_id")) != runtime_install_id or str(evaluation.get("device_id")) != device_id:
            raise RuntimeError("selected configuration no longer matches its passing evaluation")
        return {
            "model": {
                "id": model_install_id,
                "catalogue_id": model.get("catalogue_id"),
                "source_revision": model.get("source_revision"),
                "artifact_sha256": model.get("artifact_sha256"),
                "artifact_bytes": model.get("artifact_bytes"),
            },
            "runtime": {
                "id": runtime_install_id,
                "catalogue_id": runtime.get("catalogue_id"),
                "version": runtime.get("version"),
                "backend": runtime.get("backend"),
                "artifact_sha256": runtime.get("artifact_sha256"),
            },
            "evaluation": {
                "id": evaluation.get("id"),
                "suite_version": evaluation.get("suite_version"),
                "device_id": evaluation.get("device_id"),
                "context_tokens": evaluation.get("context_tokens"),
                "structured_pass": bool(evaluation.get("structured_pass")),
                "factual_pass": bool(evaluation.get("factual_pass")),
                "tailoring_pass": bool(evaluation.get("tailoring_pass")),
                "resource_pass": bool(evaluation.get("resource_pass")),
                "overall_pass": bool(evaluation.get("overall_pass")),
                "configuration": evaluation.get("configuration") or {},
            },
        }

    def _auto_tailoring_current(self, model_install_id: str, review_context_sha256: str) -> bool:
        state = self.models.store.model_state()
        if str(state.get("auto_tailoring_model_install_id") or "") != model_install_id:
            return False
        gate = self.models.store.review_gate(model_install_id)
        return bool(
            gate.get("complete")
            and str(gate.get("review_context_sha256") or "") == review_context_sha256
        )

    def _verify_run_artifacts(self, run: Mapping[str, Any]) -> None:
        source_rel = str(run.get("source_relpath") or "")
        pdf_rel = str(run.get("pdf_relpath") or "")
        manifest_rel = str(run.get("manifest_relpath") or "")
        if not source_rel or not pdf_rel or not manifest_rel:
            raise RuntimeError("tailored resume audit artifacts are incomplete")
        source = self.store.absolute_path(source_rel)
        pdf = self.store.absolute_path(pdf_rel)
        manifest_path = self.store.absolute_path(manifest_rel)
        if not source.is_file() or sha256_file(source) != str(run.get("source_sha256") or ""):
            raise RuntimeError("tailored LaTeX failed integrity verification")
        if not pdf.is_file() or sha256_file(pdf) != str(run.get("pdf_sha256") or ""):
            raise RuntimeError("tailored PDF failed integrity verification")
        if not manifest_path.is_file() or sha256_file(manifest_path) != str(run.get("manifest_sha256") or ""):
            raise RuntimeError("tailoring audit manifest failed integrity verification")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError("tailoring audit manifest is unreadable") from exc
        if str(manifest.get("run_id")) != str(run["id"]):
            raise RuntimeError("tailoring audit manifest run identity does not match")
        if str(manifest.get("review_context_sha256")) != str(run.get("review_context_sha256") or ""):
            raise RuntimeError("tailoring audit manifest review context does not match")
        components = manifest.get("components")
        if not isinstance(components, dict):
            raise RuntimeError("tailoring audit manifest has no component hashes")
        package = manifest_path.parent.resolve(strict=False)
        for name, evidence in components.items():
            if name not in AUDIT_COMPONENTS or not isinstance(evidence, dict):
                raise RuntimeError("tailoring audit manifest contains an unexpected component")
            component = (package / name).resolve(strict=False)
            if component.parent != package or not component.is_file():
                raise RuntimeError(f"tailoring audit component {name} is missing")
            if sha256_file(component) != str(evidence.get("sha256") or "") or component.stat().st_size != int(evidence.get("bytes") or -1):
                raise RuntimeError(f"tailoring audit component {name} failed integrity verification")
        required = {"resume.tex", "resume.pdf", "jd.txt", "jd.json", "diff.json", "keyword_mapping.json", "fact_references.json", "validation.json", "model.json", "model_usage.json"}
        if not required.issubset(components):
            raise RuntimeError("tailoring audit manifest is missing required evidence files")

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
