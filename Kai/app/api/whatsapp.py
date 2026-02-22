"""WhatsApp webhook + command handling.

Receives incoming WhatsApp messages via Meta Cloud API webhook,
dispatches to Orchestra agent for pipeline creation, and sends
results back over WhatsApp.

Two paths to the same output:
  1. Frontend: POST /api/chat -> Orchestra -> Q&A -> pipeline created
  2. WhatsApp: message -> Orchestra -> Q&A via WhatsApp -> pipeline created
"""

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
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, HTTPException, Request

from app.agents.orchestra import OrchestraAgent
from app.api.dependencies import get_registry
from app.config import settings
from app.database import get_db, store
from app.engine.runner import PipelineRunner
from app.memory.store import memory_store
from app.models.pipeline import Pipeline, PipelineEdge, PipelineNode, TriggerConfig
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


HELP_TEXT = (
    "*AgentFlow Commands*\n"
    "\n"
    "/flow <description> — Create a new automation flow\n"
    "/run <pipeline_id> [input] — Run a specific flow\n"
    "/help — Show this help message\n"
    "\n"
    "Or just send a message to create a flow or run your default one."
)


# ── Webhook endpoints ──────────────────────────────────────────────


@router.get("/api/whatsapp/webhook")
def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return int(challenge) if challenge and challenge.isdigit() else (challenge or "")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/api/whatsapp/webhook")
async def receive_webhook(request: Request):
    body = await request.body()
    log.info("WhatsApp webhook hit — %d bytes", len(body))

    if settings.whatsapp_app_secret:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not _verify_signature(body, signature, settings.whatsapp_app_secret):
            log.warning("WhatsApp signature verification FAILED")
            raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = json.loads(body.decode("utf-8")) if body else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    log.info("WhatsApp payload: %s", json.dumps(payload, indent=2)[:2000])
    messages = parse_incoming_messages(payload)
    log.info("Parsed %d message(s) from webhook", len(messages))
    for msg in messages:
        log.info(">> FROM %s: %s", msg.wa_id, msg.text)
        asyncio.create_task(_handle_message(msg))
    return {"ok": True}


# ── Message handling ───────────────────────────────────────────────


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
            phone_display=msg.contact_name or "",
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
            _ack(msg.wa_id, phone_number_id)
            await _handle_clarification(msg.wa_id, session_id, text, phone_number_id)
            return

        if pending_kind == "flow_rebuild" and not command_name:
            _ack(msg.wa_id, phone_number_id)
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

        # No command, no pending state — check for default pipeline
        user = store.get_whatsapp_user(msg.wa_id) or {}
        default_pipeline_id = user.get("default_pipeline_id")

        if default_pipeline_id:
            # Run the default pipeline with the user's text as input
            await _run_pipeline_and_send(msg.wa_id, default_pipeline_id, text, phone_number_id)
        else:
            # No default flow — treat plain text as a flow creation request
            _ack(msg.wa_id, phone_number_id, "Building your flow...")
            await _handle_flow_creation(msg.wa_id, session_id, text, phone_number_id)
    except Exception:
        log.exception("Failed to process WhatsApp message")


# ── Acknowledgements ──────────────────────────────────────────────


def _ack(wa_id: str, phone_number_id: str | None, message: str = "Got it, working on it...") -> None:
    """Send an immediate acknowledgement so the user knows we're processing."""
    try:
        whatsapp.send_text(wa_id, message, phone_number_id=phone_number_id)
    except Exception:
        log.debug("Failed to send ack", exc_info=True)


# ── Orchestra integration ─────────────────────────────────────────


