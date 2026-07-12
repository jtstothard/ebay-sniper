# eBay Sniper Service

A self-hosted auction sniping service for eBay UK. Monitors auctions and places proxy bids in the final seconds via the eBay Offer API. Supports multiple interfaces: Telegram bot, web dashboard, CLI, and MCP server for Hermes integration.

## Features

- **Smart Sniping**: Automatically places bids 8 seconds before auction end
- **Multiple Interfaces**: Web dashboard, Telegram bot, CLI, and MCP server
- **NTP Sync**: Accurate timing with NTP clock synchronization
- **Retry Logic**: Failed bids are retried at 3 seconds before end
- **SQLite Storage**: Simple, reliable database with bid logging
- **Docker Ready**: Easy deployment with docker-compose

## Architecture

```
                    ┌─────────────────────────────────────────────────┐
                    │           eBay Sniper Service                   │
                    │           (Python / FastAPI)                    │
                    │                                                 │
                    │  ┌───────────┐  ┌────────────┐  ┌───────────┐  │
                    │  │ FastAPI   │  │ Scheduler  │  │ eBay API  │  │
                    │  │ Web Server│  │ (APScheduler│  │ Client    │  │
                    │  │           │  │  + NTP)    │  │           │  │
                    │  │ /api/*    │  │            │  │ Browse    │  │
                    │  │ /dashboard│  │ triggers   │  │ Offer     │  │
                    │  └─────┬─────┘  └──────┬─────┘  └─────┬─────┘ │
                    │        │               │              │       │
                    │  ┌─────┴─────┐         │              │       │
                    │  │ MCP Server│         │              │       │
                    │  │ (stdio)   │         │              │       │
                    │  └─────┬─────┘         │              │       │
                    │  ┌─────┴─────┐         │              │       │
                    │  │ Telegram  │         │              │       │
                    │  │ Bot       │         │              │       │
                    │  └─────┬─────┘         │              │       │
                    │        │               │              │       │
                    │  ┌─────┴───────────────┴──────────────┴─────┐ │
                    │  │         Core Logic (shared)               │ │
                    │  │  - WatchStore (SQLite)                     │ │
                    │  │  - SniperEngine (bid orchestration)        │ │
                    │  │  - AuthManager (OAuth token store)         │ │
                    │  │  - NotificationManager                     │ │
                    │  └───────────────────────────────────────────┘ │
                    └─────────────────────────────────────────────────┘
```

## Installation

### Docker (Recommended)

1. Clone the repository
2. Copy `.env.example` to `.env.local` and configure your credentials
3. Run with docker-compose:

```bash
docker compose up -d
```

The service will be available at `http://localhost:8088`

### Local Development

1. Install dependencies:

```bash
pip install -e .
```

2. Configure environment variables (see `.env.example`)

3. Run the service:

```bash
python -m sniper.main
```

## Configuration

Configure via environment variables (see `.env.example`):

- `EBAY_APP_ID`: eBay application ID (required)
- `EBAY_CERT_ID`: eBay certificate ID (required)
- `EBAY_DEV_ID`: eBay developer ID (required)
- `EBAY_ENVIRONMENT`: `production` or `sandbox` (default: production)
- `TELEGRAM_BOT_TOKEN`: Telegram bot token (optional)
- `TELEGRAM_CHAT_ID`: Telegram chat ID for notifications (optional)
- `WEB_PORT`: Web server port (default: 8088)
- `BID_OFFSET_SECONDS`: Seconds before end to place bid (default: 8)
- `BID_RETRY_OFFSET_SECONDS`: Retry offset (default: 3)

## Usage

### Web Dashboard

Open `http://localhost:8088/dashboard` in your browser.

### CLI

```bash
# Search for auctions
sniper search "nintendo switch"

# Add a watch
sniper watch 287456575036 --max-bid 50.00

# List active watches
sniper list

# Cancel a watch
sniper cancel <watch_id>

# Check status
sniper status
```

### Telegram Bot

Commands:
- `/watch <item_id_or_url> <max_bid>` - Add a watch
- `/list` - List active watches
- `/cancel <watch_id_or_item_id>` - Cancel a watch
- `/search <query>` - Search eBay auctions
- `/status` - Show service status

### REST API

```bash
# List watches
curl http://localhost:8088/api/watches

# Add a watch
curl -X POST http://localhost:8088/api/watches \
  -H "Content-Type: application/json" \
  -d '{"item_id": "287456575036", "max_bid": 50.00}'

# Get watch details
curl http://localhost:8088/api/watches/<watch_id>

# Cancel a watch
curl -X DELETE http://localhost:8088/api/watches/<watch_id>

# Search auctions
curl "http://localhost:8088/api/search?q=nintendo%20switch"
```

### MCP Server (Hermes Integration)

The MCP server exposes tools for programmatic watch management:

- `add_watch(item_id, max_bid)` - Add a watch
- `list_watches(status)` - List watches
- `get_watch(watch_id)` - Get watch details
- `cancel_watch(watch_id)` - Cancel a watch
- `search_auctions(query)` - Search eBay
- `get_status()` - Get service status

## Important Notes

### Bid Placement is Stubbed

Until eBay grants the `buy.offer.auction` scope, bid placement is **stubbed**. The service logs:
```
STUB: bid not actually placed - item=..., max_amount=...
```

When the scope is granted, update `config.BID_PLACEMENT_STUBBED = false` and implement the real API call in `ebay_client.py`.

### Production Browse API Works

The Browse API works in production and is used for:
- Searching auctions
- Fetching item details
- Getting current prices

### NTP Synchronization

The service syncs with `pool.ntp.org` on startup to ensure accurate snipe timing. Check the NTP offset in the dashboard or via `/api/status`.

## Testing

Run tests with pytest:

```bash
pytest tests/
```

## Development

Project structure:

```
ebay-sniper/
├── src/sniper/
│   ├── core/           # Core logic (db, sniper, auth, ebay_client, ntp)
│   ├── web/            # FastAPI app + templates
│   ├── scheduler.py    # APScheduler setup
│   ├── telegram_bot.py # Telegram bot
│   ├── cli.py          # CLI (Typer)
│   ├── mcp_server.py   # MCP server
│   └── main.py         # Entry point
├── tests/              # Unit tests
├── skill/              # Hermes skill
├── Dockerfile
└── docker-compose.yml
```

## License

MIT