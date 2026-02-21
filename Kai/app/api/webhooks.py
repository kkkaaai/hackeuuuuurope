"""Webhook and file upload trigger endpoints."""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile, File

router = APIRouter(prefix="/api", tags=["triggers"])

logger = logging.getLogger("agentflow.api.webhooks")

UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/webhooks/{webhook_path:path}")
async def receive_webhook(webhook_path: str, request: Request) -> dict[str, Any]:
    """Receive an incoming webhook and trigger the associated pipeline."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            body = {}
    else:
        body = {}

    logger.info("Webhook received at /%s", webhook_path)

    # TODO: Look up pipeline associated with this webhook path and trigger it
    return {
        "received": True,
        "webhook_path": webhook_path,
        "payload": body,
        "trigger_id": f"wh_{uuid.uuid4().hex[:8]}",
    }


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload a file and return metadata for trigger_file_upload."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")

    # Sanitize filename: strip directory components, allowlist characters
    original_name = Path(file.filename or "upload").name
    safe_name = re.sub(r'[^\w.\-]', '_', original_name)
    safe_filename = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    file_path = UPLOAD_DIR / safe_filename

    # Verify resolved path is inside upload directory
    if not file_path.resolve().is_relative_to(UPLOAD_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")

    with open(file_path, "wb") as f:
        f.write(content)

    logger.info("File uploaded: %s (%d bytes)", safe_filename, len(content))

    return {
        "file_id": safe_filename,
        "file_type": file.content_type or "application/octet-stream",
        "file_size_bytes": len(content),
    }
