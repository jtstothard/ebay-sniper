# Interface Usage Guide

This document provides detailed examples for each interface supported by eBay Sniper.

## Web Dashboard

### Access
Open `http://localhost:8088/dashboard` in your browser.

### Features
- View all active watches with countdown timers
- Add new watches via the form (item URL or ID + max bid)
- Cancel watches with one click
- Auto-refreshes every 30 seconds

### Example Workflow
1. Open dashboard
2. Find an auction on eBay (e.g., `https://www.ebay.co.uk/itm/287456575036`)
3. Copy the URL or item ID (`287456575036`)
4. Paste in the "Item URL/ID" field
5. Enter your maximum bid (e.g., `50.00`)
6. Click "Add Watch"
7. Watch appears in the table with countdown

### Troubleshooting
- If dashboard doesn't load, check `WEB_PORT` in `.env.local`
- If form submission fails, check browser console for errors
- Ensure service is running: `curl http://localhost:8088/api/status`

## Telegram Bot

### Setup
1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Get the token and add to `.env.local`
3. Get your chat ID and add to `.env.local`
4. Restart the service

### Commands

#### `/watch <item_id_or_url> <max_bid>`
Add an auction to your watch list.

```
/watch 287456575036 50.00
```

Or with URL:
```
/watch https://www.ebay.co.uk/itm/287456575036 50.00
```

**Response:**
```
✅ Watch added!
📦 Nintendo Switch OLED White
⏰ Ends in: 2h 34m 12s
💰 Max bid: £50.00
🔢 Watch ID: abc123-def456
```

#### `/list`
List all active watches.

```
/list
```

**Response:**
```
📋 Active Watches (3):

1. Nintendo Switch OLED White
   Ends: 2h 34m 12s | Max bid: £50.00
   Watch ID: abc123-def456

2. PS5 Digital Edition
   Ends: 5h 12m 45s | Max bid: £400.00
   Watch ID: ghi789-jkl012
```

#### `/cancel <watch_id_or_item_id>`
Cancel a watch.

```
/watch abc123-def456
```

**Response:**
```
❌ Watch cancelled: abc123-def456
```

Or with item ID:
```
/watch 287456575036
```

#### `/search <query>`
Search eBay auctions.

```
/search nintendo switch
```

**Response:**
```
🔍 Search results (5):

1. Nintendo Switch OLED White - £280.00
   Item: 287456575036 | Ends: 2h 34m

2. Nintendo Switch with Mario Kart - £250.00
   Item: 123456789012 | Ends: 4h 12m

/watch <item_id> <max_bid> to add a watch
```

#### `/status`
Check service status.

```
/status
```

**Response:**
```
✅ eBay Sniper Status
🌐 eBay API: Connected
📍 NTP Offset: +0.023s
🤖 Bid Placement: STUBBED
📊 Active Watches: 3
```

### Notifications
The bot proactively sends notifications for:
- ✅ Bid placed (successful or stubbed)
- 🏆 Auction won
- 💔 Auction lost
- ⚠️ Outbid warning (if checked before end)
- ❌ Errors (API failures, invalid item IDs)

### Troubleshooting
- **Bot not responding**: Check `TELEGRAM_BOT_TOKEN` is correct
- **No notifications**: Verify `TELEGRAM_CHAT_ID` matches your account
- **"Unauthorized" error**: Ensure you've messaged the bot first

## CLI

**⚠️ Important:** CLI writes watches to the database but does not schedule jobs. For snipes to execute, use the web dashboard, Telegram bot, or REST API instead. See [docs/SOURCE-OF-TRUTH.md](SOURCE-OF-TRUTH.md) for details.

### Installation
```bash
pip install -e .
```

### Commands

#### `sniper search <query> [--limit N]`
Search eBay auctions.

```bash
sniper search "nintendo switch" --limit 10
```

**Output:**
```
Searching eBay for: nintendo switch

1. Nintendo Switch OLED White
   Item ID: 287456575036
   Current Bid: £280.00
   Ends: 2024-07-12 14:30:00 UTC

2. Nintendo Switch with Mario Kart
   Item ID: 123456789012
   Current Bid: £250.00
   Ends: 2024-07-12 16:45:00 UTC
```

#### `sniper watch <item_id_or_url> --max-bid <amount> [--source <source>]`
Add a watch.

```bash
sniper watch 287456575036 --max-bid 50.00
```

Or with URL:
```bash
sniper watch https://www.ebay.co.uk/itm/287456575036 --max-bid 50.00
```

**Output:**
```
✅ Watch added successfully!

Item: Nintendo Switch OLED White
Item ID: 287456575036
Watch ID: abc123-def456
Max Bid: £50.00
Ends: 2024-07-12 14:30:00 UTC
```

#### `sniper list [--status <status>]`
List watches.

```bash
sniper list
```

**Output:**
```
Active Watches (3):

1. Nintendo Switch OLED White
   Watch ID: abc123-def456
   Item ID: 287456575036
   Max Bid: £50.00
   Status: active
   Ends: 2024-07-12 14:30:00 UTC

2. PS5 Digital Edition
   Watch ID: ghi789-jkl012
   Item ID: 987654321098
   Max Bid: £400.00
   Status: active
   Ends: 2024-07-12 17:45:00 UTC
```

Filter by status:
```bash
sniper list --status won
```

