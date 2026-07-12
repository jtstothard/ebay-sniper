"""Unit tests for WatchStore (db.py)"""

import os
import tempfile
import pytest
from datetime import datetime, timezone

from sniper.core.db import WatchStore


@pytest.fixture
def db():
    """Create a temporary test database"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = WatchStore(path)
    yield db
    # Cleanup
    os.unlink(path)


def test_add_watch(db: WatchStore):
    """Test adding a watch"""
    watch_id = db.add_watch(
        item_id="v1|287456575036|0",
        legacy_item_id="287456575036",
        title="Test Item",
        auction_end_time="2025-01-01T12:00:00Z",
        max_bid=50.00,
        currency="GBP",
        source="test",
    )

    assert watch_id is not None
    assert len(watch_id) == 36  # UUID length


def test_get_watch(db: WatchStore):
    """Test retrieving a watch"""
    watch_id = db.add_watch(
        item_id="v1|287456575036|0",
        legacy_item_id="287456575036",
        title="Test Item",
        auction_end_time="2025-01-01T12:00:00Z",
        max_bid=50.00,
        currency="GBP",
        source="test",
    )

    watch = db.get_watch(watch_id)

    assert watch is not None
    assert watch["id"] == watch_id
    assert watch["item_id"] == "v1|287456575036|0"
    assert watch["title"] == "Test Item"
    assert watch["max_bid"] == 50.00
    assert watch["status"] == "active"


def test_get_watch_not_found(db: WatchStore):
    """Test retrieving a non-existent watch"""
    watch = db.get_watch("nonexistent")
    assert watch is None


def test_list_watches(db: WatchStore):
    """Test listing watches"""
    db.add_watch(
        item_id="v1|287456575036|0",
        legacy_item_id="287456575036",
        title="Test Item 1",
        auction_end_time="2025-01-01T12:00:00Z",
        max_bid=50.00,
        currency="GBP",
        source="test",
    )

    db.add_watch(
        item_id="v1|287456575037|0",
        legacy_item_id="287456575037",
        title="Test Item 2",
        auction_end_time="2025-01-01T13:00:00Z",
        max_bid=75.00,
        currency="GBP",
        source="test",
    )

    watches = db.list_watches()

    assert len(watches) == 2


def test_list_watches_by_status(db: WatchStore):
    """Test listing watches filtered by status"""
    watch_id1 = db.add_watch(
        item_id="v1|287456575036|0",
        legacy_item_id="287456575036",
        title="Test Item 1",
        auction_end_time="2025-01-01T12:00:00Z",
        max_bid=50.00,
        currency="GBP",
        source="test",
    )

    watch_id2 = db.add_watch(
        item_id="v1|287456575037|0",
        legacy_item_id="287456575037",
        title="Test Item 2",
        auction_end_time="2025-01-01T13:00:00Z",
        max_bid=75.00,
        currency="GBP",
        source="test",
    )

    db.update_watch_status(watch_id1, "cancelled")

    active_watches = db.list_watches("active")
    cancelled_watches = db.list_watches("cancelled")

    assert len(active_watches) == 1
    assert len(cancelled_watches) == 1


def test_update_watch_status(db: WatchStore):
    """Test updating watch status"""
    watch_id = db.add_watch(
        item_id="v1|287456575036|0",
        legacy_item_id="287456575036",
        title="Test Item",
        auction_end_time="2025-01-01T12:00:00Z",
        max_bid=50.00,
        currency="GBP",
        source="test",
    )

    success = db.update_watch_status(watch_id, "cancelled")

    assert success is True

    watch = db.get_watch(watch_id)
    assert watch["status"] == "cancelled"


def test_update_watch_bid(db: WatchStore):
    """Test updating watch bid information"""
    watch_id = db.add_watch(
        item_id="v1|287456575036|0",
        legacy_item_id="287456575036",
        title="Test Item",
        auction_end_time="2025-01-01T12:00:00Z",
        max_bid=50.00,
        currency="GBP",
        source="test",
    )

    success = db.update_watch_bid(watch_id, bid_placed=1, bid_amount=45.50)

    assert success is True

    watch = db.get_watch(watch_id)
    assert watch["bid_placed"] == 1
    assert watch["bid_amount"] == 45.50


def test_log_event(db: WatchStore):
    """Test logging events"""
    watch_id = db.add_watch(
        item_id="v1|287456575036|0",
        legacy_item_id="287456575036",
        title="Test Item",
        auction_end_time="2025-01-01T12:00:00Z",
        max_bid=50.00,
        currency="GBP",
        source="test",
    )

    db.log_event(watch_id, "bid_placed", {"amount": 45.50})

    log = db.get_bid_log(watch_id)

    assert len(log) == 1
    assert log[0]["event"] == "bid_placed"
    assert log[0]["watch_id"] == watch_id


def test_get_watch_by_item_id(db: WatchStore):
    """Test retrieving a watch by eBay item ID"""
    db.add_watch(
        item_id="v1|287456575036|0",
        legacy_item_id="287456575036",
        title="Test Item",
        auction_end_time="2025-01-01T12:00:00Z",
        max_bid=50.00,
        currency="GBP",
        source="test",
    )

    watch = db.get_watch_by_item_id("v1|287456575036|0")

    assert watch is not None
    assert watch["item_id"] == "v1|287456575036|0"


def test_token_storage(db: WatchStore):
    """Test storing and retrieving OAuth tokens"""
    db.store_token(
        token_type="application",
        environment="production",
        access_token="test_access_token",
        refresh_token=None,
        expires_at="2025-12-31T23:59:59Z",
        scope="https://api.ebay.com/oauth/api_scope",
    )

    token = db.get_token("application", "production")

    assert token is not None
    assert token["access_token"] == "test_access_token"
    assert token["environment"] == "production"