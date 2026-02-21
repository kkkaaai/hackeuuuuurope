from __future__ import annotations

import operator
from typing import Any

from app.blocks.executor import register_implementation

OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


@register_implementation("filter_threshold")
async def filter_threshold(inputs: dict[str, Any]) -> dict[str, Any]:
    """Check if a numeric value passes a threshold comparison."""
    raw_value = inputs.get("value")
    raw_threshold = inputs.get("threshold")

    # Handle None — upstream block may have failed
    if raw_value is None:
        return {
            "passes": False,
            "value": None,
            "threshold": raw_threshold,
            "difference": None,
            "error": "value is None (upstream block may have failed)",
        }

    value = float(raw_value)
    threshold = float(raw_threshold)
    op_str = inputs.get("operator", "<")

    op_fn = OPERATORS.get(op_str, operator.lt)
    passes = op_fn(value, threshold)

    return {
        "passes": passes,
        "value": value,
        "threshold": threshold,
        "difference": round(value - threshold, 4),
    }


@register_implementation("data_transform")
async def data_transform(inputs: dict[str, Any]) -> dict[str, Any]:
    """Reshape data by mapping fields from one structure to another."""
    data = inputs["data"]
    mapping = inputs["mapping"]

    transformed = {}
    for new_key, source_key in mapping.items():
        if isinstance(source_key, str) and source_key in data:
            transformed[new_key] = data[source_key]
        else:
            transformed[new_key] = source_key  # Literal value

    return {"transformed": transformed}


@register_implementation("loop_for_each")
async def loop_for_each(inputs: dict[str, Any]) -> dict[str, Any]:
    """Iterate over a list of items.

    Note: Actual per-item block execution is handled by the pipeline engine.
    This block collects and formats the iteration results.
    """
    items = inputs.get("items", [])
    return {
        "results": items,  # Pass-through for now; engine handles actual iteration
        "count": len(items),
    }


@register_implementation("data_diff")
async def data_diff(inputs: dict[str, Any]) -> dict[str, Any]:
    """Compare two datasets and return what changed."""
    old_data = inputs["old_data"]
    new_data = inputs["new_data"]

    if isinstance(old_data, dict) and isinstance(new_data, dict):
        return _diff_dicts(old_data, new_data)
    elif isinstance(old_data, list) and isinstance(new_data, list):
        return _diff_lists(old_data, new_data)
    else:
        changed = old_data != new_data
        return {
            "has_changes": changed,
            "added": [],
            "removed": [],
            "modified": [{"old": old_data, "new": new_data}] if changed else [],
            "summary": f"Value changed from {old_data} to {new_data}" if changed else "No changes",
        }


def _diff_dicts(old: dict, new: dict) -> dict[str, Any]:
    all_keys = set(old.keys()) | set(new.keys())
    added = [{"field": k, "value": new[k]} for k in all_keys if k not in old]
    removed = [{"field": k, "value": old[k]} for k in all_keys if k not in new]
    modified = [
        {"field": k, "old": old[k], "new": new[k]}
        for k in all_keys
        if k in old and k in new and old[k] != new[k]
    ]

    changes = added + removed + modified
    parts = []
    if added:
        parts.append(f"{len(added)} added")
    if removed:
        parts.append(f"{len(removed)} removed")
    if modified:
        parts.append(f"{len(modified)} modified")

    return {
        "has_changes": len(changes) > 0,
        "added": added,
        "removed": removed,
        "modified": modified,
        "summary": ", ".join(parts) if parts else "No changes",
    }


def _diff_lists(old: list, new: list) -> dict[str, Any]:
    old_set = set(str(x) for x in old)
    new_set = set(str(x) for x in new)
    added = [x for x in new if str(x) not in old_set]
    removed = [x for x in old if str(x) not in new_set]

    return {
        "has_changes": len(added) > 0 or len(removed) > 0,
        "added": added,
        "removed": removed,
        "modified": [],
        "summary": f"{len(added)} added, {len(removed)} removed" if added or removed else "No changes",
    }
