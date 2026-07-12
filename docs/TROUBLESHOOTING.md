# Troubleshooting

This guide covers common issues and their solutions.

## Service Won't Start

### Symptom
Service fails to start or exits immediately.

### Checks

#### 1. Verify Environment File
```bash
# Check if .env.local exists
ls -la .env.local

# Check required variables
grep -E "EBAY_APP_ID|EBAY_CERT_ID|EBAY_DEV_ID" .env.local
```

**Solution**: Copy `.env.example` to `.env.local` and fill in required values:
```bash
cp .env.example .env.local
# Edit .env.local with your credentials
```

#### 2. Check Docker Logs
```bash
docker compose logs -f sniper
```

**Common errors**:
- `KeyError: 'EBAY_APP_ID'` - Missing environment variable
- `httpx.HTTPStatusError: 401` - Invalid eBay credentials
- `sqlite3.OperationalError: unable to open database file` - Permission issue with data directory

#### 3. Verify eBay Credentials
Test credentials manually:
```bash
curl -X POST "https://api.ebay.com/identity/v1/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Basic <BASE64_ENCODED_APP_ID:CERT_ID>" \
  -d "grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope"
```

**Solution**: If you get a 401 error, your credentials are invalid. Regenerate them in the eBay Developer Portal.

#### 4. Check Port Availability
```bash
# Check if port is in use
lsof -i :8088
# or
netstat -tulpn | grep 8088
```

**Solution**: Change `WEB_PORT` in `.env.local` or stop conflicting service.

#### 5. Local Development Issues
```bash
# Verify Python version (requires 3.11+)
python --version

# Check if dependencies are installed
pip list | grep -E "fastapi|apscheduler|httpx"

# Try running in verbose mode
python -m sniper.main --verbose
```

## Can't Search or Add Watches

### Symptom
Search returns empty or errors when adding watches.

### Checks

#### 1. Test eBay API Connection
```bash
curl http://localhost:8088/api/status
```

Look for `"ebay_api": "connected"`.

#### 2. Check Marketplace Configuration
```bash
grep EBAY_MARKETPLACE .env.local
```

**Solution**: Set `EBAY_MARKETPLACE=EBAY_GB` for UK, `EBAY_US` for US, etc.

#### 3. Verify Environment Setting
```bash
grep EBAY_ENVIRONMENT .env.local
```

**Solution**: Ensure `EBAY_ENVIRONMENT` matches your credentials:
- Production credentials → `production`
- Sandbox credentials → `sandbox`

#### 4. Test Search Directly
```bash
curl "http://localhost:8088/api/search?q=nintendo"
```

**Error responses**:
- `401`: Credentials invalid or expired
- `403`: Scope missing or marketplace mismatch
- `500`: eBay API error

#### 5. Check Item ID Validity
```bash
# Test with known item ID
curl "https://api.ebay.com/buy/browse/v1/item/v1|287456575036|0" \
  -H "Authorization: Bearer <YOUR_TOKEN>"
```

**Solution**: Ensure item ID exists and is an active auction.

## Telegram Bot Not Responding

### Symptom
Bot doesn't respond to commands or sends no notifications.

### Checks

#### 1. Verify Bot Token
```bash
# Test token
curl "https://api.telegram.org/bot<TOKEN>/getMe"
```

**Expected response**:
```json
{
  "ok": true,
  "result": {
    "id": 123456789,
    "is_bot": true,
    "first_name": "YourBotName"
  }
}
```

**Solution**: If error, regenerate token via @BotFather.

#### 2. Verify Chat ID
```bash
# Get updates to find your chat ID
curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
```

Look for `"chat":{"id":123456}` in the response.

**Solution**: Ensure you've messaged the bot first, then use the chat ID from the response.

#### 3. Check Telegram Logs
```bash
docker compose logs sniper | grep -i telegram
```

**Common errors**:
- `Unauthorized: bot was blocked by the user` - Start the bot via `/start`
- `Bad Request: chat not found` - Wrong chat ID
- `Conflict: can't use getUpdates method while webhook is active` - Clear webhook

#### 4. Test Bot Manually
Send `/start` to the bot, then check logs:
```bash
docker compose logs -f sniper
# Send /status to your bot
```

**Solution**: If no logs appear, check `TELEGRAM_BOT_TOKEN` and restart service.

## NTP Sync Errors

### Symptom
Service logs NTP errors or timing seems off.

### Checks

#### 1. Test NTP Server
```bash
# Test default NTP server
ntpdate -q pool.ntp.org

# Or try alternative
ntpdate -q time.cloudflare.com
```

**Solution**: Change `NTP_SERVER` in `.env.local` to a working server.

#### 2. Check Network Connectivity
```bash
# Test DNS
nslookup pool.ntp.org

# Test connectivity
nc -zuv pool.ntp.org 123
```

