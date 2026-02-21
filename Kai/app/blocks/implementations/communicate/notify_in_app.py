from __future__ import annotations

import logging
from typing import Any

from app.blocks.executor import register_implementation
from app.database import get_db

logger = logging.getLogger("agentflow.blocks.notify")


@register_implementation("notify_in_app")
async def notify_in_app(inputs: dict[str, Any]) -> dict[str, Any]:
    """Show an in-app notification. Persists to DB and pushes to SSE subscribers."""
    title = inputs["title"]
    message = inputs["message"]
    level = inputs.get("level", "info")

    # Extract pipeline context if injected by graph_builder
    context = inputs.get("__context", {})
    pipeline_id = context.get("pipeline_id")

    log_fn = {
        "info": logger.info,
        "success": logger.info,
        "warning": logger.warning,
        "error": logger.error,
    }.get(level, logger.info)

    log_fn("[%s] %s: %s", level.upper(), title, message)

    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO notifications (pipeline_id, title, message, level, category)
               VALUES (?, ?, ?, ?, 'notification')""",
            (pipeline_id, title, message, level),
        )
        conn.commit()
        notification_id = cursor.lastrowid

    # Push to SSE notification bus (fire and forget)
    try:
        from app.api.sse import notification_bus
        await notification_bus.publish({
            "id": notification_id,
            "pipeline_id": pipeline_id,
            "title": title,
            "message": message,
            "level": level,
        })
    except Exception:
        logger.debug("SSE push failed for notification %s", notification_id, exc_info=True)

    return {"notification_id": notification_id, "delivered": True}
