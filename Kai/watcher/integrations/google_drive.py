"""Google Drive integration (stub).

Expected snapshot shape (example):
{
  "status": "ok",
  "files": [
    {"id": "file_123", "name": "Doc", "mime_type": "...", "modified_time": "..."}
  ]
}
"""

from __future__ import annotations


def fetch_state(config: dict) -> dict:
    credentials = config.get("credentials") or {}
    if not credentials:
        return {"status": "not_configured", "files": []}

    return {
        "status": "not_implemented",
        "files": [],
        "note": "Google Drive fetch not wired yet.",
    }