async def _decompose_with_history(session_id: str, message: str) -> dict[str, Any]:
    """Use Orchestra agent to decompose a message, with conversation history."""
    registry = get_registry()
    orchestra = OrchestraAgent(registry)

    history = store.get_chat_session(session_id)
    decomposition = await orchestra.decompose(
        message,
        conversation_history=history or None,
    )

    history = list(history)
    history.append({"role": "user", "content": message})

    if decomposition.get("type") == "clarification":
        history.append({"role": "assistant", "content": json.dumps(decomposition)})
        store.set_chat_session(session_id, history)
        return decomposition

    history.append({"role": "assistant", "content": f"Created pipeline: {decomposition.get('user_intent', message)}"})
    store.set_chat_session(session_id, history)
    return decomposition


# ── Flow creation (from /flow command or plain text) ──────────────


async def _handle_flow_creation(
    wa_id: str,
    session_id: str,
    description: str,
    phone_number_id: str | None,
) -> None:
    """Core flow creation logic — shared by /flow command and plain text."""
    result = await _decompose_with_history(session_id, description)
    if result.get("type") == "clarification":
        store.set_whatsapp_session(wa_id, session_id, pending_kind="clarification", pending_intent=description)
        whatsapp.send_text(wa_id, _format_clarification(result), phone_number_id=phone_number_id)
        return

    pipeline_id = _create_pipeline_from_decomposition(result, wa_id, session_id)
    node_count = len(result.get("nodes", []))
    intent = result.get("user_intent", description)
    whatsapp.send_text(
        wa_id,
        f"Flow created ({node_count} blocks): {intent}\n\nID: {pipeline_id[:12]}\nSet as your default flow.",
        phone_number_id=phone_number_id,
    )


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

    _ack(wa_id, phone_number_id, "Building your flow...")
    await _handle_flow_creation(wa_id, session_id, description, phone_number_id)


async def _handle_clarification(
    wa_id: str,
    session_id: str,
    answer: str,
    phone_number_id: str | None,
) -> None:
    result = await _decompose_with_history(session_id, answer)
    if result.get("type") == "clarification":
        store.set_whatsapp_session(wa_id, session_id, pending_kind="clarification")
        whatsapp.send_text(wa_id, _format_clarification(result), phone_number_id=phone_number_id)
        return

    pipeline_id = _create_pipeline_from_decomposition(result, wa_id, session_id)
    node_count = len(result.get("nodes", []))
    intent = result.get("user_intent", "")
    whatsapp.send_text(
        wa_id,
        f"Flow created ({node_count} blocks): {intent}\n\nID: {pipeline_id[:12]}\nSet as your default flow.",
        phone_number_id=phone_number_id,
    )


def _create_pipeline_from_decomposition(decomposition: dict, wa_id: str, session_id: str) -> str:
    """Store a pipeline from Orchestra decomposition output and set as default."""
    pipeline_id = f"pipe_{uuid.uuid4().hex[:10]}"
    nodes_raw = decomposition.get("nodes", [])
    edges_raw = decomposition.get("edges", [])

    registry = get_registry()
    nodes = []
    for n in nodes_raw:
        block_id = n.get("block_id", "")
        if block_id and not registry.get(block_id):
            log.warning("Skipping unknown block_id from decomposition: %s", block_id)
            continue
        nodes.append(PipelineNode(
            id=n.get("id", f"node_{uuid.uuid4().hex[:6]}"),
            block_id=block_id,
            inputs=n.get("inputs", {}),
            config=n.get("config", {}),
        ).model_dump())

    edges = []
    for e in edges_raw:
        edges.append(PipelineEdge(
            from_node=e.get("from_node", ""),
            to_node=e.get("to_node", ""),
            condition=e.get("condition"),
        ).model_dump())

    store.save_pipeline(
        pipeline_id,
        {
            "user_intent": decomposition.get("user_intent", ""),
            "trigger_type": "manual",
            "trigger": TriggerConfig(type="manual").model_dump(),
            "nodes": nodes,
            "edges": edges,
            "status": "active",
        },
    )
    store.set_whatsapp_default_pipeline(wa_id, pipeline_id)
    store.set_whatsapp_session(wa_id, session_id, pending_kind=None, pending_intent=None)
    return pipeline_id


