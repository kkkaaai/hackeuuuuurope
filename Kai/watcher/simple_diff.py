"""Fallback diffing when LLM is unavailable."""

from __future__ import annotations

import json
from typing import Any


def _short(value: Any, max_len: int = 300) -> str:
    text = json.dumps(value, ensure_ascii=True)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def simple_diff(prev: Any, curr: Any) -> list[dict]:
    if prev == curr:
        return []

    changes: list[dict] = []
    if isinstance(prev, dict) and isinstance(curr, dict):
        prev_keys = set(prev.keys())
        curr_keys = set(curr.keys())
        added = sorted(curr_keys - prev_keys)
        removed = sorted(prev_keys - curr_keys)
        common = sorted(prev_keys & curr_keys)

        if added:
            changes.append({
                "summary": f"Added keys: {', '.join(added)}",
                "importance": "medium",
                "details": {"added": added},
            })
        if removed:
            changes.append({
                "summary": f"Removed keys: {', '.join(removed)}",
                "importance": "medium",
                "details": {"removed": removed},
            })
        for key in common:
            if prev.get(key) != curr.get(key):
                changes.append({
                    "summary": f"Changed '{key}'",
                    "importance": "low",
                    "details": {
                        "before": _short(prev.get(key)),
                        "after": _short(curr.get(key)),
                    },
                })
        return changes

    if isinstance(prev, list) and isinstance(curr, list):
        if len(prev) != len(curr):
            changes.append({
                "summary": f"List length changed from {len(prev)} to {len(curr)}",
                "importance": "low",
                "details": {},
            })
        else:
            changes.append({
                "summary": "List contents changed",
                "importance": "low",
                "details": {},
            })
        return changes

    changes.append({
        "summary": "Value changed",
        "importance": "low",
        "details": {"before": _short(prev), "after": _short(curr)},
    })
    return changes