**Solution**: Check firewall rules allow UDP port 123.

#### 3. Check Logs
```bash
docker compose logs sniper | grep -i ntp
```

**Common errors**:
- `No route to host` - Network issue
- `Connection refused` - Wrong NTP server or port
- `Request timed out` - Server slow or blocked

#### 4. Verify Offset
```bash
curl http://localhost:8088/api/status | jq .ntp_offset
```

**Acceptable range**: -1.0 to +1.0 seconds. Larger values indicate clock issues.

**Solution**: Sync system clock or use different NTP server.

## Bid Placement Issues

### Symptom
Bids not placed or always show as stubbed.

### Checks

#### 1. Check Stub Status
```bash
curl http://localhost:8088/api/status | jq .bid_placement_stubbed
```

**If `true`**: This is expected until eBay grants scope. See [LIMITATIONS.md](LIMITATIONS.md).

#### 2. Verify OAuth Scope
```bash
# Check token scope (requires valid user token)
curl -H "Authorization: Bearer <YOUR_TOKEN>" \
  "https://api.ebay.com/commerce/identity/v1/user" | jq .scope
```

Look for `https://api.ebay.com/oauth/api_scope/buy.offer.auction`.

**Solution**: If missing, request scope approval via eBay Developer Portal.

#### 3. Check Bid Logs
```bash
# Get log for a watch
curl http://localhost:8088/api/watches/<watch_id>/log
```

Look for events like `bid_placed`, `error`, etc.

#### 4. Test Bid Placement
```bash
# Try adding a test watch
curl -X POST http://localhost:8088/api/watches \
  -H "Content-Type: application/json" \
  -d '{"item_id": "287456575036", "max_bid": 50.00}'

# Wait for auction end or manually trigger via logs
```

**Solution**: Check logs for `STUB: bid not actually placed` message.

## Database Issues

### Symptom
Watches not persisting or database errors.

### Checks

#### 1. Verify Database File
```bash
# Check if database exists
ls -la data/sniper.db

# Check permissions
stat data/sniper.db

# Test database integrity
sqlite3 data/sniper.db "PRAGMA integrity_check;"
```

**Solution**: Fix permissions or restore from backup.

#### 2. Check Volume Mount (Docker)
```bash
# Verify volume is mounted
docker compose ps
docker inspect <container_id> | jq '.[0].Mounts'
```

**Solution**: Ensure `./data` is mounted to `/data` in container.

#### 3. Rebuild Database
```bash
# Stop service
docker compose down

# Backup existing database
cp data/sniper.db data/sniper.db.backup

# Remove and restart
rm data/sniper.db
docker compose up -d
```

**Warning**: This deletes all watches.

## Performance Issues

### Symptom
Service is slow or unresponsive.

### Checks

#### 1. Check Active Watch Count
```bash
curl http://localhost:8088/api/status | jq .active_watches
```

**Solution**: If >1000 watches, consider archiving old ones.

#### 2. Check System Resources
```bash
# Docker stats
docker stats sniper

# System resources
top
```

**Solution**: Increase CPU/memory allocation or reduce watch count.

#### 3. Check Scheduler Queue
```bash
docker compose logs sniper | grep scheduler
```

Look for job queue backlog.

#### 4. Optimize NTP Sync
Reduce NTP sync frequency in code if needed (currently only on startup).

## Logs and Debugging

### Enable Verbose Logging
Edit `.env.local`:
```bash
LOG_LEVEL=DEBUG
```

Restart service.

### Common Log Patterns

#### Successful startup
```
INFO:     Started server process
INFO:     Waiting for application startup
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8088
INFO:     NTP offset: +0.023s
INFO:     Scheduler started
INFO:     Telegram bot started
```

#### Watch added successfully
```
INFO:     Watch added: watch_id=abc123, item_id=287456575036
INFO:     Job scheduled: execute_snipe at 2024-07-12 14:29:52
INFO:     Job scheduled: check_result at 2024-07-12 14:30:30
```

#### Stubbed bid
```
WARNING:  STUB: bid not actually placed - item=287456575036, max_amount=50.00
INFO:     STUB: This is a mock bid. Real bids require buy.offer.auction scope.
```

#### API error
```
ERROR:    eBay API error: 401 Unauthorized
ERROR:    Failed to add watch: invalid credentials
```

### Getting Help

1. Check logs: `docker compose logs -f sniper`
2. Verify configuration: Compare `.env.local` with `.env.example`
3. Test endpoints: Use curl to test API endpoints
4. Check eBay Developer Portal: Verify credentials and scopes
5. Review this troubleshooting guide

If issues persist, create a GitHub issue with:
- Service logs
- Configuration (redact secrets)
- Steps to reproduce
- Expected vs actual behavior