from __future__ import annotations

import base64
import logging
import os
import re
from email.message import EmailMessage
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings

logger = logging.getLogger("agentflow.blocks.google")

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.labels",
]
CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]

_BASE64URL_RE = re.compile(r"^[A-Za-z0-9_-]+=*$")


def _load_credentials(scopes: list[str]) -> Credentials:
    token_path = settings.google_oauth_token_json_path
    if not token_path:
        raise ValueError("GOOGLE_OAUTH_TOKEN_JSON_PATH not configured — add it to .env")
    if not os.path.exists(token_path):
        raise ValueError(f"Google OAuth token file not found: {token_path}")

    creds = Credentials.from_authorized_user_file(token_path, scopes)
    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            logger.error("Google OAuth refresh error [%s]: %s", type(e).__name__, e)
            raise ValueError("Google OAuth refresh failed") from None
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())
        return creds

    raise ValueError(
        "Google OAuth token expired or missing refresh token. Run the OAuth login flow."
    )


def get_gmail_service():
    creds = _load_credentials(GMAIL_SCOPES)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def get_calendar_service():
    creds = _load_credentials(CALENDAR_SCOPES)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _normalize_address_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple)):
        items: list[str] = []
        for entry in value:
            if entry is None:
                continue
            items.extend(_normalize_address_list(entry))
        return items
    return [str(value)]


def _normalize_raw_message(raw_message: str) -> str:
    raw = raw_message.strip()
    if _BASE64URL_RE.fullmatch(raw):
        return raw
    return base64.urlsafe_b64encode(raw_message.encode("utf-8")).decode("utf-8")


def build_gmail_raw_message(inputs: dict[str, Any]) -> str:
    raw_message = inputs.get("raw_message")
    if raw_message:
        return _normalize_raw_message(str(raw_message))

    to_list = _normalize_address_list(inputs.get("to"))
    if not to_list:
        raise ValueError("Missing 'to' or 'raw_message' for Gmail message")

    subject = inputs.get("subject", "")
    body = inputs.get("body")
    html_body = inputs.get("html_body")
    if body is None and html_body is None:
        raise ValueError("Missing 'body'/'html_body' or 'raw_message' for Gmail message")

    message = EmailMessage()
    from_address = inputs.get("from")
    if from_address:
        message["From"] = str(from_address)
    message["To"] = ", ".join(to_list)

    cc_list = _normalize_address_list(inputs.get("cc"))
    if cc_list:
        message["Cc"] = ", ".join(cc_list)
    bcc_list = _normalize_address_list(inputs.get("bcc"))
    if bcc_list:
        message["Bcc"] = ", ".join(bcc_list)

    reply_to = inputs.get("reply_to")
    if reply_to:
        message["Reply-To"] = str(reply_to)

    if subject:
        message["Subject"] = str(subject)

    in_reply_to = inputs.get("in_reply_to")
    if in_reply_to:
        message["In-Reply-To"] = str(in_reply_to)

    references = inputs.get("references")
    if references:
        if isinstance(references, (list, tuple)):
            message["References"] = " ".join(str(ref) for ref in references if ref)
        else:
            message["References"] = str(references)

    if html_body and body:
        message.set_content(str(body))
        message.add_alternative(str(html_body), subtype="html")
    elif html_body:
        message.add_alternative(str(html_body), subtype="html")
    else:
        message.set_content(str(body))

    raw_bytes = message.as_bytes()
    return base64.urlsafe_b64encode(raw_bytes).decode("utf-8")
