"""LangGraph state definition for pipeline execution."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict


def merge_dicts(old: dict, new: dict) -> dict:
    """Reducer: merge new keys into existing dict."""
    merged = {**old}
    merged.update(new)
    return merged


def append_list(old: list, new: list) -> list:
    """Reducer: append new items to existing list."""
    return old + new


class PipelineState(TypedDict):
    # Accumulated outputs from all executed blocks: {node_id: {output_dict}}
    shared_context: Annotated[dict[str, Any], merge_dicts]
    # Ordered log of executed node IDs
    execution_log: Annotated[list[str], append_list]
    # Any errors encountered
    errors: Annotated[list[str], append_list]
    # Memory values loaded at pipeline start
    memory: dict[str, Any]
    # The pipeline definition (nodes, edges, etc.)
    pipeline_def: dict[str, Any]
    # Trigger data passed at pipeline start
    trigger_data: dict[str, Any]
    # Previous run's shared_context for condition-based watching (old vs new comparison)
    checkpoint: dict[str, Any]
