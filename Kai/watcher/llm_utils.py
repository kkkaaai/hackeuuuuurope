"""Shared LLM utilities for the watcher package."""

from __future__ import annotations

import json
from typing import Any

import anthropic

from app.config import settings

MODEL = "claude-sonnet-4-20250514"
COMPACT_JSON_MAX_CHARS = 8000


def has_api_key() -> bool:
    return bool(settings.anthropic_api_key)


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def compact_json(data: Any, max_chars: int = COMPACT_JSON_MAX_CHARS) -> str:
    raw = json.dumps(data, ensure_ascii=True)
    if len(raw) <= max_chars:
        return raw
    return raw[: max_chars - 15] + "...(truncated)"
