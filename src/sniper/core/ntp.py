"""NTP clock synchronization for accurate snipe timing"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import ntplib

from ..config import config

logger = logging.getLogger(__name__)


class NTPSync:
    """NTP clock synchronization to ensure accurate snipe timing"""

    def __init__(self, ntp_server: Optional[str] = None):
        """Initialize NTPSync with optional custom NTP server"""
        self.ntp_server = ntp_server or config.NTP_SERVER
        self.offset: float = 0.0  # Clock offset in seconds
        self.synced: bool = False

    def sync(self) -> bool:
        """Synchronize with NTP server and calculate clock offset

        Returns:
            True if sync successful, False otherwise
        """
        try:
            client = ntplib.NTPClient()
            response = client.request(self.ntp_server, version=3)

            # Calculate offset (NTP time - local time)
            self.offset = response.offset
            self.synced = True

            logger.info(f"NTP sync successful: offset={self.offset:.6f}s")
            return True

        except Exception as e:
            logger.error(f"NTP sync failed: {e}")
            self.synced = False
            self.offset = 0.0
            return False

    def get_adjusted_time(self) -> datetime:
        """Get NTP-adjusted current time

        Returns:
            Current UTC time with NTP offset applied
        """
        local_time = time.time()
        ntp_time = local_time + self.offset
        return datetime.fromtimestamp(ntp_time, timezone.utc)

    def adjust_schedule_time(self, iso_timestamp: str) -> datetime:
        """Adjust a schedule time to local clock based on NTP offset

        If our clock is fast (offset > 0), we need to schedule later.
        If our clock is slow (offset < 0), we need to schedule earlier.

        Args:
            iso_timestamp: ISO 8601 timestamp in UTC

        Returns:
            Adjusted datetime for local scheduler
        """
        target_time = datetime.fromisoformat(iso_timestamp)
        # If our clock is fast by offset seconds, schedule offset seconds later
        adjusted_time = target_time + timedelta(seconds=self.offset)
        return adjusted_time
