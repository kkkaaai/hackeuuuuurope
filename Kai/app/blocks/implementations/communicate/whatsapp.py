from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from app.blocks.executor import register_implementation
from app.config import settings
from app.services.whatsapp import WhatsAppClient

logger = logging.getLogger("agentflow.blocks.whatsapp")

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


@register_implementation("whatsapp_send_message")
async def whatsapp_send_message(inputs: dict[str, Any]) -> dict[str, Any]:
    """Send a WhatsApp message via Meta Cloud API."""
    phone_number = inputs["phone_number"]
    message_body = inputs["message"]

    if not _E164_RE.match(phone_number):
        raise ValueError(
            "phone_number must be E.164 format: +[country][number], 7-15 digits"
        )

    if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        raise ValueError(
            "WhatsApp credentials not configured — set WHATSAPP_ACCESS_TOKEN "
            "and WHATSAPP_PHONE_NUMBER_ID in .env"
        )

    if len(message_body) > 1600:
        message_body = message_body[:1597] + "..."

    try:
        client = WhatsAppClient()
        client.send_text(phone_number, message_body)
    except ValueError:
        raise
    except Exception as e:
        logger.error("WhatsApp API error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"WhatsApp send failed: {type(e).__name__}") from None

    logger.info("WhatsApp message sent to %s", phone_number)

    return {
        "status": "sent",
        "to": phone_number,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
