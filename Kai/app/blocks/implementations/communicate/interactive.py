from __future__ import annotations

import json
import logging
from typing import Any

from app.blocks.executor import register_implementation
from app.database import get_db

logger = logging.getLogger("agentflow.blocks.interactive")


@register_implementation("ask_user_confirm")
async def ask_user_confirm(inputs: dict[str, Any]) -> dict[str, Any]:
    """Pause pipeline and ask user for confirmation.

    Auto-confirms for now, but records the confirmation request as a
    notification so users can see it on the Activity dashboard.
    """
    question = inputs["question"]
    details = inputs.get("details", {})

    logger.info("User confirmation requested: %s (details: %s)", question, details)

    with get_db() as conn:
        conn.execute(
            """INSERT INTO notifications (title, message, level, category, metadata)
               VALUES (?, ?, 'warning', 'confirmation', ?)""",
            (
                "Confirmation Requested",
                question,
                json.dumps({"details": details, "auto_confirmed": True}),
            ),
        )
        conn.commit()

    return {
        "confirmed": True,
        "user_message": "Auto-confirmed (demo mode)",
    }


@register_implementation("present_summary_card")
async def present_summary_card(inputs: dict[str, Any]) -> dict[str, Any]:
    """Format data as a summary card for display. Persists to Activity dashboard."""
    title = inputs["title"]
    data = inputs["data"]
    highlight = inputs.get("highlight", "")

    if isinstance(data, str):
        fields = [{"label": "Summary", "value": data}]
    elif isinstance(data, dict):
        fields = [
            {"label": key.replace("_", " ").title(), "value": str(value)}
            for key, value in data.items()
        ]
    else:
        fields = [{"label": "Data", "value": str(data)}]

    card = {"title": title, "fields": fields, "highlight": highlight}

    with get_db() as conn:
        conn.execute(
            """INSERT INTO notifications (title, message, level, category, metadata)
               VALUES (?, ?, 'info', 'summary_card', ?)""",
            (
                title,
                highlight or "Summary card generated",
                json.dumps({"card": card}),
            ),
        )
        conn.commit()

    return {"card": card}
