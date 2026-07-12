"""Tests for SniperScheduler and DB path resolution."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

import sniper.config as config_module
from sniper.core.db import WatchStore
from sniper.scheduler import SniperScheduler


@pytest.fixture
def temp_db(tmp_path):
    return str(tmp_path / "sniper.db")


@pytest.fixture
def scheduler(temp_db):
    db = WatchStore(temp_db)
    sniper = MagicMock()
    ntp = MagicMock()
    ntp.get_adjusted_time.return_value = datetime.now(timezone.utc)
    return SniperScheduler(db, sniper, ntp)


def test_schedule_watch_uses_serializable_job_functions(scheduler):
    end_time = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

    scheduler.schedule_watch("watch-123", end_time)
    jobs = scheduler.get_scheduled_jobs()

    assert {job["id"] for job in jobs} == {"snipe_watch-123", "check_watch-123"}
    for job in scheduler.scheduler.get_jobs():
        assert job.func_ref in {
            "sniper.scheduler:execute_snipe_job",
            "sniper.scheduler:check_result_job",
        }


@pytest.mark.parametrize("env_value", ["/data/sniper.db", "/data/does-not-matter.db"])
def test_resolve_db_path_falls_back_from_unwritable_data(monkeypatch, tmp_path, env_value):
    monkeypatch.setenv("DB_PATH", env_value)
    monkeypatch.setattr(config_module.os, "access", lambda path, mode: False)
    monkeypatch.setattr(config_module.Path, "exists", lambda self: str(self) != "/data")

    expected = str(config_module.Path(config_module.__file__).parent.parent.parent / "data" / "sniper.db")
    assert config_module._resolve_db_path() == expected
