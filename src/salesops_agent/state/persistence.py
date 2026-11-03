from pathlib import Path
from typing import Any, Dict, List, Optional
import sqlite3
import json
from datetime import datetime, timezone

DB_PATH = Path("data/state_store.db")

class StatePersistence:
    """Provides SQLite persistence for user, session, thread, and run history with strict memory isolation."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_state (
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, session_id, thread_id, key)
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS run_history (
                run_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                user_input TEXT NOT NULL,
                final_output TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """)
            conn.commit()

    def set_memory(self, user_id: str, session_id: str, thread_id: str, key: str, value: Any) -> None:
        """Stores a memory key-value pair strictly scoped to user_id, session_id, thread_id."""
        val_str = json.dumps(value)
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO conversation_state (user_id, session_id, thread_id, key, value, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, session_id, thread_id, key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """, (user_id, session_id, thread_id, key, val_str, now))
            conn.commit()

    def get_memory(self, user_id: str, session_id: str, thread_id: str, key: str) -> Optional[Any]:
        """Retrieves a memory item. Enforces memory isolation across users."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
            SELECT value FROM conversation_state
            WHERE user_id = ? AND session_id = ? AND thread_id = ? AND key = ?
            """, (user_id, session_id, thread_id, key))
            row = cursor.fetchone()
            if row:
                return json.loads(row["value"])
            return None

    def record_run(
        self,
        run_id: str,
        user_id: str,
        session_id: str,
        thread_id: str,
        user_input: str,
        final_output: str,
        status: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO run_history (run_id, user_id, session_id, thread_id, user_input, final_output, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (run_id, user_id, session_id, thread_id, user_input, final_output, status, now))
            conn.commit()

    def get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetch history for a specific user only, isolating other users."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
            SELECT * FROM run_history WHERE user_id = ? ORDER BY created_at DESC
            """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]
