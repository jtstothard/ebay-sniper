"""Main entry point for eBay Sniper Service"""

import asyncio
import logging
import sys

import uvicorn

from .config import config
from .core.db import WatchStore
from .core.sniper import SniperEngine
from .core.auth import AuthManager
from .core.ebay_client import eBayClient
from .core.ntp import NTPSync
from .scheduler import SniperScheduler
from .telegram_bot import TelegramBot
from .web.app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point - starts all components"""
    logger.info("Starting eBay Sniper Service...")

    # Initialize components
    logger.info("Initializing components...")
    db = WatchStore()
    ntp = NTPSync()

    # Sync NTP
    logger.info("Syncing with NTP server...")
    ntp.sync()
    logger.info(f"NTP offset: {ntp.offset:.6f}s")

    auth = AuthManager(db)
    ebay_client = eBayClient(auth)
    sniper = SniperEngine(db, ebay_client, ntp)
    scheduler = SniperScheduler(db, sniper, ntp)

    # Load existing watches and schedule them
    logger.info("Loading existing watches...")
    active_watches = db.list_watches("active")
    logger.info(f"Found {len(active_watches)} active watches")

    for watch in active_watches:
        try:
            # Only schedule if auction hasn't ended
            from datetime import datetime, timezone

            end_time = datetime.fromisoformat(watch["auction_end_time"])
            now = ntp.get_adjusted_time()

            if end_time > now:
                scheduler.schedule_watch(watch["id"], watch["auction_end_time"])
                logger.info(f"Scheduled snipe for watch {watch['id']}")
            else:
                # Mark as lost if auction ended without bid
                if not watch["bid_placed"]:
                    db.update_watch_status(watch["id"], "lost")
                    db.log_event(watch["id"], "auction_ended_without_bid", {})
                    logger.info(
                        f"Auction ended without bid for watch {watch['id']}, marked as lost"
                    )
        except Exception as e:
            logger.error(f"Failed to schedule watch {watch['id']}: {e}")

    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started")

    # Create FastAPI app
    fastapi_app = create_app(db, sniper, scheduler, ebay_client, ntp)

    # Start Telegram bot if configured
    telegram_bot = None
    if config.TELEGRAM_BOT_TOKEN:
        try:
            telegram_bot = TelegramBot(db, sniper, scheduler, ebay_client)
            logger.info("Telegram bot initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
    else:
        logger.info("Telegram bot not configured")

    # Start web server
    logger.info(f"Starting web server on {config.WEB_HOST}:{config.WEB_PORT}")

    # Start Telegram bot in background if configured
    if telegram_bot:
        import threading

        telegram_thread = threading.Thread(target=telegram_bot.start, daemon=True)
        telegram_thread.start()
        logger.info("Telegram bot started in background")

    # Run uvicorn
    uvicorn_config = uvicorn.Config(
        fastapi_app,
        host=config.WEB_HOST,
        port=config.WEB_PORT,
        log_level="info",
    )
    server = uvicorn.Server(uvicorn_config)

    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())