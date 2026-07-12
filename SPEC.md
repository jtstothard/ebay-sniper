# eBay Sniper Service — Build Spec

## Overview

A self-hosted auction sniping service for eBay UK. Monitors auctions, places
proxy bids in the final seconds via the eBay Offer API. Multiple interfaces:
Telegram bot, web dashboard, CLI, and MCP server for Hermes integration.

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
                    │  └─────┬─────┘  │ at end-8s  │  │ OAuth     │  │
                    │        │        └──────┬─────┘  └─────┬─────┘ │
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
                          │                    │
                    ┌─────┴─────┐        ┌─────┴─────┐
                    │ Telegram  │        │   eBay    │
                    │  API      │        │   APIs    │
                    └───────────┘        └───────────┘
```

## Components

### 1. Core Logic (`core/`)

#### `core/db.py` — SQLite WatchStore
Tables:
```sql
CREATE TABLE watches (
    id TEXT PRIMARY KEY,           -- UUID
    item_id TEXT NOT NULL,          -- eBay item ID (e.g. v1|287456575036|0)
    legacy_item_id TEXT,            -- numeric eBay item ID
    title TEXT,
    auction_end_time TEXT NOT NULL, -- ISO 8601 UTC
    max_bid REAL NOT NULL,          -- max bid amount in GBP
    currency TEXT DEFAULT 'GBP',
    status TEXT DEFAULT 'active',   -- active, won, lost, cancelled, error
    bid_placed INTEGER DEFAULT 0,   -- 0 = not yet, 1 = placed
    bid_amount REAL,                -- actual bid placed
    winning INTEGER,                -- 1 = winning after bid
    final_price REAL,               -- final auction price
    created_at TEXT NOT NULL,
    updated_at TEXT,
    notes TEXT,                     -- user notes
    source TEXT DEFAULT 'manual'    -- manual, telegram, cli, mcp, hermes
);

CREATE TABLE tokens (
    id INTEGER PRIMARY KEY,
    token_type TEXT NOT NULL,       -- 'user' or 'application'
    environment TEXT NOT NULL,      -- 'production' or 'sandbox'
    access_token TEXT,
    refresh_token TEXT,
    expires_at TEXT,
    scope TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE bid_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    watch_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    event TEXT NOT NULL,            -- scheduled, bid_placed, won, lost, error, outbid
    details TEXT,                   -- JSON
    FOREIGN KEY (watch_id) REFERENCES watches(id)
);
```

#### `core/sniper.py` — SniperEngine
- `add_watch(item_id, max_bid, source='manual')` — adds a watch, fetches auction details
- `cancel_watch(watch_id)` — cancels an active watch
- `list_watches(status='active')` — returns watches
- `get_watch(watch_id)` — returns single watch details
- `execute_snipe(watch_id)` — called by scheduler at end_time - 8s, places bid
- `check_result(watch_id)` — called after auction end, checks if won
- `_fetch_auction_details(item_id)` — uses Browse API to get title, end time, current bid

#### `core/auth.py` — AuthManager
- `get_app_token()` — client-credentials flow (for Browse API)
- `get_user_token()` — returns stored user token, refreshes if expired
- `refresh_user_token()` — uses refresh_token to get new access token
- Token stored encrypted in SQLite tokens table

#### `core/ebay_client.py` — eBay API Client
- `get_item(item_id)` — Browse API getItem
- `search_auctions(query, filters)` — Browse API search
- `get_bidding(item_id)` — Offer API GET /bidding/{item_id} (STUB until scope granted)
- `place_proxy_bid(item_id, max_amount)` — Offer API POST (STUB until scope granted)
- Must handle both production and sandbox environments

### 2. Scheduler (`scheduler.py`)
- Uses APScheduler with a persistent job store (SQLite)
- For each active watch: schedules `execute_snipe` at `end_time - 8 seconds`
- NTP sync: on startup, query NTP server, calculate clock offset, apply offset to all schedules
- Retry logic: if bid placement fails, retry once at end_time - 3s
- Result checker: schedules `check_result` at `end_time + 30s`

### 3. FastAPI Web Server (`web/app.py`)
REST API + minimal web dashboard:

#### API endpoints:
- `GET /api/watches` — list all watches (optional `?status=active`)
- `POST /api/watches` — add a watch `{item_id, max_bid, source?}`
- `GET /api/watches/{id}` — get watch details
- `DELETE /api/watches/{id}` — cancel watch
- `GET /api/watches/{id}/log` — get bid log for a watch
- `GET /api/search?q={query}` — search eBay auctions (proxied Browse API)
- `GET /api/status` — service health + eBay API connectivity status

#### Web dashboard:
- Simple HTML page at `/dashboard` (no JS framework needed — server-rendered Jinja2)
- Table of active watches with: item title, end time (countdown), max bid, status
- Form to add a new watch (item URL + max bid)
- Cancel button per watch
- Auto-refresh every 30 seconds via meta refresh

### 4. Telegram Bot (`telegram_bot.py`)
Uses python-telegram-bot (async).

Commands:
- `/watch <ebay_url_or_item_id> <max_bid>` — add a watch
- `/list` — list active watches
- `/cancel <watch_id_or_item_id>` — cancel a watch
- `/search <query>` — search eBay auctions
- `/status` — show service status

Proactive notifications:
- Watch added confirmation (with auction details)
- Bid placed notification (success/fail)
- Auction won/lost notification
- Outbid warning (if checked before end)
- Error notifications

Parse item URLs: accept both `https://www.ebay.co.uk/itm/123456789` and raw item IDs.

