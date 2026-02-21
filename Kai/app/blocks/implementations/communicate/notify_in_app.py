from __future__ import annotations

import logging
from typing import Any

from app.blocks.executor import register_implementation
from app.database import get_db

logger = logging.getLogger("agentflow.blocks.notify")


@register_implementation("notify_in_app")
async def notify_in_app(inputs: dict[str, Any]) -> dict[str, Any]:
    """Show an in-app notification. Persists to DB for the Activity dashboard."""
    title = inputs["title"]
    message = inputs["message"]
    level = inputs.get("level", "info")

    log_fn = {
        "info": logger.info,
        "success": logger.info,
        "warning": logger.warning,
        "error": logger.error,
    }.get(level, logger.info)

    log_fn("[%s] %s: %s", level.upper(), title, message)

    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO notifications (title, message, level, category)
               VALUES (?, ?, ?, 'notification')""",
            (title, message, level),
        )
        conn.commit()
        notification_id = cursor.lastrowid

    return {"notification_id": notification_id, "delivered": True}
