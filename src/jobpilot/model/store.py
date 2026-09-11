from __future__ import annotations

import json
from typing import Any, Mapping

from jobpilot.storage.database import Database, utc_now_text


class ModelStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    def record_hardware(self, snapshot: Mapping[str, Any]) -> int:
        now = utc_now_text()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO hardware_snapshots(
                    captured_at, platform_json, memory_json, cpu_json,
                    disk_json, gpu_json, budget_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    self._json(snapshot.get("platform", {})),
                    self._json(snapshot.get("memory", {})),
                    self._json(snapshot.get("cpu", {})),
                    self._json(snapshot.get("disk", {})),
                    self._json(snapshot.get("gpus", [])),
                    self._json(snapshot.get("budget", {})),
                ),
            )
            return int(cursor.lastrowid)

    def latest_hardware(self) -> dict[str, Any] | None:
        with self.database._lock:
            row = self.database.connection.execute(
                "SELECT * FROM hardware_snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return {
            "id": int(row["id"]),
            "captured_at": row["captured_at"],
            "platform": json.loads(row["platform_json"]),
            "memory": json.loads(row["memory_json"]),
            "cpu": json.loads(row["cpu_json"]),
            "disk": json.loads(row["disk_json"]),
            "gpus": json.loads(row["gpu_json"]),
            "budget": json.loads(row["budget_json"]),
        }

    def upsert_runtime_install(
        self,
        *,
        install_id: str,
        catalogue_id: str,
        version: str,
        backend: str,
        install_relpath: str,
        executable_relpath: str,
        artifact_sha256: str,
        status: str,
        failure_message: str | None = None,
    ) -> None:
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO runtime_installs(
                    id, catalogue_id, version, backend, install_relpath,
                    executable_relpath, artifact_sha256, status,
                    installed_at, last_verified_at, failure_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    catalogue_id = excluded.catalogue_id,
                    version = excluded.version,
                    backend = excluded.backend,
                    status = excluded.status,
                    last_verified_at = excluded.last_verified_at,
                    failure_message = excluded.failure_message,
                    install_relpath = excluded.install_relpath,
                    executable_relpath = excluded.executable_relpath,
                    artifact_sha256 = excluded.artifact_sha256
                """,
                (
                    install_id, catalogue_id, version, backend, install_relpath,
                    executable_relpath, artifact_sha256, status, now, now, failure_message,
                ),
            )

    def upsert_model_install(
        self,
        *,
        install_id: str,
        catalogue_id: str,
        source_revision: str,
        model_relpath: str,
        artifact_sha256: str,
        artifact_bytes: int,
        status: str,
        failure_message: str | None = None,
        app_managed: bool = True,
    ) -> None:
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO model_installs(
                    id, catalogue_id, source_revision, model_relpath,
                    artifact_sha256, artifact_bytes, app_managed, status,
                    installed_at, last_verified_at, failure_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    catalogue_id = excluded.catalogue_id,
                    source_revision = excluded.source_revision,
                    model_relpath = excluded.model_relpath,
                    artifact_sha256 = excluded.artifact_sha256,
                    artifact_bytes = excluded.artifact_bytes,
                    app_managed = excluded.app_managed,
                    status = excluded.status,
                    last_verified_at = excluded.last_verified_at,
                    failure_message = excluded.failure_message
                """,
                (
                    install_id, catalogue_id, source_revision, model_relpath,
                    artifact_sha256, int(artifact_bytes), int(bool(app_managed)), status,
                    now, now, failure_message,
                ),
            )

    def find_model_install(self, catalogue_id: str, source_revision: str) -> dict[str, Any] | None:
        with self.database._lock:
            row = self.database.connection.execute(
                "SELECT * FROM model_installs WHERE catalogue_id=? AND source_revision=? ORDER BY installed_at DESC LIMIT 1",
                (catalogue_id, source_revision),
            ).fetchone()
        return self._decode_model_row(row) if row is not None else None

    def set_model_status(self, install_id: str, status: str, failure_message: str | None = None) -> None:
        with self.database.transaction() as connection:
            updated = connection.execute(
                "UPDATE model_installs SET status=?, failure_message=?, last_verified_at=? WHERE id=?",
                (status, failure_message, utc_now_text(), install_id),
            ).rowcount
            if updated != 1:
                raise KeyError(install_id)

    def runtime_install(self, install_id: str) -> dict[str, Any] | None:
        return self._row("SELECT * FROM runtime_installs WHERE id = ?", install_id)

    def model_install(self, install_id: str) -> dict[str, Any] | None:
        with self.database._lock:
            row = self.database.connection.execute("SELECT * FROM model_installs WHERE id = ?", (install_id,)).fetchone()
        return self._decode_model_row(row) if row is not None else None

    def list_runtime_installs(self) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM runtime_installs ORDER BY installed_at, id")

    def list_model_installs(self) -> list[dict[str, Any]]:
        with self.database._lock:
            rows = self.database.connection.execute("SELECT * FROM model_installs ORDER BY installed_at, id").fetchall()
        return [self._decode_model_row(row) for row in rows]

    def record_evaluation(self, payload: Mapping[str, Any]) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO model_evaluations(
                    id, model_install_id, runtime_install_id, suite_version,
                    backend, device_id, context_tokens, elapsed_ms, peak_rss_bytes,
                    generation_tokens_per_second, prompt_tokens_per_second,
                    structured_pass, factual_pass, tailoring_pass, resource_pass,
                    overall_pass, configuration_json, pressure_json, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"], payload["model_install_id"], payload["runtime_install_id"],
                    payload["suite_version"], payload["backend"], str(payload.get("device_id") or "none"),
                    int(payload["context_tokens"]), int(payload["elapsed_ms"]), payload.get("peak_rss_bytes"),
                    payload.get("generation_tokens_per_second"), payload.get("prompt_tokens_per_second"),
                    int(bool(payload["structured_pass"])), int(bool(payload["factual_pass"])),
                    int(bool(payload["tailoring_pass"])), int(bool(payload["resource_pass"])),
                    int(bool(payload["overall_pass"])), self._json(payload.get("configuration", {})),
                    self._json(payload.get("pressure", {})), self._json(payload.get("details", {})), utc_now_text(),
                ),
            )

    def latest_evaluation(
        self,
        model_install_id: str,
        runtime_install_id: str | None = None,
        device_id: str | None = None,
    ) -> dict[str, Any] | None:
        params: list[object] = [model_install_id]
        sql = "SELECT * FROM model_evaluations WHERE model_install_id = ?"
        if runtime_install_id is not None:
            sql += " AND runtime_install_id = ?"
            params.append(runtime_install_id)
        if device_id is not None:
            sql += " AND device_id = ?"
            params.append(device_id)
        sql += " ORDER BY created_at DESC LIMIT 1"
        with self.database._lock:
            row = self.database.connection.execute(sql, tuple(params)).fetchone()
        return self._decode_evaluation(row) if row is not None else None

    def best_passing_evaluation(self, model_install_id: str) -> dict[str, Any] | None:
        with self.database._lock:
            rows = self.database.connection.execute(
                "SELECT * FROM model_evaluations WHERE model_install_id=? AND overall_pass=1 ORDER BY created_at DESC",
                (model_install_id,),
            ).fetchall()
        if not rows:
            return None
        decoded = [self._decode_evaluation(row) for row in rows]
        return max(
            decoded,
            key=lambda row: (
                float(row.get("generation_tokens_per_second") or 0.0),
                -int(row.get("elapsed_ms") or 0),
            ),
        )

    def list_evaluations(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.database._lock:
            rows = self.database.connection.execute(
                "SELECT * FROM model_evaluations ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._decode_evaluation(row) for row in rows]

    def model_state(self) -> dict[str, Any]:
        with self.database._lock:
            row = self.database.connection.execute("SELECT * FROM model_state WHERE id = 1").fetchone()
        if row is None:
            raise RuntimeError("model_state singleton is missing")
        return dict(row)

    def select_for_review(self, model_install_id: str, runtime_install_id: str, device_id: str) -> None:
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE model_state
                   SET selected_model_install_id=?, selected_runtime_install_id=?, selected_device_id=?, updated_at=?
                 WHERE id=1
                """,
                (model_install_id, runtime_install_id, device_id, now),
            )
        self.ensure_review_gate(model_install_id)

    def ensure_review_gate(self, model_install_id: str) -> dict[str, Any]:
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO model_review_gates(
                    model_install_id, required_distinct_resumes, created_at, updated_at
                ) VALUES (?, 5, ?, ?)
                """,
                (model_install_id, now, now),
            )
        return self.review_gate(model_install_id)

    def review_gate(self, model_install_id: str) -> dict[str, Any]:
        with self.database._lock:
            gate = self.database.connection.execute(
                "SELECT * FROM model_review_gates WHERE model_install_id=?", (model_install_id,)
            ).fetchone()
            approved = self.database.connection.execute(
                "SELECT COUNT(*) FROM model_review_approvals WHERE model_install_id=?", (model_install_id,)
            ).fetchone()[0]
        if gate is None:
            return {
                "model_install_id": model_install_id,
                "required_distinct_resumes": 5,
                "approved_distinct_resumes": 0,
                "remaining": 5,
                "complete": False,
                "invalidated": False,
                "invalidation_reason": None,
            }
        result = dict(gate)
        required = int(result["required_distinct_resumes"])
        result["approved_distinct_resumes"] = int(approved)
        result["remaining"] = max(0, required - int(approved))
        result["invalidated"] = bool(result.get("invalidated_at"))
        result["complete"] = bool(result.get("completed_at")) and not result["invalidated"] and int(approved) >= required
        return result

    def record_review_approval(self, model_install_id: str, resume_key: str) -> dict[str, Any]:
        key = resume_key.strip()
        if not key:
            raise ValueError("resume review key must be non-empty")
        if self.model_install(model_install_id) is None:
            raise KeyError(model_install_id)
        self.ensure_review_gate(model_install_id)
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO model_review_approvals(model_install_id, resume_key, approved_at) VALUES (?, ?, ?)",
                (model_install_id, key, now),
            )
            count = int(connection.execute(
                "SELECT COUNT(*) FROM model_review_approvals WHERE model_install_id=?", (model_install_id,)
            ).fetchone()[0])
            if count >= 5:
                connection.execute(
                    "UPDATE model_review_gates SET completed_at=?, invalidated_at=NULL, invalidation_reason=NULL, updated_at=? WHERE model_install_id=?",
                    (now, now, model_install_id),
                )
        return self.review_gate(model_install_id)

    def invalidate_review_gate(self, model_install_id: str, reason: str) -> dict[str, Any]:
        message = reason.strip()
        if not message:
            raise ValueError("review-gate invalidation requires a reason")
        self.ensure_review_gate(model_install_id)
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM model_review_approvals WHERE model_install_id=?", (model_install_id,))
            connection.execute(
                "UPDATE model_review_gates SET completed_at=NULL, invalidated_at=?, invalidation_reason=?, updated_at=? WHERE model_install_id=?",
                (now, message, now, model_install_id),
            )
        return self.review_gate(model_install_id)

    def activate_after_review_gate(self, model_install_id: str) -> str | None:
        gate = self.review_gate(model_install_id)
        if not gate["complete"]:
            raise RuntimeError("five-distinct-resume review gate is not complete")
        now = utc_now_text()
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT auto_tailoring_model_install_id FROM model_state WHERE id=1"
            ).fetchone()
            previous = row[0] if row else None
            connection.execute(
                """
                UPDATE model_state
                   SET previous_auto_model_install_id=auto_tailoring_model_install_id,
                       auto_tailoring_model_install_id=?, updated_at=?
                 WHERE id=1
                """,
                (model_install_id, now),
            )
        return str(previous) if previous else None

    def rollback_auto_model(self, failed_model_install_id: str) -> str:
        now = utc_now_text()
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT auto_tailoring_model_install_id, previous_auto_model_install_id FROM model_state WHERE id=1"
            ).fetchone()
            if row is None or row["auto_tailoring_model_install_id"] != failed_model_install_id:
                raise RuntimeError("failed model is not the current auto-tailoring model")
            previous = row["previous_auto_model_install_id"]
            if not previous:
                raise RuntimeError("no previous auto-tailoring model is available for rollback")
            connection.execute(
                """
                UPDATE model_state
                   SET auto_tailoring_model_install_id=?,
                       previous_auto_model_install_id=?,
                       updated_at=?
                 WHERE id=1
                """,
                (previous, failed_model_install_id, now),
            )
        return str(previous)

    def set_cleanup_pending(self, relpath: str | None) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE model_state SET cleanup_pending_relpath=?, updated_at=? WHERE id=1",
                (relpath, utc_now_text()),
            )

    def record_catalogue_check(self, payload: Mapping[str, Any]) -> None:
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE model_state SET last_catalogue_check_at=?, last_catalogue_check_json=?, updated_at=? WHERE id=1",
                (now, self._json(payload), now),
            )

    def _row(self, sql: str, value: str) -> dict[str, Any] | None:
        with self.database._lock:
            row = self.database.connection.execute(sql, (value,)).fetchone()
        return dict(row) if row is not None else None

    def _rows(self, sql: str) -> list[dict[str, Any]]:
        with self.database._lock:
            rows = self.database.connection.execute(sql).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _json(value: object) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _decode_model_row(row: Any) -> dict[str, Any]:
        result = dict(row)
        result["app_managed"] = bool(result.get("app_managed", 0))
        return result

    @staticmethod
    def _decode_evaluation(row: Any) -> dict[str, Any]:
        result = dict(row)
        for key in ("structured_pass", "factual_pass", "tailoring_pass", "resource_pass", "overall_pass"):
            result[key] = bool(result[key])
        result["configuration"] = json.loads(result.pop("configuration_json"))
        result["pressure"] = json.loads(result.pop("pressure_json"))
        result["details"] = json.loads(result.pop("details_json"))
        return result
