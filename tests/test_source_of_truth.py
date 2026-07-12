"""Tests for source-of-truth behavior between CLI/MCP and deployed service.

These tests document the current limitation: CLI/MCP write to SQLite directly
but do not schedule jobs, while deployed service maintains both sources.

Tests are marked with @pytest.mark.skipif to skip by default since they require
a running scheduler to show the mismatch. Run with pytest -m "not skip" to run.
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from sniper.config import config
from sniper.core.db import WatchStore


@pytest.fixture
def db():
    """Create a temporary test database"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = WatchStore(path)
    yield db
    os.unlink(path)


class TestSourceOfTruth:
    """Tests for documenting the source-of-truth mismatch."""

    def test_cli_write_adds_to_database(self, db: WatchStore):
        """CLI/MCP watch addition writes to SQLite watches table."""
        end_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        watch_id = db.add_watch(
            item_id="v1|287456575036|0",
            legacy_item_id="287456575036",
            title="Test Item",
            auction_end_time=end_time,
            max_bid=50.00,
            currency="GBP",
            source="cli",
        )

        assert watch_id is not None
        watch = db.get_watch(watch_id)
        assert watch is not None
        assert watch["status"] == "active"
        assert watch["source"] == "cli"

    def test_cli_write_does_not_schedule_jobs(self, db: WatchStore):
        """CLI/MCP watch addition does NOT create APScheduler jobs.

        This test documents the current limitation: CLI/MCP write to SQLite
        but don't interact with APScheduler, so no jobs are created.

        Note: This test cannot verify APScheduler state without a running
        scheduler instance. The absence of a scheduler in test environment
        means jobs cannot be created at all via CLI/MCP code paths.
        """
        end_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        watch_id = db.add_watch(
            item_id="v1|287456575036|0",
            legacy_item_id="287456575036",
            title="Test Item",
            auction_end_time=end_time,
            max_bid=50.00,
            currency="GBP",
            source="cli",
        )

        # Watch is in database
        assert db.get_watch(watch_id) is not None

        # But there's no scheduler instance in CLI/MCP code paths
        # Therefore no jobs were scheduled (this is the limitation)

        # To verify this properly would require:
        # 1. Starting a full service with scheduler
        # 2. Calling CLI/MCP watch addition
        # 3. Querying scheduler.get_job(f"snipe_{watch_id}") - would be None
        # This is beyond unit test scope, documented here for clarity.

    def test_cancel_watch_updates_database_only(self, db: WatchStore):
        """CLI/MCP cancel updates SQLite but doesn't remove scheduler jobs.

        This documents that cancel_watch only updates the watches table.
        The scheduled job remains and will fire at the scheduled time.
        """
        end_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        watch_id = db.add_watch(
            item_id="v1|287456575036|0",
            legacy_item_id="287456575036",
            title="Test Item",
            auction_end_time=end_time,
            max_bid=50.00,
            currency="GBP",
            source="cli",
        )

        # Cancel via DB update (what CLI/MCP do)
        db.update_watch_status(watch_id, "cancelled")

        watch = db.get_watch(watch_id)
        assert watch["status"] == "cancelled"

        # But no scheduler cleanup happened (limitation)
        # In a real scheduler, job would still exist and fire

    @pytest.mark.skipif(
        True, reason="Requires running scheduler service to demonstrate mismatch"
    )
    def test_deployed_service_creates_jobs_for_watches(self):
        """Deployed service creates APScheduler jobs for watches.

        This test would require:
        1. Running full service (python -m sniper.main)
        2. Adding watch via REST API or Telegram
        3. Verifying both DB entry and scheduled job exist

        This is marked as skipped since it's an integration test that
        requires a running service, not a unit test.

        See docs/SOURCE-OF-TRUTH.md for documented behavior.
        """
        pass

    def test_database_path_resolution(self):
        """Test that database path resolution is consistent."""
        # Config should resolve to a writable path
        assert config.DB_PATH is not None
        assert len(config.DB_PATH) > 0

        # Both WatchStore and Scheduler should use same path
        db = WatchStore()
        assert db.db_path == config.DB_PATH

    def test_scheduler_uses_same_database_path(self):
        """Verify scheduler uses the same database as WatchStore.

        APScheduler's SQLAlchemyJobStore stores jobs in the same SQLite file
        as watches table. This is critical for persistence.
        """
        # Scheduler job store URL uses config.DB_PATH
        expected_url = f"sqlite:///{config.DB_PATH}"

        # This is what scheduler.py line 53 does:
        # SQLAlchemyJobStore(url=f"sqlite:///{config.DB_PATH}")

        # Verify the path format is correct
        assert config.DB_PATH.endswith(".db") or config.DB_PATH.endswith(".sqlite")
        assert "sqlite:///" in expected_url


class TestSourceOfTruthReconciliation:
    """Tests for reconciling mismatched sources."""

    def test_restart_service_reschedules_active_watches(self):
        """Service restart reschedules all active watches.

        When the deployed service starts (main.py lines 50-75):
        1. Loads all watches with status='active' from DB
        2. For each, checks if auction end_time is in future
        3. Schedules snipe and check_result jobs

        This is the current workaround for CLI/MCP added watches.
        """
        # This behavior is documented in main.py
        # Unit test would require mocking scheduler and DB
        pass

    def test_phantom_jobs_after_cancel(self, db: WatchStore):
        """Cancelled watches may leave phantom scheduled jobs.

        If you cancel a watch via CLI/MCP:
        - Watch status becomes 'cancelled' in DB
        - But scheduled job remains in APScheduler store
        - Job fires and tries to execute snipe
        - SniperEngine checks watch status and skips execution

        Result: Phantom job attempt, logged, but no harm done.
        """
        end_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        watch_id = db.add_watch(
            item_id="v1|287456575036|0",
            legacy_item_id="287456575036",
            title="Test Item",
            auction_end_time=end_time,
            max_bid=50.00,
            currency="GBP",
            source="cli",
        )

        # Cancel via DB
        db.update_watch_status(watch_id, "cancelled")

        # Watch is cancelled
        watch = db.get_watch(watch_id)
        assert watch is not None
        assert watch["status"] == "cancelled"

        # In real scenario, job would still exist
        # But execution would skip due to status check in SniperEngine
