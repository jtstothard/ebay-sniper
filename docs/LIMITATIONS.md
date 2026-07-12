# Product Limitations

This document outlines the current limitations of eBay Sniper and future improvement plans.

## Current Limitations

### 1. Bid Placement is Stubbed

**Status**: Pending eBay API scope approval

**Details**:
- Bid placement is intentionally stubbed and does not place real bids
- The service logs stubbed bids and returns mock success
- This is due to eBay requiring manual approval for the `buy.offer.auction` OAuth scope

**Impact**:
- Search and watch functionality works fully
- Auction monitoring and notifications work fully
- No actual bids are placed on eBay
- All watch records show as "stubbed" in bid logs

**Path to Resolution**:
1. Request `buy.offer.auction` scope approval via [eBay Developer Portal](https://developer.ebay.com/)
2. Once approved, set `BID_PLACEMENT_STUBBED=false` in `.env.local`
3. The real Offer API call is already implemented in `src/sniper/core/ebay_client.py`
4. The stub code clearly logs when it's in use, so no confusion during testing

**Verification**:
```bash
curl http://localhost:8088/api/status | jq .bid_placement_stubbed
```

### 2. Single User Only

**Status**: No current multi-user support

**Details**:
- All watches are stored in a single SQLite database
- No user authentication or authorization
- No user-specific watch isolation
- Shared credentials for all operations

**Impact**:
- Only one person can use a deployment
- No per-user preferences or settings
- Cannot share a service among multiple users
- No audit trail of which user added which watch

**Path to Resolution**:
- Add user authentication (OAuth, JWT, etc.)
- Add `user_id` field to watches table
- Add user management endpoints
- Scope watches by user in queries
- Add user-specific notifications (multiple Telegram chat IDs)

### 3. Marketplace Limited to UK by Default

**Status**: Configurable but requires manual change

**Details**:
- Default marketplace is `EBAY_GB` (UK)
- Other marketplaces supported but require configuration change
- Currency handling assumes GBP by default

**Impact**:
- Default configuration only works for eBay UK
- Currency symbols hardcoded in some places (£ vs $ vs €)
- May need to restart service to change marketplace

**Path to Resolution**:
- Make marketplace per-watch configurable
- Auto-detect currency from eBay API response
- Add currency conversion support
- Allow multiple marketplaces in single deployment

### 4. Clock Accuracy Dependent on Network

**Status**: Best-effort NTP sync

**Details**:
- NTP sync happens once on startup
- No continuous clock correction
- Network latency can affect timing accuracy
- System clock drift not monitored after startup

**Impact**:
- Bid timing may be off by ±1 second in normal conditions
- Network issues can cause larger drift
- No alerts for clock synchronization problems
- May miss snipe window if clock is significantly off

**Path to Resolution**:
- Implement continuous NTP monitoring
- Add clock drift alerts in status endpoint
- Resync NTP periodically (e.g., every hour)
- Add bid retry logic with multiple attempts

### 5. No Bid History Persistence

**Status**: Basic bid log only

**Details**:
- `bid_log` table records events but not full bid details
- No historical bid amounts tracked
- Cannot see bid progression over time
- Limited audit trail

**Impact**:
- Cannot analyze bidding patterns
- Cannot reconstruct auction history
- Limited debugging information for failed bids
- No statistics on win/loss rates

**Path to Resolution**:
- Add `bid_history` table with full bid details
- Track all eBay API responses
- Add bid progression tracking
- Generate statistics and reports

### 6. Limited Error Recovery

**Status**: Basic retry logic only

**Details**:
- Only one retry attempt for failed bids
- No exponential backoff
- No circuit breaker for repeated failures
- Limited error categorization

**Impact**:
- Transient errors may cause missed opportunities
- Rate limiting not handled gracefully
- No protection against eBay API outages
- Limited visibility into failure patterns

**Path to Resolution**:
- Implement exponential backoff
- Add circuit breaker pattern
- Categorize errors (transient vs permanent)
- Add retry configuration per error type
- Add failure notifications and alerts

### 7. No Multi-Item Auction Support

**Status**: Single-item only

**Details**:
- Each watch is for one item ID
- No bulk watch operations
- No watch lists or saved searches
- No automated watch creation from search results

**Impact**:
- Must manually add each item
- Cannot "watch all results under £50"
- Cannot save common searches
- No bulk operations

**Path to Resolution**:
- Add bulk watch endpoints
- Add saved searches feature
- Add watch lists/folders
- Add automated watch creation rules
- Add watch import from search results

### 8. Limited Notification Channels

**Status**: Telegram only

**Details**:
- Notifications only via Telegram
- No email notifications
- No webhook support
- No in-app notifications

**Impact**:
- Must use Telegram for notifications
- No integration with other systems
- Cannot send notifications to multiple channels
- No notification history

**Path to Resolution**:
- Add email notifications (SMTP)
- Add webhook support
- Add in-app notification center
- Add notification preferences per channel
- Add notification history and replay

### 9. No Web UI Authentication

**Status**: No authentication

**Details**:
- Web dashboard has no authentication
- Anyone with network access can view watches
- No protection against unauthorized modifications
- Not suitable for public internet deployment

**Impact**:
- Must run behind reverse proxy with auth
- Cannot deploy publicly
- Security risk in untrusted networks
- No audit trail of web UI actions

**Path to Resolution**:
- Add basic auth or OAuth
- Add session management
- Add CSRF protection
- Add audit logging for UI actions
- Document reverse proxy setup (nginx, etc.)

### 10. Limited Search Features

**Status**: Basic search only

**Details**:
- No advanced filters (price range, condition, location)
- No saved searches
- No search history
- No search alerts

**Impact**:
- Limited search capabilities
- Cannot filter by condition (new vs used)
- Cannot set price ranges
- No automated alerts for new search results

**Path to Resolution**:
- Add advanced filters to search endpoint
- Add saved searches feature
- Add search history
- Add search alerts (auto-watch matching items)
- Add search result caching

## Intentional Design Choices

### SQLite Database
- **Choice**: SQLite over PostgreSQL/MySQL
- **Reasoning**: Simplicity, no external dependencies, easy backup
- **Trade-off**: Limited concurrency, not suitable for massive scale
- **Status**: Acceptable for personal use; would change for multi-user SaaS

### Docker-First Deployment
- **Choice**: Docker as primary deployment method
- **Reasoning**: Consistency, easy updates, isolation
- **Trade-off**: Requires Docker knowledge, larger resource footprint
- **Status**: Fits target audience (self-hosted power users)

### Single-Process Architecture
- **Choice**: All components in one process
- **Reasoning**: Simplicity, easier deployment, fewer moving parts
- **Trade-off**: Single point of failure, harder to scale
- **Status**: Acceptable for personal use; would redesign for high availability

### External NTP Dependency
- **Choice**: Use public NTP servers
- **Reasoning**: No local NTP server needed, works everywhere
- **Trade-off**: Network dependency, potential reliability issues
- **Status**: Acceptable for hobbyist use; would use local NTP for production

### eBay OAuth Client Credentials
- **Choice**: Client credentials flow for Browse API
- **Reasoning**: Simpler than user OAuth, no user interaction needed
- **Trade-off**: Limited scopes, no user-specific operations
- **Status**: Will add user OAuth when bid placement scope is approved

## Known Issues

### HTML Entity Escaping in Telegram
- **Status**: Fixed in recent commit
- **Issue**: Special characters in item titles could break Telegram HTML parsing
- **Resolution**: HTML entities now escaped in search output

### Price Mapping Inconsistency
- **Status**: Fixed in recent commit
- **Issue**: Auction items showed wrong price (listing price vs current bid)
- **Resolution**: Prefer `currentBidPrice` over `price.value` for auctions

### Telegram Polling Startup
- **Status**: Fixed in recent commit
- **Issue**: Manual event loop plumbing caused startup failures
- **Resolution**: Use python-telegram-bot's built-in `run_polling()`

## Future Improvements (Not Planned)

These are out of scope for the current project:

### Proxy Bidding Strategy
- **Not planned**: Automated bid escalation, counter-bidding strategies
- **Reason**: Adds complexity, may violate eBay terms, against simple sniping goal
- **Alternative**: Use `max_bid` parameter and let eBay handle proxy bidding

### Auction Analytics
- **Not planned**: Historical price analysis, market trends, win rate statistics
- **Reason**: Out of scope for sniping tool; use dedicated analytics tools
- **Alternative**: Export watch data and analyze separately

### Multi-Platform Support
- **Not planned**: Support for other auction sites (Amazon, etc.)
- **Reason**: eBay is the focus, adds complexity
- **Alternative**: Fork and adapt for other platforms

### Mobile App
- **Not planned**: Native iOS/Android app
- **Reason**: Web dashboard is sufficient, adds maintenance burden
- **Alternative**: Mobile-responsive web UI

## Scale Considerations

The current design targets:
- **Watches**: 0-1,000 active watches
- **Users**: 1 (single user)
- **Bids per day**: 0-100
- **Deployment**: Personal server or home lab

For larger scale (multi-tenant SaaS, thousands of users), would need:
- PostgreSQL or similar
- Distributed job scheduler (Celery, etc.)
- Microservice architecture
- Horizontal scaling
- Advanced monitoring and alerting

## Security Limitations

### Secret Management
- **Current**: Environment variables in `.env.local`
- **Limitation**: No secrets manager integration
- **Path to Resolution**: HashiCorp Vault, AWS Secrets Manager, etc.

### HTTPS/TLS
- **Current**: HTTP only
- **Limitation**: Must use reverse proxy for HTTPS
- **Path to Resolution**: Document nginx/caddy setup or embed TLS

### Audit Logging
- **Current**: Basic bid logging
- **Limitation**: No comprehensive audit trail
- **Path to Resolution**: Add structured audit logs, SIEM integration

## Summary

Most limitations are intentional trade-offs for simplicity and maintainability, with the primary blocker being eBay's `buy.offer.auction` scope approval. The service is designed for personal, self-hosted use with a focus on reliability and ease of deployment over enterprise features.

For questions about limitations or feature requests, please open a GitHub issue.