#### `sniper cancel <watch_id>`
Cancel a watch.

```bash
sniper cancel abc123-def456
```

**Output:**
```
✅ Watch cancelled: abc123-def456
```

#### `sniper status`
Check service status.

```bash
sniper status
```

**Output:**
```
eBay Sniper Status
------------------
Service: Running
eBay API: Connected
NTP Offset: +0.023s
Bid Placement: STUBBED
Active Watches: 3
Total Watches: 15
```

### Troubleshooting
- **Command not found**: Ensure you ran `pip install -e .` or added the venv to PATH
- **"eBay API error"**: Check credentials in `.env.local`
- **"Invalid item ID"**: Verify the item exists on eBay

## REST API

### Base URL
`http://localhost:8088/api`

### Endpoints

#### GET /watches
List all watches.

```bash
curl http://localhost:8088/api/watches
```

**Response:**
```json
{
  "watches": [
    {
      "id": "abc123-def456",
      "item_id": "287456575036",
      "title": "Nintendo Switch OLED White",
      "max_bid": 50.00,
      "status": "active",
      "auction_end_time": "2024-07-12T14:30:00Z",
      "created_at": "2024-07-12T12:00:00Z"
    }
  ]
}
```

Query parameters:
- `?status=active` - Filter by status

#### POST /watches
Add a watch.

```bash
curl -X POST http://localhost:8088/api/watches \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "287456575036",
    "max_bid": 50.00
  }'
```

**Response:**
```json
{
  "id": "abc123-def456",
  "item_id": "287456575036",
  "title": "Nintendo Switch OLED White",
  "max_bid": 50.00,
  "status": "active",
  "auction_end_time": "2024-07-12T14:30:00Z"
}
```

#### GET /watches/{id}
Get watch details.

```bash
curl http://localhost:8088/api/watches/abc123-def456
```

#### DELETE /watches/{id}
Cancel a watch.

```bash
curl -X DELETE http://localhost:8088/api/watches/abc123-def456
```

**Response:**
```json
{
  "success": true,
  "message": "Watch cancelled"
}
```

#### GET /search?q={query}
Search eBay auctions.

```bash
curl "http://localhost:8088/api/search?q=nintendo%20switch"
```

**Response:**
```json
{
  "results": [
    {
      "item_id": "287456575036",
      "title": "Nintendo Switch OLED White",
      "price": "£280.00",
      "auction_end_time": "2024-07-12T14:30:00Z"
    }
  ]
}
```

#### GET /status
Service status.

```bash
curl http://localhost:8088/api/status
```

**Response:**
```json
{
  "service": "running",
  "ebay_api": "connected",
  "ntp_offset": 0.023,
  "bid_placement_stubbed": true,
  "active_watches": 3
}
```

### Troubleshooting
- **404 errors**: Check endpoint path is correct
- **"eBay API error"**: Verify credentials and network
- **"Invalid request"**: Check JSON syntax

## MCP Server (Hermes Integration)

**⚠️ Important:** MCP server writes watches to the database but does not schedule jobs. For snipes to execute, use the web dashboard, Telegram bot, or REST API instead. See [docs/SOURCE-OF-TRUTH.md](SOURCE-OF-TRUTH.md) for details.

### Usage
The MCP server runs via stdio and exposes these tools:

#### `add_watch(item_id, max_bid)`
Add a watch.

```json
{
  "name": "add_watch",
  "arguments": {
    "item_id": "287456575036",
    "max_bid": 50.00
  }
}
```

#### `list_watches(status)`
List watches (optional status filter).

```json
{
  "name": "list_watches",
  "arguments": {
    "status": "active"
  }
}
```

#### `get_watch(watch_id)`
Get watch details.

```json
{
  "name": "get_watch",
  "arguments": {
    "watch_id": "abc123-def456"
  }
}
```

#### `cancel_watch(watch_id)`
Cancel a watch.

```json
{
  "name": "cancel_watch",
  "arguments": {
    "watch_id": "abc123-def456"
  }
}
```

#### `search_auctions(query, limit)`
Search eBay.

```json
{
  "name": "search_auctions",
  "arguments": {
    "query": "nintendo switch",
    "limit": 10
  }
}
```

#### `get_status()`
Get service status.

```json
{
  "name": "get_status",
  "arguments": {}
}
```

### Troubleshooting
- **"Tool not found"**: Check MCP server is running
- **Stdio errors**: Verify MCP client configuration
- **"Invalid arguments"**: Check parameter types

## Common Workflows

### Workflow 1: Find and Watch an Auction
1. **Search** via CLI: `sniper search "ps5"`
2. **Pick an item** from results
3. **Add watch** via Telegram: `/watch 123456789 400.00`
4. **Monitor** via dashboard or `/list`

### Workflow 2: Bulk Watch Management
1. **List all active**: `sniper list --status active`
2. **Cancel unwanted**: `sniper cancel <watch_id>`
3. **Add new ones**: `sniper watch <item_id> --max-bid <amount>`

### Workflow 3: Hermes Integration
1. **Ask Hermes**: "Find PS5 auctions under £300"
2. **Hermes calls**: `search_auctions("ps5", 10)`
3. **Ask Hermes**: "Watch item 123456789 for £250"
4. **Hermes calls**: `add_watch("123456789", 250.00)`