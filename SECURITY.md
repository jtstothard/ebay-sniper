# Security Policy

## Supported Versions

Currently only the latest version is supported. There is no LTS version yet.

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately.

**Do NOT open a public issue.**

Instead, send an email to: jtstothard@gmail.com

Include the following information:
- Description of the vulnerability
- Steps to reproduce (if applicable)
- Affected versions
- Proposed fix (if known)

## What Happens Next

1. I will acknowledge receipt of your report within 48 hours
2. I will investigate and assess the severity
3. I will work on a fix and aim to release a patch within a reasonable timeframe
4. Once fixed, I will credit you in the release notes (with your permission)

## Security Best Practices for Users

When deploying eBay Sniper in production:

1. **Environment Variables**: Never commit `.env` or `.env.local` to version control
2. **Docker Security**: 
   - Keep the base image updated
   - Don't run containers as root (the Dockerfile already uses a non-root user)
   - Bind only necessary ports
3. **eBay Credentials**: 
   - Use eBay's sandbox environment for testing
   - Rotate API credentials if compromised
   - Monitor eBay's API usage for anomalies
4. **Network Security**:
   - Deploy behind a reverse proxy (nginx, Caddy) in production
   - Use HTTPS/TLS
   - Consider firewall rules to restrict access to the web dashboard
5. **Database**:
   - The SQLite file (`data/sniper.db`) may contain sensitive watch/bid information
   - Ensure appropriate file permissions on the host
   - Back up the database regularly

## Known Security Considerations

- **Bid Placement Stub**: Currently, bid placement is stubbed (see README). Once eBay grants the `buy.offer.auction` scope, the implementation should be audited for:
  - Proper authentication token handling
  - Rate limiting compliance
  - Idempotent bid placement
- **NTP Sync**: The service uses `pool.ntp.org` for time synchronization. Consider running a local NTP server for hardened deployments.
- **Token Storage**: OAuth tokens are stored in SQLite. In a multi-user scenario, this should be encrypted at rest. For self-hosted single-user deployments, this is acceptable given the threat model.

## Dependency Updates

This project depends on several Python packages. Keep dependencies updated:

```bash
pip list --outdated
pip install --upgrade <package-name>
```

Review security advisories for dependencies and upgrade promptly when vulnerabilities are disclosed.