# Architecture

## System Overview

eBay Sniper is a self-hosted Python service that monitors eBay auctions and orchestrates bid placement. It uses FastAPI for the web server, APScheduler for job scheduling, and SQLite for data persistence.

## Components

### Core Services

#### FastAPI Web Server (`src/sniper/web/app.py`)
Provides REST API endpoints and a web dashboard:
- `GET /api/watches` - List all watches
- `POST /api/watches` - Add a watch
- `GET /api/watches/{id}` - Get watch details
- `DELETE /api/watches/{id}` - Cancel a watch
- `GET /api/search?q={query}` - Search eBay auctions
- `GET /api/status` - Service health and status
- `/dashboard` - Web UI (Jinja2 template)

#### Scheduler (`src/sniper/scheduler.py`)
Uses APScheduler with SQLite job store:
- Schedules snipe jobs at `auction_end_time - BID_OFFSET_SECONDS`
- Schedules result checks at `auction_end_time + RESULT_CHECK_DELAY_SECONDS`
- Implements retry logic at `auction_end_time - BID_RETRY_OFFSET_SECONDS`
- Syncs with NTP server for accurate timing

#### Core Logic (`src/sniper/core/`)

**Database (`db.py`)**
SQLite with three tables:
- `watches` - Active and historical watch records
- `tokens` - OAuth token storage
- `bid_log` - Event log for debugging

**SniperEngine (`sniper.py`)**
Orchestrates the watch lifecycle:
- `add_watch()` - Validate and store watch
- `cancel_watch()` - Remove active watch
- `execute_snipe()` - Place bid at scheduled time
- `check_result()` - Determine win/loss after auction end

**AuthManager (`auth.py`)**
Manages eBay OAuth tokens:
- `get_app_token()` - Client credentials for Browse API
- `get_user_token()` - User token for Offer API (when scope granted)
- Auto-refreshes expired tokens

**eBay Client (`ebay_client.py`)**
Wrapper for eBay APIs:
- `search_auctions()` - Browse API search
- `get_item()` - Browse API item details
- `get_bidding()` - Offer API bidding info (stubbed)
- `place_proxy_bid()` - Offer API bid placement (stubbed)

**NTP Client (`ntp.py`)**
Clock synchronization:
- Queries NTP server on startup
- Calculates offset between system clock and NTP
- Applies offset to all scheduled jobs

### Interfaces

#### Telegram Bot (`src/sniper/telegram_bot.py`)
Uses python-telegram-bot (async):
- Commands: `/watch`, `/list`, `/cancel`, `/search`, `/status`
- Proactive notifications on bid placement and auction results
- Accepts both item IDs and eBay URLs

#### CLI (`src/sniper/cli.py`)
Uses Typer:
- `sniper search <query>`
- `sniper watch <item_id> --max-bid <amount>`
- `sniper list [--status <status>]`
- `sniper cancel <watch_id>`
- `sniper status`

#### MCP Server (`src/sniper/mcp_server.py`)
Stdio MCP server for Hermes integration:
- Exposes tools: `add_watch`, `list_watches`, `get_watch`, `cancel_watch`, `search_auctions`, `get_status`
- JSON-RPC over stdio

### Data Flow

#### Adding a Watch
```
User (CLI/Web/Telegram/MCP)
    ↓
FastAPI / Interface Layer
    ↓
SniperEngine.add_watch()
    ↓
eBayClient.get_item() - validate item via Browse API
    ↓
WatchStore - save to SQLite
    ↓
Scheduler - schedule execute_snipe at end_time - 8s
    ↓
Scheduler - schedule check_result at end_time + 30s
```

#### Executing a Snipe
```
Scheduler triggers at scheduled time
    ↓
SniperEngine.execute_snipe()
    ↓
eBayClient.place_proxy_bid()
    ↓
If BID_PLACEMENT_STUBBED=true: log stub, return mock
If BID_PLACEMENT_STUBBED=false: call eBay Offer API
    ↓
WatchStore - update bid_placed flag
    ↓
NotificationManager - send Telegram notification
```

#### Checking Result
```
Scheduler triggers at end_time + 30s
    ↓
SniperEngine.check_result()
    ↓
eBayClient.get_item() - fetch final auction state
    ↓
WatchStore - update status (won/lost), final_price
    ↓
NotificationManager - send result notification
```

## Configuration

All settings via environment variables (see `.env.example`):

**eBay API:**
- `EBAY_APP_ID`, `EBAY_CERT_ID`, `EBAY_DEV_ID` - API credentials
- `EBAY_ENVIRONMENT` - `production` or `sandbox`
- `EBAY_MARKETPLACE` - Marketplace ID (default: EBAY_GB)

**Timing:**
- `BID_OFFSET_SECONDS` - Seconds before end to bid (default: 8)
- `BID_RETRY_OFFSET_SECONDS` - Retry offset (default: 3)
- `RESULT_CHECK_DELAY_SECONDS` - Delay before checking result (default: 30)
- `NTP_SERVER` - NTP server for clock sync (default: pool.ntp.org)

**Web Server:**
- `WEB_PORT` - Port for web server (default: 8088)
- `WEB_HOST` - Host binding (default: 0.0.0.0)

**Telegram:**
- `TELEGRAM_BOT_TOKEN` - Bot token
- `TELEGRAM_CHAT_ID` - Chat ID for notifications

**Stub Control:**
- `BID_PLACEMENT_STUBBED` - `true` (stub) or `false` (live)

## Deployment

### Docker (Recommended)
```yaml
services:
  sniper:
    build: .
    ports:
      - "8088:8088"
    volumes:
      - ./data:/data
    env_file:
      - .env.local
```

### Local Development
```bash
pip install -e .
python -m sniper.main
```

## Security Considerations

- `.env.local` contains secrets - never commit to git
- OAuth tokens stored in SQLite (encrypted in production)
- All API calls use HTTPS
- Web dashboard has no authentication (run behind reverse proxy in production)
- Telegram bot tokens grant bot control - keep secure

## Performance

- SQLite handles thousands of watches without issues
- APScheduler with SQLite job store persists across restarts
- NTP sync adds ~50ms overhead on startup
- Async HTTP client (httpx) for all eBay API calls

## Monitoring

### Service Status
`GET /api/status` returns:
- Service health
- eBay API connectivity
- NTP offset
- Bid placement stub status
- Active watch count

### Logs
Check logs via:
- Docker: `docker compose logs -f sniper`
- Local: terminal output
- Dashboard: visual status indicators

### Bid Log
`GET /api/watches/{id}/log` returns event history for a watch.