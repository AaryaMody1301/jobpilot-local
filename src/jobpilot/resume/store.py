from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping

from jobpilot.storage.database import Database, utc_now_text

FACT_CATEGORIES = {
    "experience_bullet",
    "employer",
    "title",
    "date",
    "metric",
    "qualification",
    "skill",
    "responsibility",
    "notice_period",
    "location",
    "other",
}
FACT_STATUSES = {"candidate", "approved", "rejected"}


class ResumeStore:
    def __init__(self, database: Database, root: Path) -> None:
        self.database = database
        self.root = root.resolve(strict=False)

    def _query_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self.database._lock:
            row = self.database.connection.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    def _query_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.database._lock:
            rows = self.database.connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def _relative(self, path: Path) -> str:
        return path.resolve(strict=False).relative_to(self.root).as_posix()

    def _absolute(self, relative: str) -> Path:
        path = (self.root / relative).resolve(strict=False)
        path.relative_to(self.root)
        return path

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        return self._query_one("SELECT * FROM source_documents WHERE id = ?", (document_id,))

    def get_active_master(self) -> dict[str, Any] | None:
        return self._query_one(
            "SELECT * FROM source_documents WHERE kind = 'master_resume' AND active = 1 ORDER BY imported_at DESC LIMIT 1"
        )

    def find_document_by_digest(self, kind: str, sha256: str) -> dict[str, Any] | None:
        return self._query_one("SELECT * FROM source_documents WHERE kind = ? AND sha256 = ?", (kind, sha256))

    def register_document(
        self,
        *,
        document_id: str,
        kind: str,
        original_name: str,
        stored_path: Path,
        sha256: str,
        byte_size: int,
        media_type: str,
    ) -> None:
        if kind not in {"master_resume", "supporting"}:
            raise ValueError("unsupported document kind")
        now = utc_now_text()
        with self.database.transaction() as connection:
            if kind == "master_resume":
                connection.execute("UPDATE source_documents SET active = 0 WHERE kind = 'master_resume' AND active = 1")
            connection.execute(
                """
                INSERT INTO source_documents(
                    id, kind, original_name, stored_relpath, sha256, byte_size,
                    media_type, imported_at, active, integrity_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'verified')
                """,
                (document_id, kind, original_name, self._relative(stored_path), sha256, byte_size, media_type, now),
            )
            if kind == "master_resume":
                connection.execute(
                    "INSERT INTO template_maps(document_id, status, updated_at) VALUES (?, 'candidate', ?)",
                    (document_id, now),
                )

    def activate_existing_master(self, document_id: str) -> None:
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute("UPDATE source_documents SET active = 0 WHERE kind = 'master_resume' AND active = 1")
            updated = connection.execute(
                "UPDATE source_documents SET active = 1, integrity_status = 'verified' WHERE id = ? AND kind = 'master_resume'",
                (document_id,),
            ).rowcount
            if updated != 1:
                raise KeyError(document_id)
            connection.execute("UPDATE template_maps SET updated_at = ? WHERE document_id = ?", (now, document_id))

    def document_path(self, document: Mapping[str, Any]) -> Path:
        return self._absolute(str(document["stored_relpath"]))

    def set_integrity(self, document_id: str, status: str) -> None:
        if status not in {"verified", "mismatch", "missing"}:
            raise ValueError("invalid integrity status")
        with self.database.transaction() as connection:
            connection.execute("UPDATE source_documents SET integrity_status = ? WHERE id = ?", (status, document_id))

    def list_documents(self, kind: str | None = None) -> list[dict[str, Any]]:
        if kind is None:
            return self._query_all("SELECT * FROM source_documents ORDER BY imported_at DESC")
        return self._query_all("SELECT * FROM source_documents WHERE kind = ? ORDER BY imported_at DESC", (kind,))

    def add_template_regions(self, document_id: str, regions: Iterable[Mapping[str, Any]]) -> None:
        now = utc_now_text()
        with self.database.transaction() as connection:
            for region in regions:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO template_regions(
                        id, document_id, ordinal, section_name, line_start, line_end,
                        raw_sha256, display_text, editable, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                    """,
                    (
                        region["region_id"], document_id, region["ordinal"], region["section"],
                        region["line_start"], region["line_end"], region["raw_sha256"],
                        region["plain_text"], now, now,
                    ),
                )

    def list_template_regions(self, document_id: str) -> list[dict[str, Any]]:
        return self._query_all(
            """
            SELECT id, document_id, ordinal, section_name, line_start, line_end,
                   raw_sha256, display_text, editable, created_at, updated_at
              FROM template_regions WHERE document_id = ? ORDER BY ordinal
            """,
            (document_id,),
        )

    def set_region_editable(self, region_id: str, editable: bool) -> None:
        now = utc_now_text()
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT document_id, editable FROM template_regions WHERE id = ?",
                (region_id,),
            ).fetchone()
            if row is None:
                raise KeyError(region_id)
            new_value = 1 if editable else 0
            if int(row["editable"]) == new_value:
                return
            connection.execute(
                "UPDATE template_regions SET editable = ?, updated_at = ? WHERE id = ?",
                (new_value, now, region_id),
            )
            connection.execute(
                "UPDATE template_maps SET status = 'candidate', confirmed_at = NULL, updated_at = ? WHERE document_id = ?",
                (now, row["document_id"]),
            )

    def template_map_status(self, document_id: str) -> str:
        row = self._query_one("SELECT status FROM template_maps WHERE document_id = ?", (document_id,))
        return str(row["status"]) if row else "missing"

    def confirm_template_map(self, document_id: str) -> None:
        regions = self.list_template_regions(document_id)
        if not regions:
            raise ValueError("no candidate editable regions were detected; review the template before confirming")
        if not any(bool(region["editable"]) for region in regions):
            raise ValueError("mark at least one wording region editable before confirming the template map")
        now = utc_now_text()
        with self.database.transaction() as connection:
            updated = connection.execute(
                "UPDATE template_maps SET status = 'confirmed', confirmed_at = ?, updated_at = ? WHERE document_id = ?",
                (now, now, document_id),
            ).rowcount
            if updated != 1:
                raise KeyError(document_id)

    def fact_bank_revision(self) -> int:
        row = self._query_one("SELECT revision FROM fact_bank_state WHERE id = 1")
        return int(row["revision"]) if row else 0

    def _bump_fact_bank(self, connection: Any) -> None:
        connection.execute("UPDATE fact_bank_state SET revision = revision + 1, updated_at = ? WHERE id = 1", (utc_now_text(),))

    def create_fact(
        self,
        *,
        value: str,
        category: str,
        source_document_id: str,
        source_ref: Mapping[str, Any],
        fact_id: str | None = None,
    ) -> str:
        value = value.strip()
        if not value or len(value) > 2000:
            raise ValueError("fact value must contain 1-2000 characters")
        if category not in FACT_CATEGORIES:
            raise ValueError("unsupported fact category")
        document = self.get_document(source_document_id)
        if document is None:
            raise KeyError(source_document_id)
        fact_id = fact_id or f"fact-{uuid.uuid4().hex}"
        now = utc_now_text()
        encoded_ref = json.dumps(dict(source_ref), sort_keys=True, separators=(",", ":"))
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO facts(id, current_version, current_status, current_category, created_at, updated_at) VALUES (?, 1, 'candidate', ?, ?, ?)",
                (fact_id, category, now, now),
            )
            connection.execute(
                """
                INSERT INTO fact_versions(fact_id, version, value_text, category, status, source_document_id, source_ref_json, created_at)
                VALUES (?, 1, ?, ?, 'candidate', ?, ?, ?)
                """,
                (fact_id, value, category, source_document_id, encoded_ref, now),
            )
            self._bump_fact_bank(connection)
        return fact_id

    def create_candidate_facts_for_regions(self, document_id: str, source_sha256: str) -> int:
        created = 0
        for region in self.list_template_regions(document_id):
            fact_id = f"fact-{source_sha256[:12]}-{int(region['ordinal']):03d}"
            if self._query_one("SELECT id FROM facts WHERE id = ?", (fact_id,)):
                continue
            section = str(region.get("section_name", "")).casefold()
            if "education" in section or "qualification" in section:
                category = "qualification"
            elif "skill" in section or "technology" in section:
                category = "skill"
            elif "experience" in section or "employment" in section or "project" in section:
                category = "experience_bullet"
            else:
                category = "other"
            self.create_fact(
                fact_id=fact_id,
                value=str(region["display_text"]),
                category=category,
                source_document_id=document_id,
                source_ref={
                    "kind": "latex_region",
                    "region_id": region["id"],
                    "line_start": region["line_start"],
                    "line_end": region["line_end"],
                    "source_sha256": source_sha256,
                },
            )
            created += 1
        return created

    def list_facts(self) -> list[dict[str, Any]]:
        rows = self._query_all(
            """
            SELECT f.id, f.current_version, f.current_status, f.current_category,
                   v.value_text, v.source_document_id, v.source_ref_json,
                   d.original_name AS source_name, f.updated_at
              FROM facts f
              JOIN fact_versions v ON v.fact_id = f.id AND v.version = f.current_version
              JOIN source_documents d ON d.id = v.source_document_id
             ORDER BY f.created_at, f.id
            """
        )
        for row in rows:
            row["source_ref"] = json.loads(row.pop("source_ref_json"))
        return rows

    def revise_fact(self, fact_id: str, *, value: str, category: str) -> None:
        value = value.strip()
        if not value or len(value) > 2000:
            raise ValueError("fact value must contain 1-2000 characters")
        if category not in FACT_CATEGORIES:
            raise ValueError("unsupported fact category")
        current = self._query_one(
            """
            SELECT f.current_version, v.source_document_id, v.source_ref_json
              FROM facts f JOIN fact_versions v ON v.fact_id = f.id AND v.version = f.current_version
             WHERE f.id = ?
            """,
            (fact_id,),
        )
        if current is None:
            raise KeyError(fact_id)
        new_version = int(current["current_version"]) + 1
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO fact_versions(fact_id, version, value_text, category, status, source_document_id, source_ref_json, created_at)
                VALUES (?, ?, ?, ?, 'candidate', ?, ?, ?)
                """,
                (fact_id, new_version, value, category, current["source_document_id"], current["source_ref_json"], now),
            )
            connection.execute(
                "UPDATE facts SET current_version = ?, current_status = 'candidate', current_category = ?, updated_at = ? WHERE id = ?",
                (new_version, category, now, fact_id),
            )
            self._bump_fact_bank(connection)

    def set_fact_status(self, fact_id: str, status: str) -> None:
        if status not in FACT_STATUSES:
            raise ValueError("invalid fact status")
        current = self._query_one("SELECT current_version FROM facts WHERE id = ?", (fact_id,))
        if current is None:
            raise KeyError(fact_id)
        version = int(current["current_version"])
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute("UPDATE fact_versions SET status = ? WHERE fact_id = ? AND version = ?", (status, fact_id, version))
            connection.execute("UPDATE facts SET current_status = ?, updated_at = ? WHERE id = ?", (status, now, fact_id))
            self._bump_fact_bank(connection)

    def fact_versions(self, fact_id: str) -> list[dict[str, Any]]:
        rows = self._query_all("SELECT * FROM fact_versions WHERE fact_id = ? ORDER BY version", (fact_id,))
        for row in rows:
            row["source_ref"] = json.loads(row.pop("source_ref_json"))
        return rows

    def upsert_baseline(self, document_id: str, values: Mapping[str, Any]) -> None:
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO resume_baselines(
                    document_id, status, compiler_version, page_count, page_sizes_json,
                    pdf_relpath, pdf_sha256, text_sha256, source_metrics_json,
                    compile_log_relpath, compile_error, offline_verified,
                    last_compile_used_network, compiled_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    status = excluded.status,
                    compiler_version = excluded.compiler_version,
                    page_count = excluded.page_count,
                    page_sizes_json = excluded.page_sizes_json,
                    pdf_relpath = excluded.pdf_relpath,
                    pdf_sha256 = excluded.pdf_sha256,
                    text_sha256 = excluded.text_sha256,
                    source_metrics_json = excluded.source_metrics_json,
                    compile_log_relpath = excluded.compile_log_relpath,
                    compile_error = excluded.compile_error,
                    offline_verified = excluded.offline_verified,
                    last_compile_used_network = excluded.last_compile_used_network,
                    compiled_at = excluded.compiled_at,
                    updated_at = excluded.updated_at
                """,
                (
                    document_id,
                    values.get("status"), values.get("compiler_version"), values.get("page_count"),
                    json.dumps(values.get("page_sizes"), separators=(",", ":")) if values.get("page_sizes") is not None else None,
                    values.get("pdf_relpath"), values.get("pdf_sha256"), values.get("text_sha256"),
                    json.dumps(values.get("source_metrics"), sort_keys=True, separators=(",", ":")) if values.get("source_metrics") is not None else None,
                    values.get("compile_log_relpath"), values.get("compile_error"),
                    1 if values.get("offline_verified") else 0,
                    1 if values.get("last_compile_used_network") else 0,
                    values.get("compiled_at"), now,
                ),
            )

    def get_baseline(self, document_id: str) -> dict[str, Any] | None:
        row = self._query_one("SELECT * FROM resume_baselines WHERE document_id = ?", (document_id,))
        if row is None:
            return None
        row["page_sizes"] = json.loads(row.pop("page_sizes_json")) if row.get("page_sizes_json") else None
        row["source_metrics"] = json.loads(row.pop("source_metrics_json")) if row.get("source_metrics_json") else None
        return row