# ── Run command ────────────────────────────────────────────────────


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
        pipeline_data = store.get_pipeline(pipeline_id)
        if not pipeline_data:
            whatsapp.send_text(wa_id, "Pipeline not found.", phone_number_id=phone_number_id)
            return

        defn = pipeline_data.get("definition", {})
        pipeline = Pipeline(
            id=pipeline_id,
            user_intent=pipeline_data.get("user_intent", ""),
            trigger=TriggerConfig(**defn.get("trigger", {"type": "manual"})),
            nodes=[PipelineNode(**n) for n in defn.get("nodes", [])],
            edges=[PipelineEdge(**e) for e in defn.get("edges", [])],
        )

        registry = get_registry()
        runner = PipelineRunner(registry=registry, memory=memory_store)
        result = await runner.run(pipeline, trigger_data={"user_input": user_input})
    except Exception:
        log.exception("Pipeline execution failed")
        try:
            whatsapp.send_text(
                wa_id,
                "Flow failed. Please try again.",
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


# ── Helpers ────────────────────────────────────────────────────────


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


def _format_clarification(result: dict) -> str:
    message = result.get("message") or "Can you clarify?"
    options = result.get("questions", [])
    if not options:
        return message
    bullets = "\n".join(f"- {opt}" for opt in options[:4])
    return f"{message}\n\n{bullets}"


def _parse_action_decision(text: str) -> tuple[int, bool] | None:
    match = re.match(r"^(approve|approved|yes|y|decline|declined|no|n)\s+(\d+)$", text, re.I)
    if not match:
        return None
    word = match.group(1).lower()
    action_id = int(match.group(2))
    approved = word in {"approve", "approved", "yes", "y"}
    return action_id, approved


def _parse_command(text: str) -> tuple[str | None, str]:
    """Extract command name and args from /command text."""
    if not text.startswith("/"):
        return None, text
    parts = text.split(maxsplit=1)
    name = parts[0][1:]  # strip leading /
    args = parts[1] if len(parts) > 1 else ""
    return name, args


async def _dispatch_command(
    wa_id: str,
    session_id: str,
    command_name: str,
    command_args: str,
    phone_number_id: str | None,
) -> None:
    if command_name == "flow":
        await _handle_flow(wa_id, session_id, f"/flow {command_args}", phone_number_id)
        return
    if command_name == "run":
        await _handle_run(wa_id, f"/run {command_args}", phone_number_id)
        return
    if command_name == "help":
        whatsapp.send_text(wa_id, HELP_TEXT, phone_number_id=phone_number_id)
        return

    cmd = COMMANDS.get(command_name)
    if cmd:
        await cmd.handler(wa_id, session_id, command_args, phone_number_id)
        return

    whatsapp.send_text(
        wa_id,
        f"Unknown command: /{command_name}\n\n{HELP_TEXT}",
        phone_number_id=phone_number_id,
    )


def _verify_signature(body: bytes, signature: str, secret: str) -> bool:
    if not signature:
        return False
    if not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── Stub handlers for pending states (implement as needed) ─────────


async def _handle_flow_rebuild(
    wa_id: str, session_id: str, text: str, phone_number_id: str | None, pending_intent: str | None
) -> None:
    await _handle_flow(wa_id, session_id, f"/flow {pending_intent or text}", phone_number_id)


async def _handle_flow_config_input(
    wa_id: str, session_id: str, text: str, phone_number_id: str | None, pending_intent: str | None
) -> None:
    whatsapp.send_text(wa_id, "Config input not yet supported.", phone_number_id=phone_number_id)
    store.set_whatsapp_session(wa_id, session_id, pending_kind=None, pending_intent=None)


async def _handle_flow_delete_confirm(
    wa_id: str, session_id: str, text: str, phone_number_id: str | None, pending_intent: str | None
) -> None:
    whatsapp.send_text(wa_id, "Delete confirm not yet supported.", phone_number_id=phone_number_id)
    store.set_whatsapp_session(wa_id, session_id, pending_kind=None, pending_intent=None)
