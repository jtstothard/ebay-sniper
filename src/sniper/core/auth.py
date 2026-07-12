"""OAuth token management for eBay APIs"""

import base64
import json
import time
from datetime import datetime, timedelta, timezone

import httpx

from ..config import config
from .db import WatchStore


class AuthManager:
    """Manages eBay OAuth tokens for Browse and Offer APIs"""

    def __init__(self, db: WatchStore):
        """Initialize AuthManager with WatchStore for token persistence"""
        self.db = db

    def _encode_credentials(self) -> str:
        """Encode app credentials for basic auth"""
        creds = f"{config.ebay_app_id}:{config.ebay_cert_id}"
        return base64.b64encode(creds.encode()).decode()

    async def get_app_token(self, force_refresh: bool = False) -> str:
        """Get application token (client-credentials flow) for Browse API

        Uses client-credentials grant type. Token is cached in SQLite and
        auto-refreshed if expired.
        """
        # Check existing token
        existing = self.db.get_token("application", config.EBAY_ENVIRONMENT)
        if existing and not force_refresh:
            if existing["expires_at"]:
                expires_at = datetime.fromisoformat(existing["expires_at"])
                if expires_at > datetime.now(timezone.utc) + timedelta(minutes=5):
                    return existing["access_token"]

        # Fetch new token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                config.ebay_oauth_url,
                headers={
                    "Authorization": f"Basic {self._encode_credentials()}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data="grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope",
            )
            response.raise_for_status()
            token_data = response.json()

        # Calculate expiry (subtract 5 min buffer)
        expires_in = token_data.get("expires_in", 7200)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 300)

        # Store token
        self.db.store_token(
            token_type="application",
            environment=config.EBAY_ENVIRONMENT,
            access_token=token_data["access_token"],
            refresh_token=None,
            expires_at=expires_at.isoformat(),
            scope=token_data.get("scope", ""),
        )

        return token_data["access_token"]

    async def get_user_token(self, force_refresh: bool = False) -> str:
        """Get user token for Offer API (bid placement)

        Note: This is currently stubbed. When eBay grants buy.offer.auction
        scope, implement auth-code flow to get user token with refresh token.
        """
        # For now, use app token as fallback (works for Browse API only)
        # This will need to be replaced with proper user token flow
        return await self.get_app_token(force_refresh=force_refresh)

    async def refresh_user_token(self, refresh_token: str) -> str:
        """Refresh user token using refresh token

        Note: Currently stubbed. Implement when scope is granted.
        """
        # TODO: Implement refresh token flow when scope is granted
        raise NotImplementedError(
            "User token refresh not implemented - buy.offer.auction scope not granted yet"
        )
