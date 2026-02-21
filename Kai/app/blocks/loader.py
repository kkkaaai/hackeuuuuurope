"""Auto-imports all block implementation modules so their @register_implementation decorators run."""

from __future__ import annotations

import importlib
import logging
from pathlib import Path

logger = logging.getLogger("agentflow.loader")

IMPLEMENTATIONS_DIR = Path(__file__).parent / "implementations"


def load_all_implementations() -> int:
    """Import every .py file under implementations/ to trigger registration."""
    count = 0
    for py_file in sorted(IMPLEMENTATIONS_DIR.rglob("*.py")):
        if py_file.name.startswith("_"):
            continue
        # Convert path to module: app.blocks.implementations.triggers.trigger_manual
        relative = py_file.relative_to(IMPLEMENTATIONS_DIR.parent.parent.parent)
        module_path = str(relative).replace("/", ".").removesuffix(".py")
        try:
            importlib.import_module(module_path)
            count += 1
        except Exception as e:
            logger.error("Failed to load %s: %s", module_path, e)
    logger.info("Loaded %d block implementation modules", count)
    return count
