"""Unit tests for eBayClient"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sniper.core.ebay_client import eBayClient
from sniper.core.auth import AuthManager


@pytest.fixture
def mock_auth():
    """Mock AuthManager"""
    auth = AsyncMock(spec=AuthManager)
    auth.get_app_token.return_value = "test_token"
    return auth


@pytest.fixture
def ebay_client(mock_auth):
    """Create eBayClient instance"""
    return eBayClient(mock_auth)


def test_normalize_item_id_numeric(ebay_client):
    """Test normalizing numeric item ID"""
    result = eBayClient._normalize_item_id("287456575036")
    assert result == "v1|287456575036|0"


def test_normalize_item_id_v1_format(ebay_client):
    """Test normalizing v1 format item ID"""
    result = eBayClient._normalize_item_id("v1|287456575036|0")
    assert result == "v1|287456575036|0"


def test_normalize_item_id_url(ebay_client):
    """Test normalizing eBay URL"""
    result = eBayClient._normalize_item_id(
        "https://www.ebay.co.uk/itm/287456575036"
    )
    assert result == "v1|287456575036|0"


def test_extract_numeric_id(ebay_client):
    """Test extracting numeric item ID"""
    result = eBayClient.extract_numeric_id("287456575036")
    assert result == "287456575036"

    result = eBayClient.extract_numeric_id("v1|287456575036|0")
    assert result == "287456575036"

    result = eBayClient.extract_numeric_id(
        "https://www.ebay.co.uk/itm/287456575036"
    )
    assert result == "287456575036"


@pytest.mark.asyncio
async def test_search_auctions(ebay_client, mock_auth):
    """Test searching auctions"""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "itemSummaries": [
                {
                    "itemId": "v1|287456575036|0",
                    "title": "Test Item",
                    "price": {"value": "30.00", "currency": "GBP"},
                    "itemWebUrl": "https://www.ebay.co.uk/itm/287456575036",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_client_class.return_value = mock_client

        results = await ebay_client.search_auctions("test query", 10)

        assert len(results) == 1
        assert results[0]["title"] == "Test Item"


def test_format_search_price_prefers_current_bid_price(ebay_client):
    """Auction results should prefer currentBidPrice over price"""
    item = {
        "title": "Auction Item",
        "price": {"value": "0.00", "currency": "GBP"},
        "currentBidPrice": {"value": "642.00", "currency": "GBP"},
    }

    assert eBayClient.format_search_price(item) == "642.00 GBP"


@pytest.mark.asyncio
async def test_get_item(ebay_client, mock_auth):
    """Test getting item details"""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "itemId": "v1|287456575036|0",
            "title": "Test Item",
            "itemEndDate": "2025-12-31T23:59:59.000Z",
            "price": {"value": "30.00", "currency": "GBP"},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_client_class.return_value = mock_client

        item = await ebay_client.get_item("287456575036")

        assert item["title"] == "Test Item"
        assert item["itemId"] == "v1|287456575036|0"


@pytest.mark.asyncio
async def test_place_proxy_bid_stubbed(ebay_client):
    """Test placing a proxy bid (stubbed)"""
    result = await ebay_client.place_proxy_bid("287456575036", 50.00)

    assert result["success"] is True
    assert result["stubbed"] is True
    assert result["itemId"] == "287456575036"
    assert result["maxAmount"] == 50.00


@pytest.mark.asyncio
async def test_get_bidding_stubbed(ebay_client):
    """Test getting bidding info (stubbed)"""
    result = await ebay_client.get_bidding("287456575036")

    assert "itemId" in result
    assert result["itemId"] == "287456575036"
    assert "bidding" in result