from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from jobpilot.model.manager import ModelManager
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.storage.database import Database

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def _manager(tmp_path: Path) -> tuple[Database, ModelManager]:
    paths = ManagedPaths(tmp_path / "JobPilotLocal")
    paths.create_all_roots()
    database = Database(paths.database_file, MIGRATIONS)
    database.apply_migrations()
    return database, ModelManager(paths, database)


def test_weekly_update_policy_is_due_only_after_seven_days() -> None:
    assert ModelManager._update_check_due(None) is True
    now = datetime.now(timezone.utc)
    assert ModelManager._update_check_due(now.isoformat()) is False
    assert ModelManager._update_check_due((now - timedelta(days=6, hours=23)).isoformat()) is False
    assert ModelManager._update_check_due((now - timedelta(days=7, seconds=1)).isoformat()) is True


def test_exclusive_operation_prevents_overlapping_local_model_work(tmp_path: Path) -> None:
    database, manager = _manager(tmp_path)
    try:
        with manager._exclusive_operation("first"):
            with pytest.raises(RuntimeError, match="already running"):
                with manager._exclusive_operation("second"):
                    pass
    finally:
        database.close()


def test_cpu_device_is_forced_and_vulkan_device_must_come_from_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database, manager = _manager(tmp_path)
    try:
        assert manager._resolve_device("cpu", "cpu", None) == "none"
        with pytest.raises(RuntimeError, match="device 'none'"):
            manager._resolve_device("cpu", "cpu", "Vulkan0")

        monkeypatch.setattr(
            manager.runtime_installer,
            "list_devices",
            lambda _: {
                "ok": True,
                "devices": [
                    {"id": "Vulkan0", "name": "Integrated GPU"},
                    {"id": "Vulkan1", "name": "Discrete GPU"},
                ],
            },
        )
        with pytest.raises(RuntimeError, match="multiple Vulkan"):
            manager._resolve_device("vulkan", "vulkan", None)
        assert manager._resolve_device("vulkan", "vulkan", "Vulkan1") == "Vulkan1"
        with pytest.raises(RuntimeError, match="not reported"):
            manager._resolve_device("vulkan", "vulkan", "Vulkan9")
    finally:
        database.close()


def test_recommendation_has_no_cloud_or_unsafe_fallback_when_budget_is_too_small(tmp_path: Path) -> None:
    database, manager = _manager(tmp_path)
    try:
        gib = 1024**3
        hardware = {
            "memory": {"total_bytes": 8 * gib},
            "budget": {
                "model_ram_budget_bytes": 2 * gib,
                "model_disk_budget_bytes": 20 * gib,
                "memory_pressure": "normal",
            },
            "gpus": [],
            "runtime_devices": {},
        }
        result = manager._recommend(hardware)
        assert result["model_id"] is None
        assert result["runtime_id"] is None
        assert result["requires_download_approval"] is False
        assert "no tested catalogue model fits" in result["reason"]
    finally:
        database.close()
