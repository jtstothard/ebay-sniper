# Source of Truth: Watch State and Scheduler Jobs

## Summary

eBay Sniper has a **dual source-of-truth** system for active watches:

1. **SQLite watches table** - Stores watch metadata and state
2. **APScheduler job store** - Stores scheduled execution jobs

**Only the deployed service maintains full alignment between these two sources.**

## How It Works

### Deployed Service (Docker/Production)

The deployed service (`python -m sniper.main`) maintains full coordination:

- Reads watches from SQLite `watches` table
- Schedules jobs in APScheduler for each active watch
- Persists jobs to SQLite via SQLAlchemyJobStore (same DB file)
- On restart: loads watches from DB, restores scheduled jobs from APScheduler store
- All interfaces (web dashboard, Telegram bot, REST API) use this service

**Result:** watches table and APScheduler jobs stay in sync.

### CLI and MCP Server (Standalone)

When running CLI commands or MCP server directly:

- Read/write directly to SQLite `watches` table
- **Do NOT interact with APScheduler**
- Cannot schedule or cancel snipe jobs
- Cannot query job state or scheduled execution times

**Result:** Watches added via CLI/MCP are stored but not scheduled for execution.

## The Mismatch

### Scenario 1: Adding a Watch via CLI/MCP

```bash
# Add watch via CLI
sniper watch 287456575036 --max-bid 50.00
```

**What happens:**
- Watch is inserted into SQLite `watches` table
- No job is created in APScheduler
- Deployed service won't execute the snipe at auction end

**Verification:**
```bash
# CLI shows the watch
sniper list

# But deployed service has no scheduled job for it
curl http://localhost:8088/api/status | jq .scheduled_jobs
```

### Scenario 2: Cancelling a Watch via CLI/MCP

```bash
# Cancel via CLI
sniper cancel abc123-def456
```

**What happens:**
- Watch is marked as cancelled in SQLite `watches` table
- Scheduled job remains in APScheduler job store
- Job will fire at scheduled time and attempt to execute

**Result:** Phantom job attempts to snipe a cancelled watch.

### Scenario 3: Adding a Watch via Deployed Service Interface

```bash
# Add watch via REST API
curl -X POST http://localhost:8088/api/watches \
  -H "Content-Type: application/json" \
  -d '{"item_id": "287456575036", "max_bid": 50.00}'
```

**What happens:**
- Watch is inserted into SQLite `watches` table
- APScheduler jobs are created for snipe and result-check
- Both sources stay aligned

**Result:** Watch is properly scheduled and will execute.

## Current Limitations

### CLI Use

CLI is **read-only for deployment operations**:

✅ **Safe operations:**
- `sniper search` - Search eBay auctions (read-only)
- `sniper list` - List watches from database
- `sniper status` - Check service configuration

⚠️ **Limited operations:**
- `sniper watch` - Adds watch to DB but **does not schedule**
- `sniper cancel` - Cancels watch in DB but **does not unschedule job**

❌ **Not supported:**
- `sniper watch` cannot create scheduled jobs
- `sniper cancel` cannot remove scheduled jobs
- CLI cannot query APScheduler job state

### MCP Server Use

MCP server is **read-only for deployment operations**:

✅ **Safe operations:**
- `search_auctions()` - Search eBay auctions (read-only)
- `list_watches()` - List watches from database
- `get_watch()` - Get watch details from database
- `get_status()` - Get service configuration

⚠️ **Limited operations:**
- `add_watch()` - Adds watch to DB but **does not schedule**
- `cancel_watch()` - Cancels watch in DB but **does not unschedule job**

❌ **Not supported:**
- MCP cannot create scheduled jobs
- MCP cannot remove scheduled jobs
- MCP cannot query APScheduler job state

## Supported Workflows

### For Running Snipes (Deployed Service)

Use these interfaces to add and manage watches that will execute:

