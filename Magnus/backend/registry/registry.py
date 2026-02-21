"""Block registry — loads system blocks from blocks.json and custom blocks from custom_blocks.json.

Custom blocks shadow system blocks on ID collision.
save() writes only to custom_blocks.json.
"""

import json
from pathlib import Path
from typing import Optional


class BlockRegistry:
    def __init__(self, path: Optional[Path] = None):
        base = path or Path(__file__).parent
        self._system_path = base / "blocks.json"
        self._custom_path = base / "custom_blocks.json"

        self._system: dict[str, dict] = {}
        self._custom: dict[str, dict] = {}

        if self._system_path.exists():
            with open(self._system_path) as f:
                self._system = {b["id"]: b for b in json.load(f)}

        if self._custom_path.exists():
            with open(self._custom_path) as f:
                self._custom = {b["id"]: b for b in json.load(f)}

    def get(self, block_id: str) -> dict:
        # Custom blocks shadow system blocks
        if block_id in self._custom:
            return self._custom[block_id]
        if block_id in self._system:
            return self._system[block_id]
        raise KeyError(f"Block not found: {block_id}")

    def save(self, block: dict):
        """Save a block to custom_blocks.json."""
        self._custom[block["id"]] = block
        with open(self._custom_path, "w") as f:
            json.dump(list(self._custom.values()), f, indent=2)

    def list_all(self) -> list[dict]:
        """Return all blocks. Custom blocks shadow system blocks on ID collision."""
        merged = {**self._system, **self._custom}
        return list(merged.values())

    def list_system(self) -> list[dict]:
        return list(self._system.values())

    def list_custom(self) -> list[dict]:
        return list(self._custom.values())

    def search(self, query: str) -> list[dict]:
        """Case-insensitive search across id, name, description, and tags."""
        q = query.lower()
        return [
            b for b in self.list_all()
            if q in b["id"].lower()
            or q in b["name"].lower()
            or q in b.get("description", "").lower()
            or any(q in tag.lower() for tag in b.get("tags", []))
        ]


registry = BlockRegistry()
