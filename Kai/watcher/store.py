"""SQLite helpers for watcher snapshots, task runs, and actions."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value)


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


@dataclass
class WatcherStore:
    path: str = settings.agentflow_db_path

    def __post_init__(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS watcher_task_runs (
                    task_id TEXT PRIMARY KEY,
                    last_run TEXT
                );

                CREATE TABLE IF NOT EXISTS watcher_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    account_type TEXT,
                    snapshot_json TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS watcher_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    account_type TEXT,
                    change_summary TEXT,
                    change_json TEXT,
                    action_title TEXT,
                    action_description TEXT,
                    action_payload_json TEXT,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );
                """
            )

    def get_last_run(self, task_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT last_run FROM watcher_task_runs WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        return row["last_run"] if row else None

    def set_last_run(self, task_id: str, timestamp: str | None = None) -> None:
        last_run = timestamp or _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO watcher_task_runs (task_id, last_run)
                VALUES (?, ?)
                ON CONFLICT(task_id) DO UPDATE SET last_run = excluded.last_run
                """,
                (task_id, last_run),
            )

    def get_latest_snapshot(self, user_id: str, account_type: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT snapshot_json FROM watcher_snapshots
                WHERE user_id = ? AND account_type = ?
                ORDER BY id DESC LIMIT 1
                """,
                (user_id, account_type),
            ).fetchone()
        if not row:
            return None
        return _json_loads(row["snapshot_json"], None)

    def save_snapshot(self, user_id: str, account_type: str, snapshot: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO watcher_snapshots (user_id, account_type, snapshot_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, account_type, _json_dumps(snapshot), _utc_now()),
            )

    def create_action(
        self,
        *,
        user_id: str,
        account_type: str,
        change_summary: str,
        change_json: dict,
        action_title: str,
        action_description: str,
        action_payload: dict,
        status: str = "pending",
    ) -> int:
        now = _utc_now()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO watcher_actions (
                    user_id, account_type, change_summary, change_json, action_title,
                    action_description, action_payload_json, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    account_type,
                    change_summary,
                    _json_dumps(change_json),
                    action_title,
                    action_description,
                    _json_dumps(action_payload),
                    status,
                    now,
                    now,
                ),
            )
            return int(cur.lastrowid)

    def get_action(self, action_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM watcher_actions WHERE id = ?",
                (action_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "account_type": row["account_type"],
            "change_summary": row["change_summary"],
            "change": _json_loads(row["change_json"], {}),
            "action_title": row["action_title"],
            "action_description": row["action_description"],
            "action_payload": _json_loads(row["action_payload_json"], {}),
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def update_action_status(self, action_id: int, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE watcher_actions
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, _utc_now(), action_id),
            )

    def list_pending_actions(self, user_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM watcher_actions
                WHERE user_id = ? AND status = 'pending'
                ORDER BY id ASC
                """,
                (user_id,),
            ).fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "user_id": row["user_id"],
                "account_type": row["account_type"],
                "change_summary": row["change_summary"],
                "action_title": row["action_title"],
                "action_description": row["action_description"],
                "action_payload": _json_loads(row["action_payload_json"], {}),
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })
        return result


store = WatcherStore()
