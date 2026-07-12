"""eBay API client for Browse and Offer APIs"""

import logging
import re
from typing import Any, Optional

import httpx

from ..config import config
from .auth import AuthManager

logger = logging.getLogger(__name__)


class eBayClient:
    """HTTP client for eBay Browse and Offer APIs"""

    def __init__(self, auth: AuthManager):
        """Initialize eBayClient with AuthManager"""
        self.auth = auth

    async def _get_headers(self) -> dict[str, str]:
        """Get headers with authorization token"""
        token = await self.auth.get_app_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-EBAY-C-MARKETPLACE-ID": config.EBAY_MARKETPLACE,
        }

    async def get_item(self, item_id: str) -> dict:
        """Get item details using Browse API getItem

        Args:
            item_id: eBay item ID (e.g., "v1|287456575036|0" or "287456575036")

        Returns:
            Item details including title, end time, current price, etc.
        """
        # Normalize item ID
        normalized_id = self._normalize_item_id(item_id)

        url = f"{config.ebay_base_url}/buy/browse/v1/item/{normalized_id}"
        headers = await self._get_headers()

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def search_auctions(self, query: str, limit: int = 20) -> list[dict]:
        """Search for auction listings using Browse API

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of auction items
        """
        url = f"{config.ebay_base_url}/buy/browse/v1/item_summary/search"
        headers = await self._get_headers()

        params = {
            "q": query,
            "limit": limit,
            # Browse API auction filter — buyingOptions, not listingType
            "filter": "buyingOptions:{AUCTION}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("itemSummaries", [])

    @staticmethod
    def format_search_price(item: dict) -> str:
        """Format a Browse API search result price for display.

        Auction search results often omit top-level ``price`` and instead
        expose the live bid under ``currentBidPrice``. Prefer that for
        auctions, then fall back to ``price`` and finally any plain numeric
        fallback the API may return.
        """
        price_info = (
            item.get("currentBidPrice")
            or item.get("price")
            or item.get("currentPrice")
            or {}
        )

        value = price_info.get("value")
        currency = price_info.get("currency", "GBP")

        if value is None:
            return f"Unknown {currency}"

        return f"{value} {currency}"

    async def get_bidding(self, item_id: str) -> dict:
        """Get bidding information using Offer API

        Note: Currently stubbed. Requires buy.offer.auction scope.
        """
        # STUB: Until scope is granted
        logger.warning(
            f"STUB: get_bidding({item_id}) - scope buy.offer.auction not granted"
        )
        return {"itemId": item_id, "bidding": []}

    async def place_proxy_bid(self, item_id: str, max_amount: float) -> dict:
        """Place a proxy bid using Offer API

        Note: Currently stubbed. Requires buy.offer.auction scope.
        When scope is granted, implement real API call:
        POST https://apiz.ebay.com/commerce/bidding/v1_proxy_bid

        Args:
            item_id: eBay item ID
            max_amount: Maximum bid amount

        Returns:
            Bid response with success status
        """
        if config.BID_PLACEMENT_STUBBED:
            # STUB: Log stubbed bid and return mock success
            logger.warning(
                f"STUB: bid not actually placed - item={item_id}, max_amount={max_amount}"
            )
            logger.info(
                "STUB: This is a mock bid. Real bids require buy.offer.auction scope."
            )
            return {
                "success": True,
                "itemId": item_id,
                "maxAmount": max_amount,
                "stubbed": True,
                "message": "STUB: bid not actually placed (scope not granted)",
            }

        # TODO: Implement real bid placement when scope is granted
        logger.warning(
            f"place_proxy_bid({item_id}, {max_amount}) - scope not granted, should be stubbed"
        )
        return {
            "success": True,
            "itemId": item_id,
            "maxAmount": max_amount,
            "stubbed": True,
        }

    @staticmethod
    def _normalize_item_id(item_id: str) -> str:
        """Normalize eBay item ID to v1 format

        Accepts:
        - Legacy numeric: "287456575036"
        - v1 format: "v1|287456575036|0"
        - URL: "https://www.ebay.co.uk/itm/287456575036"

        Returns:
            v1 format item ID: "v1|287456575036|0"
        """
        # Extract numeric ID from URL
        url_match = re.search(r"/itm/(\d+)", item_id)
        if url_match:
            numeric_id = url_match.group(1)
            return f"v1|{numeric_id}|0"

        # If already in v1 format, return as-is
        if item_id.startswith("v1|"):
            return item_id

        # Assume legacy numeric format
        return f"v1|{item_id}|0"

    @staticmethod
    def extract_numeric_id(item_id: str) -> str:
        """Extract numeric eBay item ID

        Useful for display and legacy API calls
        """
        normalized = eBayClient._normalize_item_id(item_id)
        parts = normalized.split("|")
        return parts[1] if len(parts) > 1 else normalized
