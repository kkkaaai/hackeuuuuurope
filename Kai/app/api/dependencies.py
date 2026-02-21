"""Shared dependencies for API routers."""

from __future__ import annotations

from functools import lru_cache

from app.blocks.loader import load_all_implementations
from app.blocks.registry import BlockRegistry


@lru_cache(maxsize=1)
def get_registry() -> BlockRegistry:
    """Return the singleton BlockRegistry with all implementations loaded."""
    registry = BlockRegistry()
    registry.load_from_directory()
    load_all_implementations()
    return registry
