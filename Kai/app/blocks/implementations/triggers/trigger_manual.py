from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.blocks.executor import register_implementation


@register_implementation("trigger_manual")
async def trigger_manual(inputs: dict[str, Any]) -> dict[str, Any]:
    """Start a pipeline immediately with optional user input."""
    return {
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "user_input": inputs.get("user_input", ""),
    }
