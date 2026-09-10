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
        with self.database._lock:  # serialized with the shared connection
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
                    status = excluded.status,
                    last_verified_at = excluded.last_verified_at,
                    failure_message = excluded.failure_message,
                    executable_relpath = excluded.executable_relpath
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
    ) -> None:
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO model_installs(
                    id, catalogue_id, source_revision, model_relpath,
                    artifact_sha256, artifact_bytes, status,
                    installed_at, last_verified_at, failure_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    last_verified_at = excluded.last_verified_at,
                    failure_message = excluded.failure_message,
                    artifact_bytes = excluded.artifact_bytes
                """,
                (
                    install_id, catalogue_id, source_revision, model_relpath,
                    artifact_sha256, int(artifact_bytes), status, now, now, failure_message,
                ),
            )

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
        return self._row("SELECT * FROM model_installs WHERE id = ?", install_id)

    def list_runtime_installs(self) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM runtime_installs ORDER BY installed_at, id")

    def list_model_installs(self) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM model_installs ORDER BY installed_at, id")

    def record_evaluation(self, payload: Mapping[str, Any]) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO model_evaluations(
                    id, model_install_id, runtime_install_id, suite_version,
                    backend, context_tokens, elapsed_ms, peak_rss_bytes,
                    structured_pass, factual_pass, tailoring_pass, resource_pass,
                    overall_pass, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"], payload["model_install_id"], payload["runtime_install_id"],
                    payload["suite_version"], payload["backend"], int(payload["context_tokens"]),
                    int(payload["elapsed_ms"]), payload.get("peak_rss_bytes"),
                    int(bool(payload["structured_pass"])), int(bool(payload["factual_pass"])),
                    int(bool(payload["tailoring_pass"])), int(bool(payload["resource_pass"])),
                    int(bool(payload["overall_pass"])), self._json(payload.get("details", {})), utc_now_text(),
                ),
            )

    def latest_evaluation(self, model_install_id: str, runtime_install_id: str | None = None) -> dict[str, Any] | None:
        params: list[object] = [model_install_id]
        sql = "SELECT * FROM model_evaluations WHERE model_install_id = ?"
        if runtime_install_id is not None:
            sql += " AND runtime_install_id = ?"
            params.append(runtime_install_id)
        sql += " ORDER BY created_at DESC LIMIT 1"
        with self.database._lock:
            row = self.database.connection.execute(sql, tuple(params)).fetchone()
        return self._decode_evaluation(row) if row is not None else None

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

    def select_for_review(self, model_install_id: str, runtime_install_id: str) -> None:
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE model_state
                   SET selected_model_install_id=?, selected_runtime_install_id=?, updated_at=?
                 WHERE id=1
                """,
                (model_install_id, runtime_install_id, now),
            )

    def activate_after_review_gate(self, model_install_id: str) -> str | None:
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
    def _decode_evaluation(row: Any) -> dict[str, Any]:
        result = dict(row)
        for key in ("structured_pass", "factual_pass", "tailoring_pass", "resource_pass", "overall_pass"):
            result[key] = bool(result[key])
        result["details"] = json.loads(result.pop("details_json"))
        return result
