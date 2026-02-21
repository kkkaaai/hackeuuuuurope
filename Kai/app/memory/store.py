from __future__ import annotations

import json
import logging
from typing import Any

from app.database import get_db

logger = logging.getLogger("agentflow.memory")


class MemoryStore:
    """SQLite-backed key-value store with namespaces."""

    def read(self, key: str, namespace: str = "default") -> Any | None:
        with get_db() as conn:
            row = conn.execute(
                "SELECT value FROM memory WHERE namespace = ? AND key = ?",
                (namespace, key),
            ).fetchone()
            if row is None:
                return None
            return json.loads(row["value"])

    def write(self, key: str, value: Any, namespace: str = "default") -> None:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO memory (namespace, key, value, updated_at)
                   VALUES (?, ?, ?, datetime('now'))
                   ON CONFLICT(namespace, key)
                   DO UPDATE SET value = excluded.value, updated_at = datetime('now')""",
                (namespace, key, json.dumps(value)),
            )
            conn.commit()

    def append(self, key: str, value: Any, namespace: str = "default") -> int:
        """Append to a list stored at key. Creates the list if it doesn't exist."""
        existing = self.read(key, namespace)
        if existing is None:
            existing = []
        if not isinstance(existing, list):
            existing = [existing]
        existing.append(value)
        self.write(key, existing, namespace)
        return len(existing)

    def delete(self, key: str, namespace: str = "default") -> bool:
        with get_db() as conn:
            cursor = conn.execute(
                "DELETE FROM memory WHERE namespace = ? AND key = ?",
                (namespace, key),
            )
            conn.commit()
            return cursor.rowcount > 0

    def list_keys(self, namespace: str = "default") -> list[str]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT key FROM memory WHERE namespace = ?", (namespace,)
            ).fetchall()
            return [row["key"] for row in rows]

    def clear_namespace(self, namespace: str = "default") -> int:
        with get_db() as conn:
            cursor = conn.execute(
                "DELETE FROM memory WHERE namespace = ?", (namespace,)
            )
            conn.commit()
            return cursor.rowcount


# Global singleton
memory_store = MemoryStore()
