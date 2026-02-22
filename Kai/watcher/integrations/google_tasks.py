"""Google Tasks integration (stub).

Expected snapshot shape (example):
{
  "status": "ok",
  "tasks": [
    {"id": "t_123", "title": "Follow up", "due": "..."}
  ]
}
"""

from __future__ import annotations


def fetch_state(config: dict) -> dict:
    credentials = config.get("credentials") or {}
    if not credentials:
        return {"status": "not_configured", "tasks": []}

    return {
        "status": "not_implemented",
        "tasks": [],
        "note": "Google Tasks fetch not wired yet.",
    }
