"""Core sniper engine for watch management and bid orchestration"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..config import config
from .db import WatchStore
from .ebay_client import eBayClient
from .ntp import NTPSync

logger = logging.getLogger(__name__)


class SniperEngine:
    """Main engine for managing watches and executing snipes"""

    def __init__(self, db: WatchStore, ebay_client: eBayClient, ntp: NTPSync):
        """Initialize SniperEngine"""
        self.db = db
        self.ebay_client = ebay_client
        self.ntp = ntp

    async def add_watch(
        self,
        item_id: str,
        max_bid: float,
        source: str = "manual",
        notes: Optional[str] = None,
    ) -> dict:
        """Add a new watch for an auction

        Fetches auction details via Browse API and stores watch.

        Args:
            item_id: eBay item ID or URL
            max_bid: Maximum bid amount
            source: Source of the watch (manual, telegram, cli, mcp, hermes)
            notes: Optional user notes

        Returns:
            Watch details including watch_id
        """
        # Normalize item ID
        normalized_id = eBayClient._normalize_item_id(item_id)

        # Check if watch already exists
        existing = self.db.get_watch_by_item_id(normalized_id)
        if existing:
            logger.warning(f"Watch already exists for item {item_id}")
            return existing

        # Fetch auction details
        try:
            item_data = await self.ebay_client.get_item(normalized_id)

            # Extract relevant fields
            title = item_data.get("title", "Unknown Title")
            # Get end time from item data
            end_time_str = self._extract_end_time(item_data)

            if not end_time_str:
                raise ValueError("Could not determine auction end time")

            # Parse and validate end time
            end_time = datetime.fromisoformat(end_time_str)

            # Check if auction is still active
            now = self.ntp.get_adjusted_time()
            if end_time < now:
                raise ValueError("Auction has already ended")

            # Extract legacy numeric ID
            legacy_id = normalized_id.split("|")[1] if "|" in normalized_id else None

            # Get currency
            price = item_data.get("price", {})
            currency = price.get("currency", "GBP")

            # Store watch
            watch_id = self.db.add_watch(
                item_id=normalized_id,
                legacy_item_id=legacy_id,
                title=title,
                auction_end_time=end_time_str,
                max_bid=max_bid,
                currency=currency,
                source=source,
                notes=notes,
            )

            # Log watch creation
            self.db.log_event(
                watch_id,
                "watch_created",
                {
                    "item_id": normalized_id,
                    "title": title,
                    "max_bid": max_bid,
                    "end_time": end_time_str,
                    "source": source,
                },
            )

            logger.info(
                f"Watch added: {watch_id} for item {normalized_id} "
                f"(ends {end_time}, max bid £{max_bid})"
            )

            return self.db.get_watch(watch_id)

        except Exception as e:
            logger.error(f"Failed to add watch for item {item_id}: {e}")
            raise

    async def cancel_watch(self, watch_id: str) -> bool:
        """Cancel an active watch

        Args:
            watch_id: Watch ID to cancel

        Returns:
            True if cancelled, False if not found
        """
        watch = self.db.get_watch(watch_id)
        if not watch:
            logger.warning(f"Watch {watch_id} not found")
            return False

        if watch["status"] != "active":
            logger.warning(
                f"Watch {watch_id} is not active (status: {watch['status']})"
            )
            return False

        # Update status
        self.db.update_watch_status(watch_id, "cancelled")
        self.db.log_event(watch_id, "cancelled", {"reason": "user_cancelled"})

        logger.info(f"Watch {watch_id} cancelled")
        return True

    def list_watches(self, status: Optional[str] = "active") -> list[dict]:
        """List watches, optionally filtered by status

        Args:
            status: Filter by status ('active', 'won', 'lost', 'cancelled', 'error')

        Returns:
            List of watches
        """
        if status == "all":
            return self.db.list_watches()
        return self.db.list_watches(status)

    def get_watch(self, watch_id: str) -> Optional[dict]:
        """Get a single watch by ID

        Args:
            watch_id: Watch ID

        Returns:
            Watch details or None if not found
        """
        return self.db.get_watch(watch_id)

    async def execute_snipe(self, watch_id: str) -> dict:
        """Execute a snipe bid for a watch

        Called by scheduler at end_time - BID_OFFSET_SECONDS.

        Args:
            watch_id: Watch ID

        Returns:
            Result dict with success status and details
        """
        watch = self.db.get_watch(watch_id)
        if not watch:
            logger.error(f"Watch {watch_id} not found")
            return {"success": False, "error": "Watch not found"}

        if watch["status"] != "active":
            logger.warning(
                f"Watch {watch_id} is not active (status: {watch['status']})"
            )
            return {"success": False, "error": f"Watch not active: {watch['status']}"}

        # Log bid attempt
        self.db.log_event(
            watch_id,
            "bid_attempt",
            {
                "max_bid": watch["max_bid"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        try:
            # Place proxy bid
            result = await self.ebay_client.place_proxy_bid(
                watch["item_id"], watch["max_bid"]
            )

            if result.get("success"):
                # Update watch with bid placed
                self.db.update_watch_bid(
                    watch_id, bid_placed=1, bid_amount=watch["max_bid"]
                )
                self.db.log_event(watch_id, "bid_placed", result)

                logger.info(
                    f"Snipe executed for watch {watch_id}: "
                    f"item {watch['item_id']}, bid £{watch['max_bid']}"
                )

                return {"success": True, "watch_id": watch_id, "result": result}
            else:
                # Log failure
                self.db.log_event(
                    watch_id, "error", {"error": result.get("error", "Unknown error")}
                )
                self.db.update_watch_status(watch_id, "error")

                logger.error(f"Snipe failed for watch {watch_id}: {result}")

                return {"success": False, "error": result.get("error")}

        except Exception as e:
            logger.error(f"Snipe failed for watch {watch_id}: {e}")
            self.db.log_event(watch_id, "error", {"error": str(e)})
            self.db.update_watch_status(watch_id, "error")

            return {"success": False, "error": str(e)}

    async def check_result(self, watch_id: str) -> dict:
        """Check auction result for a watch

        Called by scheduler at end_time + RESULT_CHECK_DELAY_SECONDS.

        Args:
            watch_id: Watch ID

        Returns:
            Result dict with auction outcome
        """
        watch = self.db.get_watch(watch_id)
        if not watch:
            return {"success": False, "error": "Watch not found"}

        try:
            # Fetch item details to check result
            item_data = await self.ebay_client.get_item(watch["item_id"])

            # Determine if won
            # This is a simplified check - real implementation would compare
            # with final price and current high bidder
            # For now, we'll assume we won if the auction ended and we placed a bid
            auction_ended = self._is_auction_ended(item_data)

            if auction_ended:
                # Parse final price if available
                final_price = self._extract_current_price(item_data)

                # For now, assume we won if we placed a bid
                # Real implementation would check actual winner
                winning = 1 if watch["bid_placed"] else 0

                # Update watch status
                status = "won" if winning else "lost"
                self.db.update_watch_status(watch_id, status)
                self.db.update_watch_result(watch_id, winning, final_price)

                self.db.log_event(
                    watch_id,
                    status,
                    {
                        "final_price": final_price,
                        "winning": winning,
                        "bid_placed": watch["bid_placed"],
                    },
                )

                logger.info(
                    f"Auction result for watch {watch_id}: {status}, final price £{final_price}"
                )

                return {
                    "success": True,
                    "watch_id": watch_id,
                    "status": status,
                    "winning": winning,
                    "final_price": final_price,
                }
            else:
                # Auction not ended yet, recheck later
                return {"success": False, "error": "Auction not ended"}

        except Exception as e:
            logger.error(f"Failed to check result for watch {watch_id}: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _extract_end_time(item_data: dict) -> Optional[str]:
        """Extract auction end time from item data"""
        # Browse API v1 returns end time in different fields
        if "itemEndDate" in item_data:
            return item_data["itemEndDate"]
        if "endTime" in item_data:
            return item_data["endTime"]
        return None

    @staticmethod
    def _extract_current_price(item_data: dict) -> Optional[float]:
        """Extract current price from item data"""
        if "price" in item_data:
            return float(item_data["price"].get("value", 0))
        if "currentBidPrice" in item_data:
            return float(item_data["currentBidPrice"].get("value", 0))
        return None

    @staticmethod
    def _is_auction_ended(item_data: dict) -> bool:
        """Check if auction has ended"""
        # This is a placeholder - real implementation would check endTime vs now
        return True
