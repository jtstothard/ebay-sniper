# Setup Guide

This guide walks you through setting up the eBay Sniper service from scratch.

## Prerequisites

- Docker (recommended) or Python 3.11+
- eBay Developer Account
- (Optional) Telegram Bot

## Step 1: Get eBay API Credentials

1. Go to [eBay Developers](https://developer.ebay.com/)
2. Sign in or create an account
3. Go to "My Account" → "Application Keys"
4. Create a new application (if needed)
5. You'll get three credentials:
   - **App ID** (Client ID)
   - **Cert ID** (Client Secret)
   - **Dev ID**

## Step 2: Configure Environment Variables

1. Copy the example configuration:
   ```bash
   cp .env.example .env.local
   ```

2. Edit `.env.local` and fill in your credentials:
   ```bash
   # Required: eBay API Credentials
   EBAY_APP_ID=your_actual_app_id_here
   EBAY_CERT_ID=your_actual_cert_id_here
   EBAY_DEV_ID=your_actual_dev_id_here
   
   # Required: Environment
   EBAY_ENVIRONMENT=production  # or 'sandbox'
   EBAY_MARKETPLACE=EBAY_GB     # or EBAY_US, etc.
   
   # Optional: Telegram (skip if not using)
   TELEGRAM_BOT_TOKEN=your_actual_bot_token
   TELEGRAM_CHAT_ID=your_actual_chat_id
   
   # Optional: Web server (defaults are fine)
   WEB_PORT=8088
   WEB_HOST=0.0.0.0
   
   # Optional: Snipe timing (defaults are fine)
   BID_OFFSET_SECONDS=8
   BID_RETRY_OFFSET_SECONDS=3
   RESULT_CHECK_DELAY_SECONDS=30
   
   # Optional: NTP server (default is fine)
   NTP_SERVER=pool.ntp.org
   
   # Required until eBay grants scope
   BID_PLACEMENT_STUBBED=true
   ```

**Important**: Never commit `.env.local` to git. It's ignored by `.gitignore`.

## Step 3: Optional - Set Up Telegram Bot

If you want Telegram notifications and commands:

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. BotFather gives you a token (like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
4. Get your chat ID:
   - Message your bot with any text
   - Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find `"chat":{"id":123456}` in the response
5. Add both to `.env.local`:
   ```bash
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   TELEGRAM_CHAT_ID=123456
   ```

## Step 4: Run the Service

### Docker (Recommended)

```bash
# Build and start
docker compose up -d

# Check logs
docker compose logs -f

# Stop
docker compose down
```

The web dashboard will be at `http://localhost:8088/dashboard`

### Local Development

```bash
# Install dependencies
pip install -e .

# Run the service
python -m sniper.main
```

## Step 5: Verify Setup

1. Check the service status:
   - Web: Visit `http://localhost:8088/api/status`
   - CLI: Run `sniper status`
   - Telegram: Send `/status` to your bot

2. Check the dashboard: `http://localhost:8088/dashboard`

3. Test with a sample watch:
   ```bash
   # CLI
   sniper watch 287456575036 --max-bid 50.00
   
   # Web
   # Visit dashboard and add a watch via the form
   
   # Telegram
   # Send: /watch 287456575036 50.00
   ```

## Step 6: About Bid Placement Stubbing

**Currently, bid placement is stubbed** (not actually placing bids) because eBay requires manual approval for the `buy.offer.auction` OAuth scope.

To check if you have the scope:
```bash
curl -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  "https://api.ebay.com/commerce/identity/v1/user"
```

Look for `scope` in the response. If you see `https://api.ebay.com/oauth/api_scope/buy.offer.auction`, you can:

1. Update `.env.local`:
   ```bash
   BID_PLACEMENT_STUBBED=false
   ```

2. Implement the real bid placement in `src/sniper/core/ebay_client.py` (replace the stub with the actual API call).

## Troubleshooting

### Service won't start
- Check `.env.local` exists and has required values
- Verify eBay credentials are correct
- Check logs: `docker compose logs` or look at terminal output

### Can't add watches
- Verify eBay API credentials are valid
- Check the service status endpoint for errors
- Ensure you're using a valid eBay item ID

### Telegram bot not responding
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Check `TELEGRAM_CHAT_ID` is correct
- Ensure your Telegram account has messaged the bot first

### NTP sync errors
- Check network connectivity
- Try a different NTP server in `.env.local`
- NTP sync is optional for basic operation but recommended for accurate sniping

## Next Steps

- Read the full [README.md](README.md) for usage examples
- Check [SPEC.md](SPEC.md) for technical details
- Explore the [tests/](tests/) directory for examples
- Review [docs/](docs/) for additional documentation

## Security Notes

- Keep `.env.local` private and never commit it
- Rotate eBay API tokens regularly
- Use a separate eBay developer account for testing
- Consider using a secrets manager in production
- The `data/sniper.db` file contains your watches - back it up regularly