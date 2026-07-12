# eBay Sniper Documentation

Comprehensive documentation for the eBay Sniper service.

## Getting Started

- **[README.md](../README.md)** - Project overview, quickstart, and features
- **[SETUP.md](../SETUP.md)** - Detailed setup guide with prerequisites and configuration
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - How to contribute to the project

## User Guides

- **[INTERFACES.md](INTERFACES.md)** - Complete guide for all interfaces:
  - Web Dashboard
  - Telegram Bot
  - CLI
  - REST API
  - MCP Server (Hermes Integration)

## Technical Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture, components, and data flows
- **[LIMITATIONS.md](LIMITATIONS.md)** - Current limitations and design decisions
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
- **[SOURCE-OF-TRUTH.md](SOURCE-OF-TRUTH.md)** - Watch state and scheduler job coordination

## Specifications

- **[../SPEC.md](../SPEC.md)** - Detailed build specification and component details

## Quick Reference

### Essential Commands

```bash
# Docker (recommended)
docker compose up -d           # Start service
docker compose logs -f sniper  # View logs
docker compose down            # Stop service

# CLI
sniper search "query"          # Search auctions
sniper watch <id> --max-bid 50 # Add watch
sniper list                    # List watches
sniper status                  # Service status

# API
curl http://localhost:8088/api/status        # Status
curl http://localhost:8088/api/watches       # List watches
curl "http://localhost:8088/api/search?q=ps5" # Search
```

### Key Files

- `.env.example` - Configuration template
- `.env.local` - Your local configuration (don't commit)
- `pyproject.toml` - Python dependencies
- `Dockerfile` - Container build file
- `docker-compose.yml` - Docker orchestration

### Directory Structure

```
ebay-sniper/
├── src/sniper/          # Source code
│   ├── core/           # Core logic
│   ├── web/            # Web server
│   └── *.py            # Entry points
├── tests/              # Tests
├── docs/               # This documentation
├── skill/              # Hermes skill
└── data/               # SQLite database (runtime)
```

### Important Notes

⚠️ **Bid Placement is Stubbed**
- Until eBay grants `buy.offer.auction` scope, bids are not actually placed
- Set `BID_PLACEMENT_STUBBED=true` in `.env.local`
- See [LIMITATIONS.md](LIMITATIONS.md#1-bid-placement-is-stubbed) for details

🔐 **Keep Secrets Safe**
- Never commit `.env.local`
- Use `.env.example` as template
- Rotate tokens regularly

⏰ **Timing Accuracy**
- NTP sync happens on startup
- Check status endpoint for clock offset
- Network latency can affect timing

### Getting Help

1. **Documentation**: Start with the relevant guide above
2. **Troubleshooting**: Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
3. **Status**: `curl http://localhost:8088/api/status`
4. **Logs**: `docker compose logs -f sniper`

### Current Status

- ✅ Search: Fully functional (eBay Browse API)
- ✅ Watch: Fully functional
- ✅ Monitor: Fully functional
- ✅ Notifications: Fully functional (Telegram)
- ⚠️ Bid Placement: Stubbed (pending eBay scope approval)

### Next Steps

After setting up the service:

1. Test search: `sniper search "nintendo switch"`
2. Add a test watch: `sniper watch 287456575036 --max-bid 50.00`
3. Monitor via dashboard: `http://localhost:8088/dashboard`
4. Configure Telegram for notifications (optional)
5. Explore the [MCP server](../README.md#mcp-server-hermes-integration)

## Documentation Quality

This documentation is designed to be:
- **Complete**: Covers all features and limitations
- **Actionable**: Includes working examples and commands
- **Honest**: Clearly states what works and what doesn't
- **Self-contained**: No dependence on internal chat context
- **Maintained**: Kept in sync with code changes

If you find documentation issues, please:
- Open a GitHub issue describing the problem
- Submit a PR with improvements
- Reference the specific section that needs updating

## Document Index

| Document | Purpose | Audience |
|----------|---------|----------|
| [README.md](../README.md) | Overview, quickstart | New users |
| [SETUP.md](../SETUP.md) | Installation, configuration | First-time setup |
| [INTERFACES.md](INTERFACES.md) | Interface usage | All users |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design | Developers |
| [LIMITATIONS.md](LIMITATIONS.md) | Known issues, trade-offs | Decision makers |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Problem solving | Operators |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Contribution guide | Contributors |
| [SPEC.md](../SPEC.md) | Build specification | Developers |