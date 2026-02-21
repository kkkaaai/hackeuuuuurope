"""Builds a LangGraph StateGraph from a Pipeline definition."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.blocks.executor import BlockExecutor
from app.blocks.registry import BlockRegistry
from app.engine.state import PipelineState
from app.models.pipeline import Pipeline

logger = logging.getLogger("agentflow.graph_builder")


def build_graph(pipeline: Pipeline, registry: BlockRegistry) -> StateGraph:
    """Convert a Pipeline definition into a compiled LangGraph StateGraph."""
    executor = BlockExecutor()
    graph = StateGraph(PipelineState)

    # Build adjacency from edges
    adjacency: dict[str, list[str]] = {}
    incoming: dict[str, list[str]] = {}
    conditional_edges: dict[str, str] = {}  # from_node -> condition expression

    for edge in pipeline.edges:
        adjacency.setdefault(edge.from_node, []).append(edge.to_node)
        incoming.setdefault(edge.to_node, []).append(edge.from_node)
        if edge.condition:
            conditional_edges[edge.from_node] = edge.condition

    # Find start nodes (no incoming edges)
    all_node_ids = {n.id for n in pipeline.nodes}
    start_nodes = all_node_ids - set(incoming.keys())
    # Find end nodes (no outgoing edges)
    end_nodes = all_node_ids - set(adjacency.keys())

    # Create a LangGraph node function for each pipeline node
    for node in pipeline.nodes:
        block_def = registry.get(node.block_id)
        if block_def is None:
            raise ValueError(f"Block '{node.block_id}' not found in registry")

        node_fn = _make_node_function(node.id, node.block_id, node.inputs, executor, block_def)
        graph.add_node(node.id, node_fn)

    # Wire edges
    for node_id in start_nodes:
        graph.add_edge(START, node_id)

    for from_node, to_nodes in adjacency.items():
        if from_node in conditional_edges and len(to_nodes) == 2:
            # Conditional branching: route based on the branch output
            _add_conditional_edge(graph, from_node, to_nodes)
        else:
            for to_node in to_nodes:
                graph.add_edge(from_node, to_node)

    for node_id in end_nodes:
        graph.add_edge(node_id, END)

    return graph.compile()


def _make_node_function(
    node_id: str,
    block_id: str,
    input_mapping: dict[str, Any],
    executor: BlockExecutor,
    block_def: Any,
):
    """Create a closure that executes a block and updates the pipeline state."""

    async def node_fn(state: PipelineState) -> dict:
        shared_context = state.get("shared_context", {})
        memory = state.get("memory", {})
        trigger_data = state.get("trigger_data", {})
        checkpoint = state.get("checkpoint", {})
        pipeline_def = state.get("pipeline_def", {})

        # Build inputs: start with the input mapping, add trigger data for trigger blocks
        inputs = {**input_mapping}
        if block_def.category == "trigger" and trigger_data:
            inputs.update(trigger_data)

        # Inject __context for blocks that need pipeline/checkpoint info
        inputs["__context"] = {
            "checkpoint": checkpoint,
            "pipeline_id": pipeline_def.get("id", ""),
            "node_id": node_id,
        }

        result = await executor.execute(
            block=block_def,
            inputs=inputs,
            shared_context=shared_context,
            memory=memory,
            node_id=node_id,
        )

        updates: dict[str, Any] = {
            "shared_context": {node_id: result.output},
            "execution_log": [node_id],
        }

        if result.error:
            updates["errors"] = [f"{node_id}: {result.error}"]

        return updates

    return node_fn


def _add_conditional_edge(graph: StateGraph, from_node: str, to_nodes: list[str]):
    """Add a conditional edge that routes based on the 'branch' output of a node."""
    true_node = to_nodes[0]
    false_node = to_nodes[1]

    def router(state: PipelineState) -> str:
        shared_context = state.get("shared_context", {})
        node_output = shared_context.get(from_node, {})
        branch = node_output.get("branch", "false")
        return true_node if branch == "true" else false_node

    graph.add_conditional_edges(from_node, router, {true_node: true_node, false_node: false_node})
