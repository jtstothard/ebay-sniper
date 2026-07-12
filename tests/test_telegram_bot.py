"""Tests for TelegramBot startup behavior."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from sniper.telegram_bot import TelegramBot


def test_start_uses_run_polling(monkeypatch):
    fake_app = MagicMock()
    fake_builder = MagicMock()
    fake_builder.token.return_value = fake_builder
    fake_builder.build.return_value = fake_app

    monkeypatch.setattr("sniper.telegram_bot.Application.builder", lambda: fake_builder)

    bot = TelegramBot(MagicMock(), MagicMock(), MagicMock(), MagicMock())

    bot.start()

    fake_app.run_polling.assert_called_once_with(stop_signals=None)


@pytest.mark.asyncio
async def test_watch_command_shows_actionable_example(monkeypatch):
    fake_app = MagicMock()
    fake_builder = MagicMock()
    fake_builder.token.return_value = fake_builder
    fake_builder.build.return_value = fake_app

    monkeypatch.setattr("sniper.telegram_bot.Application.builder", lambda: fake_builder)

    bot = TelegramBot(MagicMock(), MagicMock(), MagicMock(), MagicMock())
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = []

    await bot.watch_command(update, context)

    update.message.reply_text.assert_awaited_once()
    message, = update.message.reply_text.await_args.args
    assert "/watch 206406145417 650" in message
    assert "parse_mode" not in update.message.reply_text.await_args.kwargs


@pytest.mark.asyncio
async def test_search_command_escapes_html_entities(monkeypatch):
    fake_app = MagicMock()
    fake_builder = MagicMock()
    fake_builder.token.return_value = fake_builder
    fake_builder.build.return_value = fake_app

    monkeypatch.setattr("sniper.telegram_bot.Application.builder", lambda: fake_builder)

    ebay_client = MagicMock()
    ebay_client.search_auctions = AsyncMock(
        return_value=[
            {
                "title": "Saphire Radeon <max_bid> & more",
                "currentBidPrice": {"value": "642.00", "currency": "GBP"},
                "itemId": "v1|1234567890|0",
            }
        ]
    )

    bot = TelegramBot(MagicMock(), MagicMock(), MagicMock(), ebay_client)
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["Saphire", "Radeon"]

    await bot.search_command(update, context)

    update.message.reply_text.assert_awaited_once()
    message, = update.message.reply_text.await_args.args
    assert "&lt;max_bid&gt;" in message
    assert "<max_bid>" not in message
    assert "Saphire Radeon &lt;max_bid&gt; &amp; more" in message
    assert "💰 642.00 GBP" in message
    assert "parse_mode" in update.message.reply_text.await_args.kwargs
    assert update.message.reply_text.await_args.kwargs["parse_mode"] == "HTML"
