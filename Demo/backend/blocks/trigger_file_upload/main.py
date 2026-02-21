"""Trigger file upload block — returns file metadata (skipped by executor)."""

from pathlib import Path


async def execute(inputs: dict, context: dict) -> dict:
    fp = Path(inputs["file_path"])
    return {
        "file_path": str(fp),
        "file_type": inputs.get("file_type", fp.suffix.lstrip(".")),
        "file_size_bytes": fp.stat().st_size if fp.exists() else 0,
    }
