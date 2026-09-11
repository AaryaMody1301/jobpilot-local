from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Mapping

from jobpilot.resume.jd import ManualJobDescription
from jobpilot.storage.database import Database, utc_now_text

TAILORED_STATUSES = {
    "generating",
    "needs_review",
    "approved",
    "rejected",
    "auto_validated",
    "blocked",
    "stale",
    "failed",
}


class TailoringStore:
    def __init__(self, database: Database, root: Path) -> None:
        self.database = database
        self.root = root.resolve(strict=False)

    def register_jd(self, jd: ManualJobDescription) -> dict[str, Any]:
        with self.database._lock:
            existing = self.database.connection.execute(
                "SELECT * FROM manual_job_descriptions WHERE jd_sha256=? ORDER BY created_at DESC LIMIT 1",
                (jd.sha256,),
            ).fetchone()
        if existing is not None:
            return dict(existing)
        jd_id = f"jd-{jd.sha256[:16]}"
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO manual_job_descriptions(
                    id, source_url, jd_sha256, jd_text, instruction_like, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (jd_id, jd.source_url, jd.sha256, jd.text, 1 if jd.instruction_like else 0, now, now),
            )
        return self.get_jd(jd_id) or {"id": jd_id}

    def get_jd(self, jd_id: str) -> dict[str, Any] | None:
        with self.database._lock:
            row = self.database.connection.execute(
                "SELECT * FROM manual_job_descriptions WHERE id=?", (jd_id,)
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["instruction_like"] = bool(result["instruction_like"])
        return result

    def list_jds(self, limit: int = 30) -> list[dict[str, Any]]:
        with self.database._lock:
            rows = self.database.connection.execute(
                "SELECT * FROM manual_job_descriptions ORDER BY created_at DESC LIMIT ?", (int(limit),)
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["instruction_like"] = bool(item["instruction_like"])
            result.append(item)
        return result

    def create_run(
        self,
        *,
        jd_id: str,
        master_document_id: str,
        master_sha256: str,
        fact_bank_revision: int,
        model_install_id: str,
        runtime_install_id: str,
        device_id: str,
        resume_key: str,
    ) -> dict[str, Any]:
        run_id = f"tailor-{uuid.uuid4().hex}"
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO tailored_resumes(
                    id, jd_id, master_document_id, master_sha256, fact_bank_revision,
                    model_install_id, runtime_install_id, device_id, resume_key,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'generating', ?, ?)
                """,
                (
                    run_id, jd_id, master_document_id, master_sha256, int(fact_bank_revision),
                    model_install_id, runtime_install_id, device_id, resume_key, now, now,
                ),
            )
        return self.get_run(run_id) or {"id": run_id}

    def complete_run(
        self,
        run_id: str,
        *,
        status: str,
        source_path: Path | None,
        pdf_path: Path | None,
        source_sha256: str | None,
        pdf_sha256: str | None,
        diff: object,
        keyword_mapping: object,
        fact_refs: object,
        validation: object,
        model_usage: object,
        failure_message: str | None = None,
    ) -> dict[str, Any]:
        if status not in TAILORED_STATUSES or status == "generating":
            raise ValueError("invalid completed tailoring status")
        now = utc_now_text()
        with self.database.transaction() as connection:
            updated = connection.execute(
                """
                UPDATE tailored_resumes
                   SET status=?, source_relpath=?, pdf_relpath=?, source_sha256=?, pdf_sha256=?,
                       diff_json=?, keyword_mapping_json=?, fact_refs_json=?, validation_json=?,
                       model_usage_json=?, failure_message=?, updated_at=?
                 WHERE id=?
                """,
                (
                    status,
                    self._relative(source_path) if source_path else None,
                    self._relative(pdf_path) if pdf_path else None,
                    source_sha256,
                    pdf_sha256,
                    self._json(diff),
                    self._json(keyword_mapping),
                    self._json(fact_refs),
                    self._json(validation),
                    self._json(model_usage),
                    failure_message[-2000:] if failure_message else None,
                    now,
                    run_id,
                ),
            ).rowcount
            if updated != 1:
                raise KeyError(run_id)
        return self.get_run(run_id) or {"id": run_id}

    def set_review_status(self, run_id: str, status: str, note: str | None = None) -> dict[str, Any]:
        if status not in {"approved", "rejected", "stale"}:
            raise ValueError("invalid review status")
        now = utc_now_text()
        with self.database.transaction() as connection:
            updated = connection.execute(
                "UPDATE tailored_resumes SET status=?, review_note=?, reviewed_at=?, updated_at=? WHERE id=?",
                (status, (note or "").strip()[:1000] or None, now, now, run_id),
            ).rowcount
            if updated != 1:
                raise KeyError(run_id)
        return self.get_run(run_id) or {"id": run_id}

    def fail_run(self, run_id: str, message: str, *, blocked: bool = False) -> dict[str, Any]:
        status = "blocked" if blocked else "failed"
        return self.complete_run(
            run_id,
            status=status,
            source_path=None,
            pdf_path=None,
            source_sha256=None,
            pdf_sha256=None,
            diff=[],
            keyword_mapping=[],
            fact_refs=[],
            validation={"overall_pass": False, "reason": message[-2000:]},
            model_usage={},
            failure_message=message,
        )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.database._lock:
            row = self.database.connection.execute("SELECT * FROM tailored_resumes WHERE id=?", (run_id,)).fetchone()
        return self._decode_run(row) if row is not None else None

    def list_runs(self, limit: int = 30) -> list[dict[str, Any]]:
        with self.database._lock:
            rows = self.database.connection.execute(
                "SELECT * FROM tailored_resumes ORDER BY created_at DESC LIMIT ?", (int(limit),)
            ).fetchall()
        return [self._decode_run(row) for row in rows]

    def absolute_path(self, relative: str) -> Path:
        resolved = (self.root / relative).resolve(strict=False)
        if resolved == self.root or not resolved.is_relative_to(self.root):
            raise ValueError("tailoring artifact path escaped the app-managed root")
        return resolved

    def _relative(self, path: Path) -> str:
        resolved = path.resolve(strict=False)
        if resolved == self.root or not resolved.is_relative_to(self.root):
            raise ValueError("tailoring artifact path escaped the app-managed root")
        return resolved.relative_to(self.root).as_posix()

    @staticmethod
    def _json(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def _decode_run(cls, row: Any) -> dict[str, Any]:
        result = dict(row)
        for key in ("diff_json", "keyword_mapping_json", "fact_refs_json", "validation_json", "model_usage_json"):
            value = result.pop(key)
            result[key.removesuffix("_json")] = json.loads(value) if value else ([] if key.endswith(("diff_json", "mapping_json", "refs_json")) else {})
        return result