✅ **Web Dashboard** - `http://localhost:8088/dashboard`
✅ **Telegram Bot** - `/watch <item_id> <max_bid>`
✅ **REST API** - `POST /api/watches`

These interfaces use the deployed service and maintain full source-of-truth alignment.

### For Query and Inspection (CLI/MCP)

Use these interfaces to inspect state without modifying schedules:

✅ `sniper search` - Find auctions
✅ `sniper list` - See what's in the database
✅ `sniper status` - Check configuration
✅ MCP `list_watches()` - Query watches
✅ MCP `get_watch()` - Inspect watch details
✅ MCP `search_auctions()` - Find auctions

### For Bulk Operations (Manual Restart)

If you need CLI/MCP watch management capabilities:

1. Use CLI/MCP to modify watches table
2. Restart deployed service: `docker compose restart sniper`
3. Service reloads watches and reschedules jobs from database

**Warning:** This approach works but has race conditions during restart. Use only for maintenance, not frequent operations.

## Future Improvement Path

To enable full CLI/MCP watch management, the system needs:

1. **Scheduler API endpoint** - Expose scheduling via REST API
2. **CLI/MCP scheduler integration** - Connect to deployed scheduler service
3. **Unified access layer** - All interfaces route through deployed service
4. **Separate write path** - CLI/MCP call service endpoints instead of direct DB access

### Rough Implementation Plan

1. Add scheduler management endpoints to REST API:
   - `POST /api/schedule/<watch_id>` - Schedule jobs for a watch
   - `DELETE /api/schedule/<watch_id>` - Remove scheduled jobs

2. Update CLI to call service endpoints:
   ```python
   # Instead of db.add_watch()
   response = httpx.post(f"{API_BASE}/api/watches", data={...})
   # Let service handle both DB write and job scheduling
   ```

3. Update MCP server to call service endpoints:
   ```python
   # Instead of db.add_watch()
   async with httpx.AsyncClient() as client:
       await client.post(f"{API_BASE}/api/watches", json={...})
   ```

4. Deprecate direct DB access from CLI/MCP:
   - Keep read-only DB access for local inspection
   - Remove write DB access, route all writes through service

## Detecting Mismatches

### Check for Unscheduled Watches

```bash
# List active watches
docker exec -it ebay-sniper sniper list --status active

# Check scheduled jobs count (requires scheduler API or DB query)
docker exec -it ebay-sniper sqlite3 /data/sniper.db \
  "SELECT COUNT(*) FROM apscheduler_jobs;"
```

If counts differ, there's a mismatch.

### Check for Phantom Jobs

```bash
# Get all scheduled job IDs
docker exec -it ebay-sniper sqlite3 /data/sniper.db \
  "SELECT id FROM apscheduler_jobs;"

# Extract watch IDs from job IDs
# Job IDs are formatted as "snipe_<watch_id>" or "check_<watch_id>"

# Check if those watches still exist as active
docker exec -it ebay-sniper sqlite3 /data/sniper.db \
  "SELECT id FROM watches WHERE status='active';"
```

Jobs referencing non-active watches are phantom.

## Resolving Mismatches

### For Unscheduled Watches

Restart the deployed service to reschedule all active watches:

```bash
docker compose restart sniper
```

The service will:
1. Load all `status='active'` watches from database
2. Create APScheduler jobs for each
3. Align sources

### For Phantom Jobs

Restart the deployed service (as above). On startup, the service only schedules active watches, leaving stale jobs orphaned. They'll execute but fail to find the watch and log an error.

To clean them manually:

```bash
# Clear all APScheduler jobs (drastic, use with caution)
docker exec -it ebay-sniper sqlite3 /data/sniper.db \
  "DELETE FROM apscheduler_jobs;"
docker compose restart sniper
```

## Questions or Issues?

If you encounter source-of-truth issues:

1. Check which interface you're using (web/telegram/API vs CLI/MCP)
2. Verify the deployed service is running and accessible
3. Restart the service to force realignment
4. Open a GitHub issue with steps to reproduce