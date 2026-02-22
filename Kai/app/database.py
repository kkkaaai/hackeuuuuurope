import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent.parent / "agentflow.db"


@contextmanager
def get_db():
    """Yield a SQLite connection; automatically closed on exit."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS memory (
                namespace TEXT NOT NULL,
                key       TEXT NOT NULL,
                value     TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (namespace, key)
            );

            CREATE TABLE IF NOT EXISTS pipelines (
                id          TEXT PRIMARY KEY,
                user_intent TEXT NOT NULL,
                definition  TEXT NOT NULL,
                status      TEXT DEFAULT 'created',
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS execution_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_id TEXT NOT NULL,
                run_id      TEXT NOT NULL,
                node_id     TEXT,
                status      TEXT,
                input_data  TEXT,
                output_data TEXT,
                error       TEXT,
                started_at  TEXT DEFAULT (datetime('now')),
                finished_at TEXT,
                FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_id TEXT,
                run_id      TEXT,
                node_id     TEXT,
                title       TEXT NOT NULL,
                message     TEXT NOT NULL,
                level       TEXT DEFAULT 'info',
                category    TEXT DEFAULT 'notification',
                metadata    TEXT DEFAULT '{}',
                read        INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                id          TEXT PRIMARY KEY,
                history     TEXT DEFAULT '[]',
                status      TEXT DEFAULT 'active',
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS whatsapp_users (
                wa_id             TEXT PRIMARY KEY,
                phone_display     TEXT DEFAULT '',
                default_pipeline_id TEXT,
                last_seen         TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS whatsapp_sessions (
                wa_id          TEXT PRIMARY KEY,
                session_id     TEXT NOT NULL,
                pending_kind   TEXT,
                pending_intent TEXT,
                updated_at     TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_execution_logs_pipeline
                ON execution_logs(pipeline_id, finished_at DESC);

            CREATE INDEX IF NOT EXISTS idx_notifications_created
                ON notifications(created_at DESC);
        """)
        conn.commit()


class DataStore:
    """Thin convenience wrapper around get_db() for the ported WhatsApp/watcher code."""

    # ── Notifications ──────────────────────────────────────────────

    def create_notification(self, data: dict[str, Any]) -> int:
        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO notifications
                   (pipeline_id, run_id, node_id, title, message, level, category, metadata, read)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data.get("pipeline_id"),
                    data.get("run_id"),
                    data.get("node_id"),
                    data["title"],
                    data["message"],
                    data.get("level", "info"),
                    data.get("category", "notification"),
                    json.dumps(data.get("metadata", {})),
                    int(data.get("read", False)),
                ),
            )
            conn.commit()
            return cur.lastrowid  # type: ignore[return-value]

    # ── WhatsApp users ─────────────────────────────────────────────

    def upsert_whatsapp_user(
        self, wa_id: str, *, phone_display: str = "", last_seen: str = ""
    ) -> None:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO whatsapp_users (wa_id, phone_display, last_seen)
                   VALUES (?, ?, ?)
                   ON CONFLICT(wa_id) DO UPDATE SET
                       phone_display = COALESCE(NULLIF(excluded.phone_display, ''), phone_display),
                       last_seen = excluded.last_seen""",
                (wa_id, phone_display, last_seen),
            )
            conn.commit()

    def get_whatsapp_user(self, wa_id: str) -> dict[str, Any] | None:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM whatsapp_users WHERE wa_id = ?", (wa_id,)
            ).fetchone()
        if not row:
            return None
        return dict(row)

    def set_whatsapp_default_pipeline(self, wa_id: str, pipeline_id: str) -> None:
        with get_db() as conn:
            conn.execute(
                "UPDATE whatsapp_users SET default_pipeline_id = ? WHERE wa_id = ?",
                (pipeline_id, wa_id),
            )
            conn.commit()

    # ── WhatsApp sessions ──────────────────────────────────────────

    def get_whatsapp_session(self, wa_id: str) -> dict[str, Any] | None:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM whatsapp_sessions WHERE wa_id = ?", (wa_id,)
            ).fetchone()
        if not row:
            return None
        return dict(row)

    def set_whatsapp_session(
        self,
        wa_id: str,
        session_id: str,
        *,
        pending_kind: str | None = None,
        pending_intent: str | None = None,
    ) -> None:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO whatsapp_sessions (wa_id, session_id, pending_kind, pending_intent, updated_at)
                   VALUES (?, ?, ?, ?, datetime('now'))
                   ON CONFLICT(wa_id) DO UPDATE SET
                       session_id = excluded.session_id,
                       pending_kind = excluded.pending_kind,
                       pending_intent = excluded.pending_intent,
                       updated_at = excluded.updated_at""",
                (wa_id, session_id, pending_kind, pending_intent),
            )
            conn.commit()

    # ── Pipelines ──────────────────────────────────────────────────

    def save_pipeline(self, pipeline_id: str, definition: dict[str, Any]) -> None:
        user_intent = definition.get("user_intent", "")
        status = definition.get("status", "created")
        # Store definition without user_intent (it has its own column)
        stored = {k: v for k, v in definition.items() if k != "user_intent"}
        with get_db() as conn:
            conn.execute(
                """INSERT INTO pipelines (id, user_intent, definition, status)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       definition = excluded.definition,
                       updated_at = datetime('now')""",
                (pipeline_id, user_intent, json.dumps(stored), status),
            )
            conn.commit()

    def get_pipeline(self, pipeline_id: str) -> dict[str, Any] | None:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM pipelines WHERE id = ?", (pipeline_id,)
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["definition"] = json.loads(result.get("definition", "{}"))
        return result

    # ── Chat sessions ──────────────────────────────────────────────

    def get_chat_session(self, session_id: str) -> list[dict[str, str]]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT history FROM chat_sessions WHERE id = ?", (session_id,)
            ).fetchone()
        if not row:
            return []
        return json.loads(row["history"])

    def set_chat_session(self, session_id: str, history: list[dict[str, str]]) -> None:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO chat_sessions (id, history, updated_at)
                   VALUES (?, ?, datetime('now'))
                   ON CONFLICT(id) DO UPDATE SET
                       history = excluded.history,
                       updated_at = excluded.updated_at""",
                (session_id, json.dumps(history)),
            )
            conn.commit()


store = DataStore()
