# eBay Sniper

A self-hosted auction monitoring service for eBay. Search for auctions, add them to your watch list, and get notified when they're ending. Bid placement is currently stubbed pending eBay API scope approval.

## What Works Today

- **Search**: Find active auctions via eBay Browse API (CLI, web, Telegram, MCP)
- **Watch**: Add items to your watch list with max-bid targets
- **Monitor**: Track auctions via web dashboard, Telegram bot, CLI, or MCP server
- **Notifications**: Get alerts via Telegram when auctions end or status changes

## What's Pending

- **Bid Placement**: Currently stubbed. eBay requires manual approval for the `buy.offer.auction` OAuth scope before actual bids can be placed. The service logs stubbed bids and simulates success for testing workflows.

## Quickstart (Docker - Recommended)

```bash
# 1. Clone and configure
git clone <your-repo-url>
cd ebay-sniper
cp .env.example .env.local
# Edit .env.local with your eBay credentials

# 2. Start the service
docker compose up -d

# 3. Access the dashboard
open http://localhost:8088/dashboard
```

See [SETUP.md](SETUP.md) for detailed setup instructions, including how to get eBay API credentials and configure Telegram.

## Interfaces

### Web Dashboard
- URL: `http://localhost:8088/dashboard`
- View active watches, add new ones, cancel existing watches
- Auto-refreshes every 30 seconds

### Telegram Bot
Commands:
- `/watch <item_id_or_url> <max_bid>` - Add a watch
- `/list` - List active watches
- `/cancel <watch_id_or_item_id>` - Cancel a watch
- `/search <query>` - Search eBay auctions
- `/status` - Show service status

Example:
```
/watch 287456575036 50.00
```

### CLI
**Note:** CLI writes watches to the database but does not schedule jobs. For snipes to execute, use the web dashboard, Telegram bot, or REST API instead. See [docs/SOURCE-OF-TRUTH.md](docs/SOURCE-OF-TRUTH.md) for details.

```bash
# Search for auctions (safe - read-only)
sniper search "nintendo switch"

# List watches (safe - read-only from DB)
sniper list

# Check status (safe - read-only)
sniper status

# Add a watch (limited - stores to DB but does not schedule)
sniper watch 287456575036 --max-bid 50.00
# Service restart required to schedule this watch

# Cancel a watch (limited - marks cancelled but does not unschedule job)
sniper cancel <watch_id>
# Service restart required to clear scheduled job
```

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

# Service status
curl http://localhost:8088/api/status
```

### MCP Server (Hermes Integration)
**Note:** MCP server writes watches to the database but does not schedule jobs. For snipes to execute, use the web dashboard, Telegram bot, or REST API instead. See [docs/SOURCE-OF-TRUTH.md](docs/SOURCE-OF-TRUTH.md) for details.

The MCP server exposes tools for programmatic watch management:
- `add_watch(item_id, max_bid)` - Add a watch (limited - stores to DB but does not schedule)
- `list_watches(status)` - List watches (safe - read-only from DB)
- `get_watch(watch_id)` - Get watch details (safe - read-only)
- `cancel_watch(watch_id)` - Cancel a watch (limited - marks cancelled but does not unschedule job)
- `search_auctions(query)` - Search eBay (safe - read-only)
- `get_status()` - Get service configuration (safe - read-only)

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
│  │  - SniperEngine (watch orchestration)      │ │
│  │  - AuthManager (OAuth token store)         │ │
│  │  - NotificationManager                     │ │
│  └───────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

## Configuration

All configuration is via environment variables. See `.env.example` for the complete list:

**Required:**
- `EBAY_APP_ID` - eBay application ID
- `EBAY_CERT_ID` - eBay certificate ID
- `EBAY_DEV_ID` - eBay developer ID
- `EBAY_ENVIRONMENT` - `production` or `sandbox` (default: production)
- `BID_PLACEMENT_STUBBED` - Set to `true` (default) until scope is granted

**Optional:**
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `TELEGRAM_CHAT_ID` - Telegram chat ID for notifications
- `WEB_PORT` - Web server port (default: 8088)
- `BID_OFFSET_SECONDS` - Seconds before end to place bid (default: 8)
- `NTP_SERVER` - NTP server for clock sync (default: pool.ntp.org)

## eBay API Scope Approval

Bid placement requires the `buy.offer.auction` OAuth scope, which must be manually approved by eBay. Until you receive approval:

1. The service will log stubbed bids: `STUB: bid not actually placed`
2. All other functionality (search, watch, monitor) works fully
3. When approved, set `BID_PLACEMENT_STUBBED=false` in `.env.local`

To request approval:
1. Go to [eBay Developers](https://developer.ebay.com/)
2. Navigate to your application settings
3. Request the `buy.offer.auction` scope for production use

## Troubleshooting

### Service won't start
- Check `.env.local` exists and contains required values
- Verify eBay credentials are correct
- Check logs: `docker compose logs -f sniper`

### Can't search or add watches
- Verify eBay API credentials are valid
- Check `EBAY_ENVIRONMENT` matches your credentials
- Visit `http://localhost:8088/api/status` for detailed error info

### Telegram bot not responding
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Ensure your account has messaged the bot first
- Check logs for authentication errors

### NTP sync errors
- Check network connectivity
- Try a different NTP server in `.env.local`
- NTP sync is optional but recommended for accurate timing

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

### Running tests
```bash
pytest tests/
```

See [DEVELOPER.md](DEVELOPER.md) for detailed development workflow, CI/CD setup, and pre-commit hooks.

### CI/CD
All pull requests run automated tests and code quality checks via GitHub Actions:
- Unit tests (pytest)
- Code formatting (black)
- Import sorting (isort)
- Coverage reporting (codecov)

Run the same checks locally before pushing:
```bash
pip install -e '.[dev]'
pip install pre-commit
pre-commit run --all-files
pytest tests/ -v
```

### Local development setup
```bash
# Install dependencies
pip install -e .

# Run the service
python -m sniper.main
```

## Limitations

- **Bid placement**: Stubbed until eBay grants `buy.offer.auction` scope
- **Marketplace**: Currently configured for eBay GB (UK), but other marketplaces supported
- **Single user**: No multi-user support - all watches share the same SQLite database
- **Clock accuracy**: NTP sync helps but relies on system clock and network latency

## Documentation

Comprehensive documentation is available:
- **[docs/INDEX.md](docs/INDEX.md)** - Complete documentation index
- **[SETUP.md](SETUP.md)** - Detailed setup guide
- **[docs/INTERFACES.md](docs/INTERFACES.md)** - Interface usage guide
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture
- **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[docs/LIMITATIONS.md](docs/LIMITATIONS.md)** - Current limitations and design decisions

## License

MIT