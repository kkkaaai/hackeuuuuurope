import sqlite3
from contextlib import contextmanager
from pathlib import Path

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

            CREATE INDEX IF NOT EXISTS idx_execution_logs_pipeline
                ON execution_logs(pipeline_id, finished_at DESC);

            CREATE INDEX IF NOT EXISTS idx_notifications_created
                ON notifications(created_at DESC);
        """)
        conn.commit()
