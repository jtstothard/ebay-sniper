"""MCP server for eBay Sniper - integrates with Hermes"""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from .config import config
from .core.db import WatchStore
from .core.sniper import SniperEngine
from .core.auth import AuthManager
from .core.ebay_client import eBayClient
from .core.ntp import NTPSync

logger = logging.getLogger(__name__)

# Create MCP server
app = Server("ebay-sniper")


def get_components():
    """Get shared components (lazy initialization)"""
    db = WatchStore()
    ntp = NTPSync()
    ntp.sync()
    auth = AuthManager(db)
    ebay_client = eBayClient(auth)
    sniper = SniperEngine(db, ebay_client, ntp)

    return db, sniper, ebay_client, ntp


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="add_watch",
            description="Add a watch for an eBay auction. The item can be specified by ID or URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "eBay item ID or URL (e.g., 287456575036 or https://www.ebay.co.uk/itm/287456575036)",
                    },
                    "max_bid": {
                        "type": "number",
                        "description": "Maximum bid amount in GBP",
                    },
                    "source": {
                        "type": "string",
                        "description": "Source of the watch (e.g., 'hermes', 'mcp', 'cli')",
                        "default": "mcp",
                    },
                },
                "required": ["item_id", "max_bid"],
            },
        ),
        Tool(
            name="list_watches",
            description="List all watches, optionally filtered by status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status: 'active', 'won', 'lost', 'cancelled', 'error', or 'all'",
                        "enum": ["active", "won", "lost", "cancelled", "error", "all"],
                        "default": "active",
                    },
                },
            },
        ),
        Tool(
            name="get_watch",
            description="Get details of a specific watch by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "watch_id": {
                        "type": "string",
                        "description": "Watch ID to retrieve",
                    },
                },
                "required": ["watch_id"],
            },
        ),
        Tool(
            name="cancel_watch",
            description="Cancel an active watch.",
            inputSchema={
                "type": "object",
                "properties": {
                    "watch_id": {
                        "type": "string",
                        "description": "Watch ID to cancel",
                    },
                },
                "required": ["watch_id"],
            },
        ),
        Tool(
            name="search_auctions",
            description="Search eBay for auction listings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string",
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results (default: 20)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_status",
            description="Get service status including NTP sync and eBay API connectivity.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    db, sniper, ebay_client, ntp = get_components()

    try:
        if name == "add_watch":
            item_id = arguments.get("item_id")
            max_bid = float(arguments.get("max_bid"))
            source = arguments.get("source", "mcp")

            if not item_id:
                raise ValueError("item_id is required")

            watch = await sniper.add_watch(
                item_id=item_id, max_bid=max_bid, source=source
            )

            return [
                TextContent(
                    type="text",
                    text=f"Watch added successfully!\n"
                    f"  Watch ID: {watch['id']}\n"
                    f"  Title: {watch['title']}\n"
                    f"  Item ID: {watch['item_id']}\n"
                    f"  End Time: {watch['auction_end_time']}\n"
                    f"  Max Bid: £{watch['max_bid']}",
                )
            ]

        elif name == "list_watches":
            status_filter = arguments.get("status", "active")
            watches = sniper.list_watches(
                None if status_filter == "all" else status_filter
            )

            if not watches:
                return [
                    TextContent(type="text", text=f"No watches found (status: {status_filter})")
                ]

            text = f"{len(watches)} watch(es) found (status: {status_filter}):\n\n"
            for i, watch in enumerate(watches, 1):
                text += (
                    f"{i}. {watch['title']}\n"
                    f"   Watch ID: {watch['id']}\n"
                    f"   Item ID: {watch['item_id']}\n"
                    f"   End Time: {watch['auction_end_time']}\n"
                    f"   Max Bid: £{watch['max_bid']}\n"
                    f"   Status: {watch['status']}\n\n"
                )

            return [TextContent(type="text", text=text)]

        elif name == "get_watch":
            watch_id = arguments.get("watch_id")
            if not watch_id:
                raise ValueError("watch_id is required")

            watch = sniper.get_watch(watch_id)
            if not watch:
                return [TextContent(type="text", text=f"Watch not found: {watch_id}")]

            log = db.get_bid_log(watch_id)

            text = (
                f"Watch Details:\n"
                f"  Watch ID: {watch['id']}\n"
                f"  Title: {watch['title']}\n"
                f"  Item ID: {watch['item_id']}\n"
                f"  End Time: {watch['auction_end_time']}\n"
                f"  Max Bid: £{watch['max_bid']}\n"
                f"  Status: {watch['status']}\n"
                f"  Bid Placed: {'Yes' if watch['bid_placed'] else 'No'}\n"
                f"  Source: {watch['source']}\n"
            )

            if watch["bid_amount"]:
                text += f"  Bid Amount: £{watch['bid_amount']}\n"

            if watch["final_price"]:
                text += f"  Final Price: £{watch['final_price']}\n"

            if log:
                text += f"\nEvent Log ({len(log)} events):\n"
                for event in log:
                    text += f"  - {event['timestamp']}: {event['event']}\n"

            return [TextContent(type="text", text=text)]

        elif name == "cancel_watch":
            watch_id = arguments.get("watch_id")
            if not watch_id:
                raise ValueError("watch_id is required")

            success = await sniper.cancel_watch(watch_id)

            if success:
                return [TextContent(type="text", text=f"Watch {watch_id} cancelled successfully")]
            else:
                return [TextContent(type="text", text=f"Failed to cancel watch {watch_id}")]

        elif name == "search_auctions":
            query = arguments.get("query")
            limit = int(arguments.get("limit", 20))

            if not query:
                raise ValueError("query is required")

            results = await ebay_client.search_auctions(query, limit)

            if not results:
                return [TextContent(type="text", text=f"No results found for '{query}'")]

            text = f"Found {len(results)} results for '{query}':\n\n"
            for i, item in enumerate(results, 1):
                title = item.get("title", "Unknown")
                price = eBayClient.format_search_price(item)
                item_id = item.get("itemId", "Unknown")
                url = item.get("itemWebUrl", "N/A")

                # Extract numeric ID for easier use
                numeric_id = item_id.split("|")[1] if "|" in item_id else item_id

                text += (
                    f"{i}. {title}\n"
                    f"   Item ID: {numeric_id}\n"
                    f"   Price: {price}\n"
                    f"   URL: {url}\n\n"
                )

            return [TextContent(type="text", text=text)]

        elif name == "get_status":
            synced = ntp.sync()
            now = ntp.get_adjusted_time()

            status_text = (
                f"eBay Sniper Status:\n"
                f"  Environment: {config.EBAY_ENVIRONMENT}\n"
                f"  NTP Synced: {'Yes' if synced else 'No'}\n"
                f"  NTP Offset: {ntp.offset:.6f}s\n"
                f"  Current Time: {now.isoformat()}\n"
                f"  Bid Placement: {'STUBBED' if config.BID_PLACEMENT_STUBBED else 'Active'}\n"
                f"  Marketplace: {config.EBAY_MARKETPLACE}\n"
            )

            active_watches = sniper.list_watches("active")
            status_text += f"  Active Watches: {len(active_watches)}\n"

            return [TextContent(type="text", text=status_text)]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Tool call failed: {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def run_stdio():
    """Run the MCP server over stdio."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    """Entry point for the MCP server."""
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()