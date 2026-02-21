"""Trigger file upload block — returns file metadata (skipped by executor)."""

from pathlib import Path

from storage.uris import get_metadata, resolve_uri


async def execute(inputs: dict, context: dict) -> dict:
    ref = inputs["file_path"]
    uri = resolve_uri(ref)
    metadata = get_metadata(uri)

    file_type = inputs.get("file_type")
    if not file_type:
        file_type = metadata.get("content_type") or Path(ref).suffix.lstrip(".")

    return {
        "file_path": ref,
        "file_uri": uri,
        "file_type": file_type,
        "file_size_bytes": metadata.get("size_bytes", 0) or 0,
    }
