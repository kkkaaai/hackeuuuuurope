"""Handle approvals and execute proposed actions."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.database import store as app_store
from app.services.whatsapp import WhatsAppClient
from watcher.llm_utils import MODEL, get_client, has_api_key
from watcher.store import store as watcher_store

log = logging.getLogger(__name__)


def _notify(title: str, message: str, *, level: str = "info", metadata: dict | None = None) -> None:
    app_store.create_notification({
        "pipeline_id": None,
        "run_id": None,
        "node_id": None,
        "title": title,
        "message": message,
        "level": level,
        "category": "summary_card",
        "metadata": metadata or {},
        "read": False,
    })


def _execute_action(action: dict) -> str:
    if not has_api_key():
        return "Action approved, but no Anthropic API key is configured."

    client = get_client()

    action_payload = action.get("action_payload") or {}
    action_type = action_payload.get("action_type", "")
    payload = action_payload.get("payload", {})

    system_prompt = (
        "You are an assistant preparing a proactive deliverable for the user. "
        "Produce a concise, helpful response the user can act on immediately."
    )

    user_input = {
        "action_title": action.get("action_title"),
        "action_description": action.get("action_description"),
        "change_summary": action.get("change_summary"),
        "action_type": action_type,
        "payload": payload,
    }

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(user_input)}],
    )
    return message.content[0].text if message.content else ""


def approve_action(action_id: int, wa_id: str | None = None) -> str:
    action = watcher_store.get_action(action_id)
    if not action:
        return "Action not found."

    watcher_store.update_action_status(action_id, "approved")
    result_text = _execute_action(action)
    watcher_store.update_action_status(action_id, "completed")

    message = f"Action {action_id} completed.\n\n{result_text}".strip()
    _notify("Watcher action completed", message, metadata={"action_id": action_id})

    if wa_id:
        WhatsAppClient().send_text(wa_id, message)

    return message


def decline_action(action_id: int, wa_id: str | None = None) -> str:
    action = watcher_store.get_action(action_id)
    if not action:
        return "Action not found."

    watcher_store.update_action_status(action_id, "declined")
    message = f"Action {action_id} declined."
    _notify("Watcher action declined", message, metadata={"action_id": action_id})

    if wa_id:
        WhatsAppClient().send_text(wa_id, message)

    return message
