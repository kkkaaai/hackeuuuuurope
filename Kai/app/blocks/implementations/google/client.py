"""Google API client — shared OAuth2 credential loader for Gmail & Calendar."""

from __future__ import annotations

import logging
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings

logger = logging.getLogger("agentflow.blocks.google")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/calendar",
]


def _load_credentials() -> Credentials:
    """Load OAuth2 credentials from token.json, refreshing if expired."""
    token_path = settings.google_oauth_token_json_path
    if not token_path or not os.path.exists(token_path):
        raise ValueError(
            "Google OAuth token file not found. "
            "Run `python scripts/google_oauth_login.py` to authenticate."
        )

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            logger.error("Google OAuth refresh error [%s]: %s", type(e).__name__, e)
            raise ValueError("Google OAuth refresh failed — re-run OAuth login") from None
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        return creds

    raise ValueError(
        "Google OAuth token expired with no refresh token. "
        "Run `python scripts/google_oauth_login.py` to re-authenticate."
    )


def get_gmail_service():
    """Build a Gmail API v1 service client."""
    creds = _load_credentials()
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def get_calendar_service():
    """Build a Google Calendar API v3 service client."""
    creds = _load_credentials()
    return build("calendar", "v3", credentials=creds, cache_discovery=False)
