"""Core watcher engine: fetch state, diff, propose actions, notify."""

from __future__ import annotations

import importlib
import logging
from typing import Any

from app.database import store as app_store
from app.services.whatsapp import WhatsAppClient
from watcher.llm_actions import propose_actions
from watcher.llm_diff import compare_snapshots
from watcher.store import store as watcher_store

log = logging.getLogger(__name__)


ALLOWED_INTEGRATIONS = {
    "google_calendar",
    "google_gmail",
    "google_drive",
    "google_contacts",
    "google_tasks",
}


def _load_integration(account_type: str):
    if account_type not in ALLOWED_INTEGRATIONS:
        raise ValueError(f"Unknown integration: {account_type}")
    module_name = f"watcher.integrations.{account_type}"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise RuntimeError(f"Integration module not found: {module_name}") from exc


def _notify_in_app(title: str, message: str, *, level: str = "info", metadata: dict | None = None) -> None:
    app_store.create_notification({
        "pipeline_id": None,
        "run_id": None,
        "node_id": None,
        "title": title,
        "message": message,
        "level": level,
        "category": "confirmation",
        "metadata": metadata or {},
        "read": False,
    })


def run_watch(task: dict) -> dict:
    config = task.get("config", {})
    account_type = config.get("account_type") or ""
    if not account_type:
        raise ValueError("Task config missing account_type")

    user_id = config.get("user_id") or "default"
    wa_id = config.get("wa_id") or ""

    integration = _load_integration(account_type)
    current_snapshot = integration.fetch_state(config)

    if not isinstance(current_snapshot, dict):
        raise ValueError("Integration fetch_state must return a dict")

    if current_snapshot.get("status") in {"disabled", "not_configured", "not_implemented"}:
        log.info("Integration %s disabled or not configured", account_type)
        return {"status": current_snapshot.get("status", "skipped")}

    previous_snapshot = watcher_store.get_latest_snapshot(user_id, account_type)
    watcher_store.save_snapshot(user_id, account_type, current_snapshot)

    if previous_snapshot is None:
        return {"status": "seeded", "changes": 0}

    changes = compare_snapshots(account_type, previous_snapshot, current_snapshot)
    if not changes:
        return {"status": "no_changes", "changes": 0}

    whatsapp = WhatsAppClient()
    actions_created = 0

    for change in changes:
        actions = propose_actions(account_type, change, current_snapshot)
        if not actions:
            continue

        for action in actions:
            action_title = str(action.get("title", "Proposed action")).strip() or "Proposed action"
            action_description = str(action.get("description", "")).strip()
            action_payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}

            action_id = watcher_store.create_action(
                user_id=user_id,
                account_type=account_type,
                change_summary=str(change.get("summary", "Change detected")),
                change_json=change,
                action_title=action_title,
                action_description=action_description,
                action_payload={
                    "action_type": action.get("action_type", ""),
                    "payload": action_payload,
                },
            )
            actions_created += 1

            prompt = (
                f"Change detected: {change.get('summary', 'Update')}\n"
                f"Proposed action: {action_title}\n"
                f"{action_description}\n\n"
                f"Reply 'approve {action_id}' or 'decline {action_id}'."
            )

            if wa_id:
                whatsapp.send_text(wa_id, prompt)

            _notify_in_app(
                title="Watcher action pending",
                message=prompt,
                metadata={
                    "action_id": action_id,
                    "account_type": account_type,
                    "change": change,
                },
            )

    return {"status": "changes_found", "changes": len(changes), "actions": actions_created}
