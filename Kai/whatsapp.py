"""WhatsApp webhook + command handling."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable

from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.database import store
from app.models import PipelineEdge, PipelineNode, RunPipelineRequest, TriggerConfig
from app.openai_client import plan_pipeline
from app.routes.pipelines import run_pipeline
from app.services.whatsapp import IncomingMessage, WhatsAppClient, parse_incoming_messages
from watcher.action_runner import approve_action, decline_action

log = logging.getLogger(__name__)
router = APIRouter()
whatsapp = WhatsAppClient()


@dataclass(frozen=True)
class Command:
    name: str
    usage: str
    description: str
    handler: Callable[[str, str, str, str | None], Awaitable[None]]


COMMANDS: dict[str, Command] = {}


def _register_command(command: Command) -> None:
    COMMANDS[command.name] = command


@router.get("/api/whatsapp/webhook")
def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        return int(challenge) if challenge and challenge.isdigit() else (challenge or "")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/api/whatsapp/webhook")
async def receive_webhook(request: Request):
    body = await request.body()

    if settings.WHATSAPP_APP_SECRET:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not _verify_signature(body, signature, settings.WHATSAPP_APP_SECRET):
            raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = json.loads(body.decode("utf-8")) if body else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    messages = parse_incoming_messages(payload)
    for msg in messages:
        asyncio.create_task(_handle_message(msg))
    return {"ok": True}


async def _handle_message(msg: IncomingMessage) -> None:
    try:
        if not msg.wa_id:
            return

        phone_number_id = msg.phone_number_id
        if not msg.text:
            whatsapp.send_text(
                msg.wa_id,
                "Unsupported message type. Send text to use flows.",
                phone_number_id=phone_number_id,
            )
            return

        text = msg.text.strip()
        if not text:
            return

        decision = _parse_action_decision(text)
        if decision:
            action_id, approved = decision
            if approved:
                approve_action(action_id, msg.wa_id)
            else:
                decline_action(action_id, msg.wa_id)
            return

        now = datetime.now(timezone.utc).isoformat()
        store.upsert_whatsapp_user(
            msg.wa_id,
            phone_display=msg.contact_name,
            last_seen=now,
        )

        session = store.get_whatsapp_session(msg.wa_id)
        session_id = session.get("session_id") if session else str(uuid.uuid4())
        if not session:
            store.set_whatsapp_session(msg.wa_id, session_id)

        pending_kind = session.get("pending_kind") if session else None
        pending_intent = session.get("pending_intent") if session else None

        command_name, command_args = _parse_command(text)

        if pending_kind == "clarification" and not command_name:
            await _handle_clarification(msg.wa_id, session_id, text, phone_number_id)
            return

        if pending_kind == "flow_rebuild" and not command_name:
            await _handle_flow_rebuild(msg.wa_id, session_id, text, phone_number_id, pending_intent)
            return

        if pending_kind == "flow_config" and not command_name:
            await _handle_flow_config_input(msg.wa_id, session_id, text, phone_number_id, pending_intent)
            return

        if pending_kind == "flow_delete_confirm" and not command_name:
            await _handle_flow_delete_confirm(msg.wa_id, session_id, text, phone_number_id, pending_intent)
            return

        if command_name:
            await _dispatch_command(msg.wa_id, session_id, command_name, command_args, phone_number_id)
            return

        user = store.get_whatsapp_user(msg.wa_id) or {}
        default_pipeline_id = user.get("default_pipeline_id")
        if not default_pipeline_id:
            whatsapp.send_text(
                msg.wa_id,
                "No default flow set. Use /flow <description> to create one.",
                phone_number_id=phone_number_id,
            )
            return

        await _run_pipeline_and_send(msg.wa_id, default_pipeline_id, text, phone_number_id)
    except Exception:
        log.exception("Failed to process WhatsApp message")


async def _handle_flow(
    wa_id: str,
    session_id: str,
    text: str,
    phone_number_id: str | None,
) -> None:
    description = text[len("/flow"):].strip()
    if not description:
        whatsapp.send_text(wa_id, "Usage: /flow <description>", phone_number_id=phone_number_id)
        return

    result = _plan_with_history(session_id, description)
    if result.type == "clarification":
        store.set_whatsapp_session(wa_id, session_id, pending_kind="clarification", pending_intent=description)
        whatsapp.send_text(wa_id, _format_clarification(result), phone_number_id=phone_number_id)
        return

    pipeline_id = str(uuid.uuid4())
    nodes = [
        PipelineNode(
            id=step.id,
            block_id=step.block_type,
            inputs={"description": step.description, "prompt": step.prompt},
            config={"needs_web_search": step.needs_web_search},
        ).model_dump()
        for step in result.steps
    ]
    edges = [
        PipelineEdge(
            from_node=edge.from_step,
            to_node=edge.to_step,
            condition=edge.condition,
        ).model_dump()
        for edge in result.edges
    ]

    store.save_pipeline(
        pipeline_id,
        {
            "user_intent": result.intent,
            "trigger_type": "manual",
            "trigger": TriggerConfig(type="manual").model_dump(),
            "nodes": nodes,
            "edges": edges,
            "status": "active",
            "requires_file_input": result.requires_file_input,
        },
    )
    store.set_whatsapp_default_pipeline(wa_id, pipeline_id)
    store.set_whatsapp_session(wa_id, session_id, pending_kind=None, pending_intent=None)

    suffix = " (requires file input)" if result.requires_file_input else ""
    whatsapp.send_text(
        wa_id,
        f"Created flow {pipeline_id[:8]} and set it as default.{suffix}",
        phone_number_id=phone_number_id,
    )


async def _handle_clarification(
    wa_id: str,
    session_id: str,
    answer: str,
    phone_number_id: str | None,
) -> None:
    result = _plan_with_history(session_id, answer)
    if result.type == "clarification":
        store.set_whatsapp_session(wa_id, session_id, pending_kind="clarification")
        whatsapp.send_text(wa_id, _format_clarification(result), phone_number_id=phone_number_id)
        return

    pipeline_id = str(uuid.uuid4())
    nodes = [
        PipelineNode(
            id=step.id,
            block_id=step.block_type,
            inputs={"description": step.description, "prompt": step.prompt},
            config={"needs_web_search": step.needs_web_search},
        ).model_dump()
        for step in result.steps
    ]
    edges = [
        PipelineEdge(
            from_node=edge.from_step,
            to_node=edge.to_step,
            condition=edge.condition,
        ).model_dump()
        for edge in result.edges
    ]

    store.save_pipeline(
        pipeline_id,
        {
            "user_intent": result.intent,
            "trigger_type": "manual",
            "trigger": TriggerConfig(type="manual").model_dump(),
            "nodes": nodes,
            "edges": edges,
            "status": "active",
            "requires_file_input": result.requires_file_input,
        },
    )
    store.set_whatsapp_default_pipeline(wa_id, pipeline_id)
    store.set_whatsapp_session(wa_id, session_id, pending_kind=None, pending_intent=None)

    suffix = " (requires file input)" if result.requires_file_input else ""
    whatsapp.send_text(
        wa_id,
        f"Created flow {pipeline_id[:8]} and set it as default.{suffix}",
        phone_number_id=phone_number_id,
    )


async def _handle_run(wa_id: str, text: str, phone_number_id: str | None) -> None:
    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        whatsapp.send_text(
            wa_id,
            "Usage: /run <pipeline_id> [optional input]",
            phone_number_id=phone_number_id,
        )
        return

    pipeline_id = parts[1]
    user_input = parts[2] if len(parts) > 2 else ""
    if not store.get_pipeline(pipeline_id):
        whatsapp.send_text(
            wa_id,
            "Pipeline not found. Use /flow to create one.",
            phone_number_id=phone_number_id,
        )
        return

    await _run_pipeline_and_send(wa_id, pipeline_id, user_input, phone_number_id)


async def _run_pipeline_and_send(
    wa_id: str,
    pipeline_id: str,
    user_input: str,
    phone_number_id: str | None,
) -> None:
    try:
        whatsapp.send_text(wa_id, "Running your flow...", phone_number_id=phone_number_id)
    except Exception:
        log.exception("Failed to send initial WhatsApp message")
    try:
        result = await run_pipeline(pipeline_id, RunPipelineRequest(user_input=user_input))
    except HTTPException as exc:
        try:
            whatsapp.send_text(
                wa_id,
                f"Pipeline error: {exc.detail}",
                phone_number_id=phone_number_id,
            )
        except Exception:
            log.exception("Failed to send WhatsApp error message")
        return

    if result.errors:
        try:
            whatsapp.send_text(
                wa_id,
                "Flow failed: " + "; ".join(result.errors),
                phone_number_id=phone_number_id,
            )
        except Exception:
            log.exception("Failed to send WhatsApp failure message")
        return

    output = _extract_final_output(result.shared_context)
    try:
        whatsapp.send_result(wa_id, output, phone_number_id=phone_number_id)
    except Exception:
        log.exception("Failed to send WhatsApp result")


def _plan_with_history(session_id: str, message: str):
    history = store.get_chat_session(session_id)
    result = plan_pipeline(message, history=history or None)

    history = list(history)
    history.append({"role": "user", "content": message})

    if result.type == "clarification":
        history.append({"role": "assistant", "content": result.message})
        store.set_chat_session(session_id, history)
        return result

    history.append({"role": "assistant", "content": f"Created pipeline: {result.intent}"})
    store.set_chat_session(session_id, history)
    return result


def _extract_final_output(shared_context: dict) -> dict:
    if not shared_context:
        return {}
    for key in reversed(list(shared_context.keys())):
        if key == "user_input":
            continue
        value = shared_context.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _format_clarification(result) -> str:
    message = result.message or "Can you clarify?"
    options = getattr(result, "questions", None) or []
    if not options:
        return message
    bullets = "\n".join(f"- {opt}" for opt in options[:4])
    return f"{message}\n\nOptions:\n{bullets}"


def _parse_action_decision(text: str) -> tuple[int, bool] | None:
    match = re.match(r"^(approve|approved|yes|y|decline|declined|no|n)\s+(\d+)$", text, re.I)
    if not match:
        return None
    word = match.group(1).lower()
    action_id = int(match.group(2))
    approved = word in {"approve", "approved", "yes", "y"}
    return action_id, approved


def _verify_signature(body: bytes, signature: str, secret: str) -> bool:
    if not signature:
        return False
    if not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
