"""Data diff block — compares old and new data and reports changes."""

import json


async def execute(inputs: dict, context: dict) -> dict:
    old = inputs["old_data"]
    new = inputs["new_data"]

    # Handle list comparison
    if isinstance(old, list) and isinstance(new, list):
        old_set = {json.dumps(i, sort_keys=True, default=str) for i in old}
        new_set = {json.dumps(i, sort_keys=True, default=str) for i in new}
        added = [json.loads(i) for i in new_set - old_set]
        removed = [json.loads(i) for i in old_set - new_set]
        return {
            "has_changes": bool(added or removed),
            "added": added,
            "removed": removed,
            "modified": [],
            "summary": f"{len(added)} added, {len(removed)} removed",
        }

    # Handle dict comparison
    if isinstance(old, dict) and isinstance(new, dict):
        added = [{"key": k, "value": new[k]} for k in new if k not in old]
        removed = [{"key": k, "value": old[k]} for k in old if k not in new]
        modified = [
            {"key": k, "old": old[k], "new": new[k]}
            for k in old if k in new and old[k] != new[k]
        ]
        return {
            "has_changes": bool(added or removed or modified),
            "added": added,
            "removed": removed,
            "modified": modified,
            "summary": f"{len(added)} added, {len(removed)} removed, {len(modified)} modified",
        }

    # Scalar comparison
    changed = old != new
    return {
        "has_changes": changed,
        "added": [new] if changed else [],
        "removed": [old] if changed else [],
        "modified": [],
        "summary": "Values differ" if changed else "No changes",
    }
