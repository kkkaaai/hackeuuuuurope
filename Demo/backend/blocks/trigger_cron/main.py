"""Trigger cron block — returns trigger metadata (skipped by executor)."""

from datetime import datetime, timezone


async def execute(inputs: dict, context: dict) -> dict:
    return {"triggered_at": datetime.now(timezone.utc).isoformat()}
