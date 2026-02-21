from __future__ import annotations

import logging
from typing import Any

from app.blocks.executor import register_implementation
from app.config import settings

logger = logging.getLogger("agentflow.blocks.email")


@register_implementation("email_send")
async def email_send(inputs: dict[str, Any]) -> dict[str, Any]:
    """Send an email via SendGrid."""
    to_email = inputs["to"]
    subject = inputs["subject"]
    body = inputs["body"]
    from_name = inputs.get("from_name", "AgentFlow")

    if not settings.sendgrid_api_key:
        raise ValueError("SENDGRID_API_KEY not configured — add it to .env")

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email=f"{from_name} <noreply@agentflow.ai>",
            to_emails=to_email,
            subject=subject,
            html_content=body,
        )

        sg = SendGridAPIClient(settings.sendgrid_api_key)
        response = sg.send(message)
    except Exception as e:
        logger.error("SendGrid API error: %s", e)
        raise ValueError(f"SendGrid email failed: {type(e).__name__}") from None

    return {
        "message_id": response.headers.get("X-Message-Id", ""),
        "status": "sent" if response.status_code in (200, 202) else "failed",
    }
