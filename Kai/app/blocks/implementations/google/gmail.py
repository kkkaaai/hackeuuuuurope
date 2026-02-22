"""Gmail integration blocks — send, read, and find emails."""

from __future__ import annotations

import base64
import logging
from email.message import EmailMessage
from typing import Any

from app.blocks.executor import register_implementation
from app.blocks.implementations.google.client import get_gmail_service

logger = logging.getLogger("agentflow.blocks.google.gmail")


def _build_raw_message(
    to: str,
    subject: str,
    body: str,
    html_body: str | None = None,
    cc: str | None = None,
    bcc: str | None = None,
) -> str:
    """Build a base64url-encoded RFC 2822 message."""
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc

    if html_body and body:
        msg.set_content(body)
        msg.add_alternative(html_body, subtype="html")
    elif html_body:
        msg.set_content(html_body, subtype="html")
    else:
        msg.set_content(body)

    return base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")


def _extract_header(headers: list[dict], name: str) -> str:
    """Pull a header value from the Gmail message headers list."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _decode_body(payload: dict) -> str:
    """Best-effort decode of a Gmail message body (plain text preferred)."""
    # Simple single-part message
    body_data = payload.get("body", {}).get("data")
    if body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

    # Multipart — find text/plain first, fall back to text/html
    parts = payload.get("parts", [])
    plain = ""
    html = ""
    for part in parts:
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if not data:
            continue
        decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        if mime == "text/plain" and not plain:
            plain = decoded
        elif mime == "text/html" and not html:
            html = decoded
    return plain or html


@register_implementation("gmail_send_email")
async def gmail_send_email(inputs: dict[str, Any]) -> dict[str, Any]:
    """Send an email via Gmail."""
    to = inputs["to"]
    subject = inputs["subject"]
    body = inputs.get("body", "")
    html_body = inputs.get("html_body")
    cc = inputs.get("cc")
    bcc = inputs.get("bcc")

    if not to:
        raise ValueError("Recipient 'to' is required")
    if not subject:
        raise ValueError("'subject' is required")
    if not body and not html_body:
        raise ValueError("'body' or 'html_body' is required")

    try:
        service = get_gmail_service()
        raw = _build_raw_message(to, subject, body, html_body, cc, bcc)
        result = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
    except ValueError:
        raise
    except Exception as e:
        logger.error("Gmail send error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail send failed: {type(e).__name__}") from None

    logger.info("Email sent to %s (id=%s)", to, result.get("id"))
    return {
        "message_id": result.get("id", ""),
        "thread_id": result.get("threadId", ""),
        "status": "sent",
    }


@register_implementation("gmail_read_email")
async def gmail_read_email(inputs: dict[str, Any]) -> dict[str, Any]:
    """Read a specific email by message ID, or the latest email if no ID given."""
    message_id = inputs.get("message_id")

    try:
        service = get_gmail_service()

        # If no message_id, fetch the most recent message
        if not message_id:
            list_result = service.users().messages().list(
                userId="me", maxResults=1
            ).execute()
            messages = list_result.get("messages", [])
            if not messages:
                return {
                    "message_id": "",
                    "thread_id": "",
                    "from": "",
                    "to": "",
                    "subject": "",
                    "body": "",
                    "date": "",
                    "snippet": "No messages found",
                }
            message_id = messages[0]["id"]

        msg = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
    except ValueError:
        raise
    except Exception as e:
        logger.error("Gmail read error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail read failed: {type(e).__name__}") from None

    headers = msg.get("payload", {}).get("headers", [])
    body_text = _decode_body(msg.get("payload", {}))

    return {
        "message_id": msg.get("id", ""),
        "thread_id": msg.get("threadId", ""),
        "from": _extract_header(headers, "From"),
        "to": _extract_header(headers, "To"),
        "subject": _extract_header(headers, "Subject"),
        "body": body_text,
        "date": _extract_header(headers, "Date"),
        "snippet": msg.get("snippet", ""),
    }


@register_implementation("gmail_find_emails")
async def gmail_find_emails(inputs: dict[str, Any]) -> dict[str, Any]:
    """Search Gmail using a query string and return matching emails."""
    query = inputs.get("query", "")
    max_results = min(int(inputs.get("max_results", 10)), 50)

    if not query:
        raise ValueError("'query' is required — use Gmail search syntax (e.g. 'from:kai subject:meeting')")

    try:
        service = get_gmail_service()
        list_result = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        message_stubs = list_result.get("messages", [])

        emails = []
        for stub in message_stubs:
            msg = service.users().messages().get(
                userId="me", id=stub["id"], format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"],
            ).execute()
            headers = msg.get("payload", {}).get("headers", [])
            emails.append({
                "message_id": msg.get("id", ""),
                "thread_id": msg.get("threadId", ""),
                "from": _extract_header(headers, "From"),
                "to": _extract_header(headers, "To"),
                "subject": _extract_header(headers, "Subject"),
                "date": _extract_header(headers, "Date"),
                "snippet": msg.get("snippet", ""),
            })
    except ValueError:
        raise
    except Exception as e:
        logger.error("Gmail find error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail find failed: {type(e).__name__}") from None

    return {
        "emails": emails,
        "result_count": len(emails),
        "query": query,
    }
