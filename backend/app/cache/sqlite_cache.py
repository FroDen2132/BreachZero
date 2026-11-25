"""SQLite-backed IOC cache to shield live events from external API rate limits."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from app.models.contracts import EvidenceCard


class SqliteIocCache:
    """Thread-safe lightweight SQLite cache with configurable TTL."""

    def __init__(self, db_path: Path, ttl_seconds: int = 7 * 86400) -> None:
        self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        self.init_db()

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ioc_cache (
                    cache_key TEXT PRIMARY KEY,
                    card_json TEXT NOT NULL,
                    expires_at INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    @staticmethod
    def _make_key(enricher_id: str, ioc_type: str, ioc_value: str) -> str:
        return f"{enricher_id}:{ioc_type}:{ioc_value.strip().lower()}"

    def get(self, enricher_id: str, ioc_type: str, ioc_value: str) -> Optional[EvidenceCard]:
        key = self._make_key(enricher_id, ioc_type, ioc_value)
        now = int(time.time())
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT card_json, expires_at FROM ioc_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()
            if not row:
                return None
            card_json, expires_at = row
            if expires_at < now:
                conn.execute("DELETE FROM ioc_cache WHERE cache_key = ?", (key,))
                conn.commit()
                return None
            return EvidenceCard.model_validate_json(card_json)

    def set(self, enricher_id: str, ioc_type: str, ioc_value: str, card: EvidenceCard) -> None:
        key = self._make_key(enricher_id, ioc_type, ioc_value)
        expires_at = int(time.time()) + self.ttl_seconds
        payload = json.dumps(card.model_dump(), ensure_ascii=False)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO ioc_cache (cache_key, card_json, expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    card_json = excluded.card_json,
                    expires_at = excluded.expires_at
                """,
                (key, payload, expires_at),
            )
            conn.commit()
