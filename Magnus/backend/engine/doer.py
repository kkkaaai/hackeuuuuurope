"""The Doer — executes Pipeline JSON as a parallel DAG.

Uses graphlib.TopologicalSorter for dependency ordering and
asyncio.gather for parallel execution of independent nodes.
"""

import asyncio
from graphlib import TopologicalSorter
from typing import Any

from engine.executor import execute_block
from engine.memory import load_memory, save_memory


async def run_pipeline(pipeline: dict, user_id: str) -> dict[str, Any]:
    """Execute a pipeline JSON — the core Doer.

    1. Build dependency graph from edges
    2. Load user memory
    3. Execute nodes in topological order, running independent nodes in parallel
    4. Save memory
    5. Return full state with results and log

    Args:
        pipeline: Pipeline JSON with "nodes" and "edges"
        user_id: The user running this pipeline

    Returns:
        {"pipeline_id": ..., "results": {...}, "log": [...]}
    """
    nodes_by_id = {n["id"]: n for n in pipeline["nodes"]}
    pipeline_id = pipeline.get("id", "unknown")

    # Build dependency graph: {node_id: set(dependency_ids)}
    graph: dict[str, set[str]] = {n["id"]: set() for n in pipeline["nodes"]}
    for edge in pipeline.get("edges", []):
        graph[edge["to"]].add(edge["from"])

    # Load memory
    user, memory = await load_memory(user_id)

    state: dict[str, Any] = {
        "user_id": user_id,
        "pipeline_id": pipeline_id,
        "results": {},
        "user": user,
        "memory": memory,
        "log": [{"step": "_load_memory", "user_id": user_id}],
    }

    # Execute in topological order with parallel batching
    sorter = TopologicalSorter(graph)
    sorter.prepare()

    while sorter.is_active():
        ready = sorter.get_ready()
        if not ready:
            break

        # Run all ready nodes concurrently
        tasks = [
            _execute_node(node_id, nodes_by_id[node_id], state)
            for node_id in ready
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        for node_id, result in zip(ready, results):
            if isinstance(result, Exception):
                state["results"][node_id] = {"error": str(result)}
                state["log"].append({
                    "node": node_id,
                    "block": nodes_by_id[node_id].get("block_id"),
                    "error": str(result),
                })
            else:
                state["results"][node_id] = result
                state["log"].append({
                    "node": node_id,
                    "block": nodes_by_id[node_id].get("block_id"),
                    "output": result,
                })
            sorter.done(node_id)

    # Save memory
    await save_memory(user_id, state["memory"], pipeline_id, state["results"])
    state["log"].append({"step": "_save_memory", "user_id": user_id})

    return state


async def _execute_node(node_id: str, node_def: dict, state: dict) -> dict:
    """Execute a single node, passing current state for template resolution."""
    return await execute_block(node_def, state)
