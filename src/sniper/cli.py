"""Command-line interface for eBay Sniper"""

import asyncio
import logging
from datetime import datetime

import typer

from .config import config
from .core.db import WatchStore
from .core.sniper import SniperEngine
from .core.auth import AuthManager
from .core.ebay_client import eBayClient
from .core.ntp import NTPSync

app = typer.Typer(
    name="sniper",
    help="eBay Sniper CLI - Self-hosted auction sniping for eBay",
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def get_components():
    """Get shared components"""
    db = WatchStore()
    ntp = NTPSync()
    auth = AuthManager(db)
    ebay_client = eBayClient(auth)
    sniper = SniperEngine(db, ebay_client, ntp)

    return db, sniper, ebay_client, ntp


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of results"),
):
    """Search eBay auctions"""
    _, _, ebay_client, _ = get_components()

    results = asyncio.run(ebay_client.search_auctions(query, limit))

    if not results:
        typer.echo(f"No results found for '{query}'")
        raise typer.Exit()

    typer.echo(f"\nFound {len(results)} results for '{query}':\n")

    for i, item in enumerate(results, 1):
        typer.echo(f"{i}. {item.get('title', 'Unknown')}")
        typer.echo(f"   Item ID: {item.get('itemId', 'Unknown')}")

        price = eBayClient.format_search_price(item)
        typer.echo(f"   Price: {price}")

        if "itemWebUrl" in item:
            typer.echo(f"   URL: {item['itemWebUrl']}")

        typer.echo()


@app.command()
def watch(
    item_id: str = typer.Argument(..., help="eBay item ID or URL"),
    max_bid: float = typer.Option(..., "--max-bid", "-m", help="Maximum bid amount"),
):
    """Add a watch for an auction"""
    db, sniper, _, _ = get_components()

    try:
        watch = asyncio.run(
            sniper.add_watch(item_id=item_id, max_bid=max_bid, source="cli")
        )

        typer.echo(f"\nWatch added successfully!")
        typer.echo(f"  Watch ID: {watch['id']}")
        typer.echo(f"  Title: {watch['title']}")
        typer.echo(f"  Item ID: {watch['item_id']}")
        typer.echo(f"  End Time: {watch['auction_end_time']}")
        typer.echo(f"  Max Bid: £{watch['max_bid']}")
        typer.echo(f"\nUse 'sniper list' to see all watches")

    except Exception as e:
        typer.echo(f"Error adding watch: {e}", err=True)
        raise typer.Exit(1)


@app.command("list")
def list_watches(
    status: str = typer.Option("active", "--status", "-s", help="Filter by status"),
):
    """List all watches"""
    db, sniper, _, _ = get_components()

    watches = sniper.list_watches(status if status != "all" else None)

    if not watches:
        typer.echo(f"No watches found (status: {status})")
        return

    typer.echo(f"\n{len(watches)} watch(es) found (status: {status}):\n")

    for i, watch in enumerate(watches, 1):
        typer.echo(f"{i}. {watch['title']}")
        typer.echo(f"   Watch ID: {watch['id']}")
        typer.echo(f"   Item ID: {watch['item_id']}")
        typer.echo(f"   End Time: {watch['auction_end_time']}")
        typer.echo(f"   Max Bid: £{watch['max_bid']}")
        typer.echo(f"   Status: {watch['status']}")
        typer.echo(f"   Bid Placed: {'Yes' if watch['bid_placed'] else 'No'}")

        if watch["final_price"]:
            typer.echo(f"   Final Price: £{watch['final_price']}")

        typer.echo()


@app.command()
def cancel(
    watch_id: str = typer.Argument(..., help="Watch ID to cancel"),
):
    """Cancel a watch"""
    db, sniper, _, _ = get_components()

    success = asyncio.run(sniper.cancel_watch(watch_id))

    if success:
        typer.echo(f"Watch {watch_id} cancelled successfully")
    else:
        typer.echo(f"Failed to cancel watch {watch_id}", err=True)
        raise typer.Exit(1)


@app.command()
def status():
    """Show service status"""
    _, _, _, ntp = get_components()

    # Sync NTP
    synced = ntp.sync()

    typer.echo("\neBay Sniper Status:")
    typer.echo(f"  Environment: {config.EBAY_ENVIRONMENT}")
    typer.echo(f"  NTP Synced: {'Yes' if synced else 'No'}")
    if synced:
        typer.echo(f"  NTP Offset: {ntp.offset:.6f}s")
    typer.echo(f"  Bid Placement: {'STUBBED' if config.BID_PLACEMENT_STUBBED else 'Active'}")
    typer.echo(f"  Marketplace: {config.EBAY_MARKETPLACE}")
    typer.echo()


@app.command()
def ntp_sync():
    """Sync with NTP server"""
    _, _, _, ntp = get_components()

    typer.echo("Syncing with NTP server...")
    synced = ntp.sync()

    if synced:
        typer.echo(f"NTP sync successful")
        typer.echo(f"  Server: {ntp.ntp_server}")
        typer.echo(f"  Offset: {ntp.offset:.6f}s")
    else:
        typer.echo("NTP sync failed", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()