"""Pipeline runner — executes compiled LangGraph pipelines."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from app.blocks.loader import load_all_implementations
from app.blocks.registry import BlockRegistry, registry as global_registry
from app.database import get_db
from app.engine.graph_builder import build_graph
from app.memory.store import MemoryStore, memory_store
from app.models.execution import ExecutionResult, ExecutionStatus
from app.models.pipeline import Pipeline

logger = logging.getLogger("agentflow.runner")

# Ensure implementations are loaded
_loaded = False


def _ensure_loaded():
    global _loaded
    if not _loaded:
        load_all_implementations()
        global_registry.load_from_directory()
        _loaded = True


class PipelineRunner:
    def __init__(
        self,
        registry: BlockRegistry | None = None,
        memory: MemoryStore | None = None,
    ):
        _ensure_loaded()
        self.registry = registry or global_registry
        self.memory = memory or memory_store

    async def run(
        self,
        pipeline: Pipeline,
        trigger_data: dict[str, Any] | None = None,
        broadcast_updates: bool = True,
    ) -> ExecutionResult:
        """Execute a pipeline end-to-end.

        If broadcast_updates is True, sends real-time node progress over WebSocket.
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        logger.info("Starting pipeline %s (run: %s)", pipeline.id, run_id)

        # Load memory keys
        loaded_memory = {}
        for key in pipeline.memory_keys:
            value = self.memory.read(key)
            if value is not None:
                loaded_memory[key] = value

        # Build and compile the graph
        try:
            compiled = build_graph(pipeline, self.registry)
        except Exception as e:
            logger.error("Failed to build graph: %s", e)
            return ExecutionResult(
                pipeline_id=pipeline.id,
                run_id=run_id,
                status=ExecutionStatus.FAILED,
                errors=[f"Graph build failed: {e}"],
            )

        # Initial state
        initial_state = {
            "shared_context": {},
            "execution_log": [],
            "errors": [],
            "memory": loaded_memory,
            "pipeline_def": pipeline.model_dump(),
            "trigger_data": trigger_data or {},
            "checkpoint": (trigger_data or {}).get("checkpoint", {}),
        }

        # Broadcast run_start (to both run_id and pipeline_id channels
        # so clients can subscribe before knowing the run_id)
        if broadcast_updates:
            start_msg = {
                "type": "run_start",
                "run_id": run_id,
                "pipeline_id": pipeline.id,
                "node_count": len(pipeline.nodes),
            }
            await self._broadcast(run_id, start_msg)
            await self._broadcast(pipeline.id, start_msg)

        # Execute using astream for real-time node updates
        # Accumulate results ourselves since astream yields per-node dicts
        seen_nodes: set[str] = set()
        shared_context: dict[str, Any] = {}
        execution_log: list[str] = []
        errors: list[str] = []

        try:
            async for state_update in compiled.astream(initial_state):
                # astream yields {node_name: {shared_context: ..., execution_log: ..., ...}}
                for value in state_update.values():
                    if not isinstance(value, dict):
                        continue
                    if "shared_context" in value:
                        shared_context.update(value["shared_context"])
                    if "execution_log" in value:
                        execution_log.extend(value["execution_log"])
                    if "errors" in value:
                        errors.extend(value["errors"])

                # Broadcast newly completed nodes
                if broadcast_updates:
                    for node_id in execution_log:
                        if node_id not in seen_nodes:
                            seen_nodes.add(node_id)
                            node_msg = {
                                "type": "node_complete",
                                "node_id": node_id,
                                "run_id": run_id,
                            }
                            await self._broadcast(run_id, node_msg)
                            await self._broadcast(pipeline.id, node_msg)
        except Exception as e:
            logger.error("Pipeline execution failed: %s", e)
            if broadcast_updates:
                await self._broadcast(run_id, {
                    "type": "run_error",
                    "run_id": run_id,
                    "error": str(e),
                })
            return ExecutionResult(
                pipeline_id=pipeline.id,
                run_id=run_id,
                status=ExecutionStatus.FAILED,
                errors=[str(e)],
            )

        status = ExecutionStatus.FAILED if errors else ExecutionStatus.COMPLETED

        logger.info(
            "Pipeline %s finished: %s (%d nodes executed)",
            pipeline.id,
            status.value,
            len(execution_log),
        )

        # Broadcast run_complete
        if broadcast_updates:
            complete_msg = {
                "type": "run_complete",
                "run_id": run_id,
                "status": status.value,
                "node_count": len(execution_log),
            }
            await self._broadcast(run_id, complete_msg)
            await self._broadcast(pipeline.id, complete_msg)

        # Persist node-level results to execution_logs table
        try:
            with get_db() as conn:
                for node_id in execution_log:
                    output = shared_context.get(node_id, {})
                    error_prefix = f"{node_id}: "
                    node_has_error = any(e.startswith(error_prefix) for e in errors)
                    node_status = "failed" if node_has_error else "completed"
                    error_msg = next(
                        (e for e in errors if e.startswith(error_prefix)), None
                    ) if node_has_error else None
                    conn.execute(
                        """INSERT INTO execution_logs
                           (pipeline_id, run_id, node_id, status, output_data, error, finished_at)
                           VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
                        (
                            pipeline.id,
                            run_id,
                            node_id,
                            node_status,
                            json.dumps(output),
                            error_msg,
                        ),
                    )
                conn.commit()
        except Exception as e:
            logger.warning("Failed to persist execution logs: %s", e)

        return ExecutionResult(
            pipeline_id=pipeline.id,
            run_id=run_id,
            status=status,
            shared_context=shared_context,
            errors=errors,
        )

    async def _broadcast(self, run_id: str, data: dict[str, Any]) -> None:
        """Send a WebSocket message. Silently skips if no subscribers."""
        try:
            from app.api.websocket import connection_manager
            await connection_manager.broadcast(run_id, data)
        except Exception:
            logger.debug("WebSocket broadcast skipped for run %s", run_id, exc_info=True)
