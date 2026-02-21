from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.blocks.executor import register_implementation


@register_implementation("trigger_webhook")
async def trigger_webhook(inputs: dict[str, Any]) -> dict[str, Any]:
    """Webhook trigger — receives payload from external service via FastAPI route."""
    return {
        "payload": inputs.get("payload", {}),
        "headers": inputs.get("headers", {}),
        "method": inputs.get("method", "POST"),
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }


@register_implementation("trigger_file_upload")
async def trigger_file_upload(inputs: dict[str, Any]) -> dict[str, Any]:
    """File upload trigger — receives file metadata from upload endpoint."""
    import os

    file_path = inputs.get("file_path", "")
    file_type = inputs.get("file_type", "application/octet-stream")

    file_size = 0
    if file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)

    return {
        "file_path": file_path,
        "file_type": file_type,
        "file_size_bytes": file_size,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }
