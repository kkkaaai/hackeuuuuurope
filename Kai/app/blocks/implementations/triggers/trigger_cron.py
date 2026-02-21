from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.blocks.executor import register_implementation


@register_implementation("trigger_cron")
async def trigger_cron(inputs: dict[str, Any]) -> dict[str, Any]:
    """Cron trigger — in real usage APScheduler fires this.

    When executed directly, it returns the current time as the trigger event.
    The actual scheduling is handled by the engine's Scheduler class.
    """
    return {
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "schedule": inputs.get("schedule", ""),
        "timezone": inputs.get("timezone", "UTC"),
    }
