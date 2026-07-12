"""Configuration management for eBay Sniper Service"""

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Load environment variables from .env.local if it exists
env_path = Path(__file__).parent.parent.parent / ".env.local"
if env_path.exists():
    load_dotenv(env_path)


def _default_db_path() -> str:
    """Pick a writable default database location."""
    repo_db = Path(__file__).parent.parent.parent / "data" / "sniper.db"
    data_dir = Path("/data")

    if data_dir.exists() and os.access(data_dir, os.W_OK | os.X_OK):
        return str(data_dir / "sniper.db")

    return str(repo_db)


def _resolve_db_path() -> str:
    """Use DB_PATH if it is writable; otherwise fall back to a local path."""
    env_db_path = os.getenv("DB_PATH")
    if env_db_path:
        candidate = Path(env_db_path)
        candidate_parent = candidate.parent
        if candidate_parent.exists() and os.access(candidate_parent, os.W_OK | os.X_OK):
            return env_db_path

    return _default_db_path()


class Config:
    """Application configuration loaded from environment variables"""

    # eBay API credentials
    EBAY_APP_ID: str = os.getenv("EBAY_APP_ID", "")
    EBAY_CERT_ID: str = os.getenv("EBAY_CERT_ID", "")
    EBAY_DEV_ID: str = os.getenv("EBAY_DEV_ID", "")
    EBAY_ENVIRONMENT: Literal["production", "sandbox"] = os.getenv(
        "EBAY_ENVIRONMENT", "production"
    )
    EBAY_MARKETPLACE: str = os.getenv("EBAY_MARKETPLACE", "EBAY_GB")

    # Sandbox credentials (optional)
    EBAY_SANDBOX_APP_ID: str = os.getenv("EBAY_SANDBOX_APP_ID", "")
    EBAY_SANDBOX_CERT_ID: str = os.getenv("EBAY_SANDBOX_CERT_ID", "")

    # Telegram bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Web server
    WEB_PORT: int = int(os.getenv("WEB_PORT", "8088"))
    WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")

    # Database — default to local data dir; /data is the container path
    DB_PATH: str = _resolve_db_path()

    # Sniping configuration
    BID_OFFSET_SECONDS: int = int(
        os.getenv("BID_OFFSET_SECONDS", os.getenv("SNIPER_BID_OFFSET_SECONDS", "8"))
    )
    BID_RETRY_OFFSET_SECONDS: int = int(
        os.getenv(
            "BID_RETRY_OFFSET_SECONDS", os.getenv("SNIPER_RETRY_OFFSET_SECONDS", "3")
        )
    )
    RESULT_CHECK_DELAY_SECONDS: int = int(os.getenv("RESULT_CHECK_DELAY_SECONDS", "30"))

    # NTP server for clock sync
    NTP_SERVER: str = os.getenv("NTP_SERVER", "pool.ntp.org")

    # Bid placement stub (until eBay grants buy.offer.auction scope)
    BID_PLACEMENT_STUBBED: bool = os.getenv("BID_PLACEMENT_STUBBED", "true").lower() in (
        "true",
        "1",
    )

    @property
    def ebay_base_url(self) -> str:
        """Get eBay API base URL based on environment"""
        if self.EBAY_ENVIRONMENT == "sandbox":
            return "https://api.sandbox.ebay.com"
        return "https://api.ebay.com"

    @property
    def ebay_oauth_url(self) -> str:
        """Get eBay OAuth token endpoint based on environment"""
        if self.EBAY_ENVIRONMENT == "sandbox":
            return "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
        return "https://api.ebay.com/identity/v1/oauth2/token"

    @property
    def ebay_app_id(self) -> str:
        """Get App ID for current environment"""
        if self.EBAY_ENVIRONMENT == "sandbox" and self.EBAY_SANDBOX_APP_ID:
            return self.EBAY_SANDBOX_APP_ID
        return self.EBAY_APP_ID

    @property
    def ebay_cert_id(self) -> str:
        """Get Cert ID for current environment"""
        if self.EBAY_ENVIRONMENT == "sandbox" and self.EBAY_SANDBOX_CERT_ID:
            return self.EBAY_SANDBOX_CERT_ID
        return self.EBAY_CERT_ID

    def validate(self) -> bool:
        """Validate required configuration"""
        if not self.EBAY_APP_ID:
            raise ValueError("EBAY_APP_ID is required")
        if not self.EBAY_CERT_ID:
            raise ValueError("EBAY_CERT_ID is required")
        if not self.EBAY_DEV_ID:
            raise ValueError("EBAY_DEV_ID is required")
        return True


config = Config()