### 5. CLI (`cli.py`)
Uses Typer or Click. Talks to the same SQLite store directly (or calls the FastAPI API if running).

Commands:
```bash
sniper watch <item_id_or_url> --max-bid 95.00
sniper list [--status active|all]
sniper cancel <watch_id>
sniper search <query>
sniper status
```

### 6. MCP Server (`mcp_server.py`)
A stdio MCP server using the `mcp` Python package. Exposes tools:
- `add_watch(item_id, max_bid)` 
- `list_watches(status)`
- `cancel_watch(watch_id)`
- `search_auctions(query)`

This lets Hermes (or any MCP client) manage watches programmatically.

### 7. Hermes Skill
A skill at `~/.hermes/skills/ebay-sniper/SKILL.md` that wraps the CLI/MCP, so Jay can say "watch this eBay auction, max bid £50" in Telegram and Hermes adds it.

### 8. Docker
- `Dockerfile` — Python 3.12-slim, install deps, run with uvicorn + scheduler
- `docker-compose.yml` — single container, SQLite volume mount, env vars for:
  - `EBAY_APP_ID`, `EBAY_CERT_ID`, `EBAY_DEV_ID`
  - `EBAY_SANDBOX_APP_ID`, `EBAY_SANDBOX_CERT_ID`
  - `EBAY_ENVIRONMENT` (production/sandbox)
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID` (Jay's chat ID for notifications)
  - `WEB_PORT` (default 8088)
- Healthcheck hitting `/api/status`

## Tech Stack

- **Python 3.12+**
- **FastAPI** — web server + REST API
- **APScheduler** — job scheduling
- **python-telegram-bot** — Telegram bot
- **httpx** — async HTTP client for eBay APIs
- **Typer** — CLI
- **Jinja2** — web dashboard templates
- **SQLAlchemy** or raw sqlite3 — database
- **mcp** — MCP server (pip install mcp)
- **Docker** — containerization

## Directory Structure

```
ebay-sniper/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── README.md
├── src/
│   └── sniper/
│       ├── __init__.py
│       ├── main.py              # entry point: starts web server + scheduler + telegram bot
│       ├── config.py            # env var config
│       ├── core/
│       │   ├── __init__.py
│       │   ├── db.py            # SQLite WatchStore
│       │   ├── sniper.py        # SniperEngine
│       │   ├── auth.py          # AuthManager (OAuth)
│       │   ├── ebay_client.py   # eBay API client
│       │   └── ntp.py           # NTP clock offset
│       ├── scheduler.py         # APScheduler setup
│       ├── web/
│       │   ├── __init__.py
│       │   ├── app.py           # FastAPI app
│       │   ├── templates/
│       │   │   └── dashboard.html
│       │   └── static/
│       ├── telegram_bot.py      # Telegram bot
│       ├── cli.py               # CLI (Typer)
│       └── mcp_server.py        # MCP server
├── tests/
│   ├── test_db.py
│   ├── test_sniper.py
│   └── test_ebay_client.py
└── skill/
    └── SKILL.md                 # Hermes skill
```

## Key Design Decisions

1. **Bid placement is stubbed** until eBay grants `buy.offer.auction` scope.
   The stub logs the bid attempt and returns a mock success. When scope is
   granted, swap in the real API call. The stub clearly logs "STUB: bid not
   actually placed" so nobody is confused during testing.

2. **Production Browse API for listing discovery** — works now, tested.

3. **SQLite** — no external database needed. Single file, easy backup.

4. **NTP sync** — critical for a sniper. Query `pool.ntp.org` on startup,
   calculate offset between system clock and NTP, apply to all scheduled
   bid times.

5. **8-second snipe offset** — configurable. Default is end_time - 8s with
   a retry at end_time - 3s if the first attempt fails.

6. **OAuth token persistence** — user token stored in SQLite, auto-refreshed
   via refresh token. For now, the AuthManager uses client-credentials
   (app token) for Browse API. When scope is granted, add the user-token
   auth-code flow for the Offer API.

7. **Error handling** — if a bid fails, notify via Telegram immediately.
   Log all events to bid_log table for debugging.

8. **Marketplace** — default to EBAY_GB. Configurable via env var.

## Build Order

1. `core/db.py` + `core/config.py` (foundation)
2. `core/ebay_client.py` + `core/auth.py` (API connectivity)
3. `core/sniper.py` (watch management logic)
4. `core/ntp.py` + `scheduler.py` (timing engine)
5. `web/app.py` + templates (web dashboard + API)
6. `cli.py` (command-line interface)
7. `telegram_bot.py` (Telegram bot)
8. `mcp_server.py` (MCP server)
9. `Dockerfile` + `docker-compose.yml` (containerization)
10. `skill/SKILL.md` (Hermes skill)
11. `tests/` (unit tests for core logic)

## Verification

After build, verify:
- [ ] CLI: `sniper search "nintendo switch"` returns eBay auction results
- [ ] CLI: `sniper watch <item_id> --max-bid 50` adds a watch
- [ ] CLI: `sniper list` shows the watch
- [ ] Web: `http://localhost:8088/dashboard` shows the dashboard
- [ ] API: `GET /api/watches` returns JSON
- [ ] API: `POST /api/watches` adds a watch
- [ ] Scheduler: watch end_time triggers execute_snipe (check bid_log)
- [ ] Telegram: `/watch <url> 50` adds a watch and confirms
- [ ] Telegram: `/list` shows watches
- [ ] MCP: `add_watch` tool works via MCP client
- [ ] Docker: `docker compose up` starts the service cleanly
