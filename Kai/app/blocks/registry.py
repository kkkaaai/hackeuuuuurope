from __future__ import annotations

import json
import logging
from pathlib import Path

from app.models.block import BlockCategory, BlockDefinition

logger = logging.getLogger("agentflow.registry")

DEFINITIONS_DIR = Path(__file__).parent / "definitions"


class BlockRegistry:
    """In-memory registry of all block definitions."""

    def __init__(self) -> None:
        self._blocks: dict[str, BlockDefinition] = {}

    def load_from_directory(self, directory: Path | None = None) -> int:
        """Load block definitions from all JSON files in the definitions directory."""
        directory = directory or DEFINITIONS_DIR
        loaded = 0
        for path in sorted(directory.glob("*.json")):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            blocks = data if isinstance(data, list) else data.get("blocks", [])
            for block_data in blocks:
                try:
                    block = BlockDefinition(**block_data)
                    self._blocks[block.id] = block
                    loaded += 1
                except Exception as exc:
                    logger.warning("Skipped invalid block in %s: %s", path.name, exc)
        logger.info("Loaded %d block definitions from %s", loaded, directory)
        return loaded

    def get(self, block_id: str) -> BlockDefinition | None:
        return self._blocks.get(block_id)

    def register(self, block: BlockDefinition) -> None:
        self._blocks[block.id] = block
        logger.info("Registered block: %s", block.id)

    def list_all(self) -> list[BlockDefinition]:
        return list(self._blocks.values())

    def list_by_category(self, category: BlockCategory) -> list[BlockDefinition]:
        return [b for b in self._blocks.values() if b.category == category]

    def list_by_tier(self, tier: int) -> list[BlockDefinition]:
        return [b for b in self._blocks.values() if b.tier == tier]

    def search(self, query: str) -> list[BlockDefinition]:
        """Simple keyword search across block names and descriptions."""
        query_lower = query.lower()
        terms = query_lower.split()
        results: list[tuple[int, BlockDefinition]] = []

        for block in self._blocks.values():
            text = f"{block.name} {block.description} {block.id}".lower()
            score = sum(1 for term in terms if term in text)
            if score > 0:
                results.append((score, block))

        results.sort(key=lambda x: x[0], reverse=True)
        return [block for _, block in results]

    @property
    def count(self) -> int:
        return len(self._blocks)


# Global singleton
registry = BlockRegistry()
