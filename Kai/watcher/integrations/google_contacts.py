"""Google Contacts integration (stub).

Expected snapshot shape (example):
{
  "status": "ok",
  "contacts": [
    {"id": "c_123", "name": "Ada", "email": "ada@example.com"}
  ]
}
"""

from __future__ import annotations


def fetch_state(config: dict) -> dict:
    credentials = config.get("credentials") or {}
    if not credentials:
        return {"status": "not_configured", "contacts": []}

    return {
        "status": "not_implemented",
        "contacts": [],
        "note": "Google Contacts fetch not wired yet.",
    }
