"""Telegram bot for eBay Sniper"""

import html
import logging
from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .config import config
from .core.auth import AuthManager
from .core.db import WatchStore
from .core.ebay_client import eBayClient
from .core.ntp import NTPSync
from .core.sniper import SniperEngine
from .scheduler import SniperScheduler

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for managing sniper watches"""

    def __init__(
        self,
        db: WatchStore,
        sniper: SniperEngine,
        scheduler: SniperScheduler,
        ebay_client: eBayClient,
    ):
        """Initialize Telegram bot"""
        self.db = db
        self.sniper = sniper
        self.scheduler = scheduler
        self.ebay_client = ebay_client

        # Create application
        self.application = (
            Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        )

        # Register handlers
        self.application.add_handler(CommandHandler("watch", self.watch_command))
        self.application.add_handler(CommandHandler("list", self.list_command))
        self.application.add_handler(CommandHandler("cancel", self.cancel_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("help", self.help_command))

    async def send_notification(self, message: str):
        """Send notification to configured chat ID"""
        if not config.TELEGRAM_CHAT_ID:
            logger.warning("No TELEGRAM_CHAT_ID configured")
            return

        try:
            await self.application.bot.send_message(
                chat_id=config.TELEGRAM_CHAT_ID, text=message, parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    async def watch_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add a watch - /watch <item_id_or_url> <max_bid>"""
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "Usage: /watch <item_id_or_url> <max_bid>\n"
                "Example: /watch 206406145417 650\n"
                "Example: /watch https://www.ebay.co.uk/itm/206406145417 650"
            )
            return

        item_id = context.args[0]
        try:
            max_bid = float(context.args[1])
        except ValueError:
            await update.message.reply_text("Error: max_bid must be a number")
            return

        try:
            watch = await self.sniper.add_watch(
                item_id=item_id, max_bid=max_bid, source="telegram"
            )

            # Schedule the snipe
            self.scheduler.schedule_watch(watch["id"], watch["auction_end_time"])

            # Send confirmation
            end_time = datetime.fromisoformat(watch["auction_end_time"])
            now = datetime.now(timezone.utc)
            remaining = end_time - now

            remaining_str = ""
            if remaining.total_seconds() > 3600:
                remaining_str = f"{int(remaining.total_seconds() / 3600)}h"
            elif remaining.total_seconds() > 60:
                remaining_str = f"{int(remaining.total_seconds() / 60)}m"
            else:
                remaining_str = f"{int(remaining.total_seconds())}s"

            example_bid = (
                str(int(watch["max_bid"]))
                if float(watch["max_bid"]).is_integer()
                else f"{watch['max_bid']:.2f}"
            )

            msg = (
                f"✅ <b>Watch Added</b>\n"
                f"\n"
                f"📦 {watch['title']}\n"
                f"🔗 <a href='https://www.ebay.co.uk/itm/{watch['legacy_item_id']}'>View on eBay</a>\n"
                f"💰 Max Bid: £{watch['max_bid']:.2f}\n"
                f"⏰ Ends: {watch['auction_end_time']}\n"
                f"⏳ Remaining: {remaining_str}\n"
                f"🆔 Watch ID: {watch['id']}\n"
                f"💡 Example: /watch {watch['legacy_item_id']} {example_bid}"
            )

            await update.message.reply_text(msg, parse_mode="HTML")

        except Exception as e:
            logger.error(f"Failed to add watch: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List active watches - /list"""
        watches = self.sniper.list_watches("active")

        if not watches:
            await update.message.reply_text("📭 No active watches")
            return

        now = datetime.now(timezone.utc)
        msg = f"📋 <b>Active Watches ({len(watches)})</b>\n\n"

        for i, watch in enumerate(watches, 1):
            end_time = datetime.fromisoformat(watch["auction_end_time"])
            remaining = end_time - now

            if remaining.total_seconds() > 3600:
                time_str = f"{int(remaining.total_seconds() / 3600)}h"
            elif remaining.total_seconds() > 60:
                time_str = f"{int(remaining.total_seconds() / 60)}m"
            elif remaining.total_seconds() > 0:
                time_str = f"{int(remaining.total_seconds())}s 🔥"
            else:
                time_str = "ENDED"

            msg += (
                f"{i}. <b>{watch['title'][:50]}...</b>\n"
                f"   💰 £{watch['max_bid']:.2f} | ⏰ {time_str}\n"
                f"   🆔 {watch['id'][:8]}...\n\n"
            )

        await update.message.reply_text(msg, parse_mode="HTML")

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel a watch - /cancel <watch_id_or_item_id>"""
        if not context.args:
            await update.message.reply_text(
                "Usage: /cancel <watch_id_or_item_id>\n"
                "Example: /cancel abc12345\n"
                "Example: /cancel 287456575036"
            )
            return

        identifier = context.args[0]

        # Try to find watch by ID or item ID
        watch = self.db.get_watch(identifier)
        if not watch:
            watch = self.db.get_watch_by_item_id(identifier)

        if not watch:
            await update.message.reply_text(f"❌ Watch not found: {identifier}")
            return

        if watch["status"] != "active":
            await update.message.reply_text(
                f"❌ Watch is not active (status: {watch['status']})"
            )
            return

        # Cancel watch
        success = await self.sniper.cancel_watch(watch["id"])

        if success:
            # Unschedule
            self.scheduler.unschedule_watch(watch["id"])
            await update.message.reply_text(f"✅ Watch cancelled: {watch['title']}")
        else:
            await update.message.reply_text(f"❌ Failed to cancel watch")

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Search eBay auctions - /search <query>"""
        if not context.args:
            await update.message.reply_text("Usage: /search <query>")
            return

        query = " ".join(context.args)

        try:
            results = await self.ebay_client.search_auctions(query, limit=10)

            if not results:
                await update.message.reply_text(f"📭 No results found for: {query}")
                return

            msg = f"🔍 <b>Search Results: {html.escape(query)}</b>\n\n"

            for i, item in enumerate(results, 1):
                raw_title = item.get("title", "Unknown")[:60]
                title = html.escape(raw_title)
                price = html.escape(eBayClient.format_search_price(item))
                item_id = item.get("itemId", "Unknown")

                # Extract numeric ID
                numeric_id = html.escape(
                    item_id.split("|")[1] if "|" in item_id else item_id
                )

                msg += (
                    f"{i}. <b>{title}...</b>\n"
                    f"   💰 {price}\n"
                    f"   🆔 {numeric_id}\n"
                    f"   /watch {numeric_id} &lt;max_bid&gt;\n\n"
                )

            await update.message.reply_text(msg, parse_mode="HTML")

        except Exception as e:
            logger.error(f"Search failed: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show service status - /status"""
        watches = self.sniper.list_watches("active")
        jobs = self.scheduler.get_scheduled_jobs()

        msg = (
            f"📊 <b>eBay Sniper Status</b>\n\n"
            f"🌐 Environment: {config.EBAY_ENVIRONMENT}\n"
            f"🎯 Active Watches: {len(watches)}\n"
            f"⏰ Scheduled Jobs: {len(jobs)}\n"
            f"💸 Bid Placement: {'STUBBED' if config.BID_PLACEMENT_STUBBED else 'Active'}\n"
            f"🏪 Marketplace: {config.EBAY_MARKETPLACE}"
        )

        await update.message.reply_text(msg, parse_mode="HTML")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help - /help"""
        help_text = (
            "<b>eBay Sniper Bot Commands</b>\n\n"
            "<b>Watch Management</b>\n"
            "/watch <item_id_or_url> <max_bid> - Add a watch\n"
            "/list - List active watches\n"
            "/cancel <watch_id_or_item_id> - Cancel a watch\n\n"
            "<b>Search</b>\n"
            "/search <query> - Search eBay auctions\n\n"
            "<b>Info</b>\n"
            "/status - Show service status\n"
            "/help - Show this help message\n\n"
            "<b>Examples</b>\n"
            "/watch 206406145417 650\n"
            "/watch https://www.ebay.co.uk/itm/206406145417 650\n"
            "/search nintendo switch\n"
            "/cancel abc12345"
        )
        await update.message.reply_text(help_text, parse_mode="HTML")

    def start(self):
        """Start the bot"""
        logger.info("Starting Telegram bot")
        # Let python-telegram-bot manage initialize/start/polling/shutdown itself.
        # This is safer than manual loop plumbing in a background thread.
        self.application.run_polling(stop_signals=None)

    def stop(self):
        """Stop the bot"""
        logger.info("Stopping Telegram bot")
        self.application.stop_running()
