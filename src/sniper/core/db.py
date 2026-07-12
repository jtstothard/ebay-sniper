"""SQLite database schema and WatchStore implementation"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..config import config


class WatchStore:
    """SQLite-based storage for watches, tokens, and bid logs"""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize WatchStore with database path"""
        self.db_path = db_path or config.DB_PATH
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self):
        """Ensure database directory exists"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS watches (
                    id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    legacy_item_id TEXT,
                    title TEXT,
                    auction_end_time TEXT NOT NULL,
                    max_bid REAL NOT NULL,
                    currency TEXT DEFAULT 'GBP',
                    status TEXT DEFAULT 'active',
                    bid_placed INTEGER DEFAULT 0,
                    bid_amount REAL,
                    winning INTEGER,
                    final_price REAL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    notes TEXT,
                    source TEXT DEFAULT 'manual'
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tokens (
                    id INTEGER PRIMARY KEY,
                    token_type TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    access_token TEXT,
                    refresh_token TEXT,
                    expires_at TEXT,
                    scope TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bid_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    watch_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    event TEXT NOT NULL,
                    details TEXT,
                    FOREIGN KEY (watch_id) REFERENCES watches(id)
                )
            """
            )

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_watches_status ON watches(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_watches_item_id ON watches(item_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_bid_log_watch_id ON bid_log(watch_id)"
            )

    def add_watch(
        self,
        item_id: str,
        legacy_item_id: Optional[str],
        title: str,
        auction_end_time: str,
        max_bid: float,
        currency: str = "GBP",
        source: str = "manual",
        notes: Optional[str] = None,
    ) -> str:
        """Add a new watch to the database"""
        watch_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO watches (
                    id, item_id, legacy_item_id, title, auction_end_time,
                    max_bid, currency, status, created_at, source, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    watch_id,
                    item_id,
                    legacy_item_id,
                    title,
                    auction_end_time,
                    max_bid,
                    currency,
                    "active",
                    now,
                    source,
                    notes,
                ),
            )
            conn.commit()

        return watch_id

    def get_watch(self, watch_id: str) -> Optional[dict]:
        """Get a watch by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM watches WHERE id = ?", (watch_id,)
            )
            row = cur.fetchone()
            if row:
                return dict(row)
            return None

    def get_watch_by_item_id(self, item_id: str) -> Optional[dict]:
        """Get a watch by eBay item ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM watches WHERE item_id = ? AND status = 'active'",
                (item_id,),
            )
            row = cur.fetchone()
            if row:
                return dict(row)
            return None

    def list_watches(self, status: Optional[str] = None) -> list[dict]:
        """List all watches, optionally filtered by status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if status:
                cur = conn.execute(
                    "SELECT * FROM watches WHERE status = ? ORDER BY auction_end_time ASC",
                    (status,),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM watches ORDER BY auction_end_time ASC"
                )
            return [dict(row) for row in cur.fetchall()]

    def update_watch_status(self, watch_id: str, status: str) -> bool:
        """Update watch status"""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE watches SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, watch_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def update_watch_bid(
        self, watch_id: str, bid_placed: int, bid_amount: Optional[float] = None
    ) -> bool:
        """Update watch bid information"""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                UPDATE watches SET bid_placed = ?, bid_amount = ?, updated_at = ?
                WHERE id = ?
            """,
                (bid_placed, bid_amount, now, watch_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def update_watch_result(
        self,
        watch_id: str,
        winning: Optional[int],
        final_price: Optional[float] = None,
    ) -> bool:
        """Update watch auction result"""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                UPDATE watches SET winning = ?, final_price = ?, updated_at = ?
                WHERE id = ?
            """,
                (winning, final_price, now, watch_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def log_event(self, watch_id: str, event: str, details: Optional[dict] = None):
        """Log an event to bid_log"""
        timestamp = datetime.now(timezone.utc).isoformat()
        details_json = json.dumps(details) if details else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO bid_log (watch_id, timestamp, event, details)
                VALUES (?, ?, ?, ?)
            """,
                (watch_id, timestamp, event, details_json),
            )
            conn.commit()

    def get_bid_log(self, watch_id: str) -> list[dict]:
        """Get all bid log entries for a watch"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM bid_log WHERE watch_id = ? ORDER BY timestamp ASC",
                (watch_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_active_watches_due_before(
        self, timestamp: str
    ) -> list[dict]:
        """Get active watches that are due before a timestamp (for scheduler)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """
                SELECT * FROM watches
                WHERE status = 'active' AND auction_end_time <= ?
                ORDER BY auction_end_time ASC
            """,
                (timestamp,),
            )
            return [dict(row) for row in cur.fetchall()]

    def store_token(
        self,
        token_type: str,
        environment: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[str] = None,
        scope: Optional[str] = None,
    ):
        """Store or update OAuth token"""
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # Check if token exists
            cur = conn.execute(
                """
                SELECT id FROM tokens
                WHERE token_type = ? AND environment = ?
            """,
                (token_type, environment),
            )
            existing = cur.fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE tokens SET
                        access_token = ?, refresh_token = ?,
                        expires_at = ?, scope = ?, updated_at = ?
                    WHERE token_type = ? AND environment = ?
                """,
                    (
                        access_token,
                        refresh_token,
                        expires_at,
                        scope,
                        now,
                        token_type,
                        environment,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO tokens (
                        token_type, environment, access_token, refresh_token,
                        expires_at, scope, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        token_type,
                        environment,
                        access_token,
                        refresh_token,
                        expires_at,
                        scope,
                        now,
                        now,
                    ),
                )
            conn.commit()

    def get_token(
        self, token_type: str, environment: str
    ) -> Optional[dict]:
        """Get stored OAuth token"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """
                SELECT * FROM tokens
                WHERE token_type = ? AND environment = ?
            """,
                (token_type, environment),
            )
            row = cur.fetchone()
            if row:
                return dict(row)
            return None