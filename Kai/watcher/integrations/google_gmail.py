"""Gmail integration (stub).

Expected snapshot shape (example):
{
  "status": "ok",
  "messages": [
    {"id": "msg_123", "subject": "Hello", "from": "a@b.com", "snippet": "..."}
  ]
}
"""

from __future__ import annotations


def fetch_state(config: dict) -> dict:
    credentials = config.get("credentials") or {}
    if not credentials:
        return {"status": "not_configured", "messages": []}

    return {
        "status": "not_implemented",
        "messages": [],
        "note": "Gmail fetch not wired yet.",
    }
