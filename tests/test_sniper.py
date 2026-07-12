"""Unit tests for SniperEngine"""

import os
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock

from sniper.core.db import WatchStore
from sniper.core.ebay_client import eBayClient
from sniper.core.sniper import SniperEngine
from sniper.core.ntp import NTPSync


@pytest.fixture
def db():
    """Create a temporary test database"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = WatchStore(path)
    yield db
    os.unlink(path)


@pytest.fixture
def mock_ebay_client():
    """Mock eBay client"""
    client = AsyncMock(spec=eBayClient)
    return client


@pytest.fixture
def ntp():
    """Create NTPSync instance"""
    ntp = NTPSync()
    ntp.offset = 0.0
    ntp.synced = True
    return ntp


@pytest.fixture
def sniper(db, mock_ebay_client, ntp):
    """Create SniperEngine instance"""
    return SniperEngine(db, mock_ebay_client, ntp)


@pytest.mark.asyncio
async def test_add_watch(sniper: SniperEngine, mock_ebay_client):
    """Test adding a watch"""
    # Mock eBay API response
    mock_ebay_client.get_item.return_value = {
        "itemId": "v1|287456575036|0",
        "title": "Test Item",
        "itemEndDate": "2099-12-31T23:59:59.000Z",
        "price": {"value": "30.00", "currency": "GBP"},
    }

    watch = await sniper.add_watch(
        item_id="287456575036", max_bid=50.00, source="test"
    )

    assert watch is not None
    assert watch["title"] == "Test Item"
    assert watch["max_bid"] == 50.00
    assert watch["status"] == "active"


@pytest.mark.asyncio
async def test_add_watch_already_exists(sniper: SniperEngine, mock_ebay_client):
    """Test adding a watch that already exists"""
    mock_ebay_client.get_item.return_value = {
        "itemId": "v1|287456575036|0",
        "title": "Test Item",
        "itemEndDate": "2099-12-31T23:59:59.000Z",
        "price": {"value": "30.00", "currency": "GBP"},
    }

    await sniper.add_watch(item_id="287456575036", max_bid=50.00, source="test")

    # Try to add the same item again
    watch = await sniper.add_watch(item_id="287456575036", max_bid=60.00, source="test")

    assert watch is not None
    assert watch["max_bid"] == 50.00  # Should return the original watch


@pytest.mark.asyncio
async def test_add_watch_auction_ended(sniper: SniperEngine, mock_ebay_client):
    """Test adding a watch for an ended auction"""
    # Set NTP time to after auction end
    sniper.ntp.synced = True
    sniper.ntp.offset = 0.0

    # Auction ended yesterday
    mock_ebay_client.get_item.return_value = {
        "itemId": "v1|287456575036|0",
        "title": "Test Item",
        "itemEndDate": "2020-01-01T12:00:00.000Z",
        "price": {"value": "30.00", "currency": "GBP"},
    }

    with pytest.raises(ValueError, match="Auction has already ended"):
        await sniper.add_watch(item_id="287456575036", max_bid=50.00, source="test")


@pytest.mark.asyncio
async def test_cancel_watch(sniper: SniperEngine, db: WatchStore):
    """Test cancelling a watch"""
    # Add a watch
    watch_id = db.add_watch(
        item_id="v1|287456575036|0",
        legacy_item_id="287456575036",
        title="Test Item",
        auction_end_time="2099-12-31T23:59:59Z",
        max_bid=50.00,
        currency="GBP",
        source="test",
    )

    # Cancel it
    success = await sniper.cancel_watch(watch_id)

    assert success is True

    watch = db.get_watch(watch_id)
    assert watch["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_watch_not_found(sniper: SniperEngine):
    """Test cancelling a non-existent watch"""
    success = await sniper.cancel_watch("nonexistent")
    assert success is False


@pytest.mark.asyncio
async def test_cancel_watch_not_active(sniper: SniperEngine, db: WatchStore):
    """Test cancelling a watch that's not active"""
    watch_id = db.add_watch(
        item_id="v1|287456575036|0",
        legacy_item_id="287456575036",
        title="Test Item",
        auction_end_time="2099-12-31T23:59:59Z",
        max_bid=50.00,
        currency="GBP",
        source="test",
    )

    db.update_watch_status(watch_id, "cancelled")

    success = await sniper.cancel_watch(watch_id)
    assert success is False


def test_list_watches(sniper: SniperEngine, db: WatchStore):
    """Test listing watches"""
    db.add_watch(
        item_id="v1|287456575036|0",
        legacy_item_id="287456575036",
        title="Test Item 1",
        auction_end_time="2099-12-31T23:59:59Z",
        max_bid=50.00,
        currency="GBP",
        source="test",
    )

    db.add_watch(
        item_id="v1|287456575037|0",
        legacy_item_id="287456575037",
        title="Test Item 2",
        auction_end_time="2099-12-31T23:59:59Z",
        max_bid=75.00,
        currency="GBP",
        source="test",
    )

    watches = sniper.list_watches()
    assert len(watches) == 2

    active_watches = sniper.list_watches("active")
    assert len(active_watches) == 2

    cancelled_watches = sniper.list_watches("cancelled")
    assert len(cancelled_watches) == 0


def test_get_watch(sniper: SniperEngine, db: WatchStore):
    """Test getting a single watch"""
    watch_id = db.add_watch(
        item_id="v1|287456575036|0",
        legacy_item_id="287456575036",
        title="Test Item",
        auction_end_time="2099-12-31T23:59:59Z",
        max_bid=50.00,
        currency="GBP",
        source="test",
    )

    watch = sniper.get_watch(watch_id)

    assert watch is not None
    assert watch["id"] == watch_id
    assert watch["title"] == "Test Item"


def test_get_watch_not_found(sniper: SniperEngine):
    """Test getting a non-existent watch"""
    watch = sniper.get_watch("nonexistent")
    assert watch is None


@pytest.mark.asyncio
async def test_execute_snipe_success(sniper: SniperEngine, db: WatchStore, mock_ebay_client):
    """Test successful snipe execution"""
    watch_id = db.add_watch(
        item_id="v1|287456575036|0",
        legacy_item_id="287456575036",
        title="Test Item",
        auction_end_time="2099-12-31T23:59:59Z",
        max_bid=50.00,
        currency="GBP",
        source="test",
    )

    mock_ebay_client.place_proxy_bid.return_value = {
        "success": True,
        "itemId": "v1|287456575036|0",
        "maxAmount": 50.00,
        "stubbed": True,
    }

    result = await sniper.execute_snipe(watch_id)

    assert result["success"] is True
    assert result["watch_id"] == watch_id

    watch = db.get_watch(watch_id)
    assert watch["bid_placed"] == 1
    assert watch["bid_amount"] == 50.00


@pytest.mark.asyncio
async def test_execute_snipe_watch_not_found(sniper: SniperEngine):
    """Test executing snipe for non-existent watch"""
    result = await sniper.execute_snipe("nonexistent")
    assert result["success"] is False
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_execute_snipe_not_active(sniper: SniperEngine, db: WatchStore):
    """Test executing snipe for non-active watch"""
    watch_id = db.add_watch(
        item_id="v1|287456575036|0",
        legacy_item_id="287456575036",
        title="Test Item",
        auction_end_time="2099-12-31T23:59:59Z",
        max_bid=50.00,
        currency="GBP",
        source="test",
    )

    db.update_watch_status(watch_id, "cancelled")

    result = await sniper.execute_snipe(watch_id)
    assert result["success"] is False
    assert "not active" in result["error"]