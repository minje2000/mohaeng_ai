from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import settings


class ChatLogService:
    def __init__(self) -> None:
        self.db_path = Path(settings.CHAT_LOG_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chat_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL DEFAULT (datetime('now')),
                        session_id TEXT,
                        client_key TEXT,
                        page_type TEXT,
                        intent TEXT,
                        status_code INTEGER,
                        latency_ms INTEGER,
                        message TEXT,
                        answer_preview TEXT,
                        card_count INTEGER NOT NULL DEFAULT 0,
                        source_count INTEGER NOT NULL DEFAULT 0,
                        rate_limited INTEGER NOT NULL DEFAULT 0,
                        metadata_json TEXT
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def log_event(
        self,
        *,
        session_id: str | None,
        client_key: str | None,
        page_type: str | None,
        intent: str | None,
        status_code: int,
        latency_ms: int,
        message: str,
        answer_preview: str | None,
        card_count: int = 0,
        source_count: int = 0,
        rate_limited: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        preview = (answer_preview or "").strip()[:400]
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO chat_logs (
                        session_id, client_key, page_type, intent, status_code, latency_ms,
                        message, answer_preview, card_count, source_count, rate_limited, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        client_key,
                        page_type,
                        intent,
                        status_code,
                        latency_ms,
                        (message or "")[:2000],
                        preview,
                        max(0, int(card_count or 0)),
                        max(0, int(source_count or 0)),
                        1 if rate_limited else 0,
                        metadata_json,
                    ),
                )
                conn.commit()
            finally:
                conn.close()


    def list_recent(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT id, created_at, session_id, client_key, page_type, intent, status_code, latency_ms,
                           message, answer_preview, card_count, source_count, rate_limited, metadata_json
                    FROM chat_logs
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (max(1, int(limit or 200)),),
                ).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

    def summarize(self) -> dict[str, Any]:
        with self._lock:
            conn = self._connect()
            try:
                total = conn.execute("SELECT COUNT(*) FROM chat_logs").fetchone()[0]
                errors = conn.execute("SELECT COUNT(*) FROM chat_logs WHERE status_code >= 400").fetchone()[0]
                rate_limited = conn.execute("SELECT COUNT(*) FROM chat_logs WHERE rate_limited = 1").fetchone()[0]
                avg_latency = conn.execute("SELECT COALESCE(AVG(latency_ms), 0) FROM chat_logs").fetchone()[0]
                top_intents = conn.execute("SELECT intent, COUNT(*) cnt FROM chat_logs GROUP BY intent ORDER BY cnt DESC LIMIT 10").fetchall()
                return {
                    'total': total,
                    'errors': errors,
                    'rateLimited': rate_limited,
                    'avgLatencyMs': int(avg_latency or 0),
                    'topIntents': [{'intent': row[0] or 'unknown', 'count': row[1]} for row in top_intents],
                }
            finally:
                conn.close()
