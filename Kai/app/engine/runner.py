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
    ) -> ExecutionResult:
        """Execute a pipeline end-to-end."""
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
        }

        # Execute
        try:
            final_state = await compiled.ainvoke(initial_state)
        except Exception as e:
            logger.error("Pipeline execution failed: %s", e)
            return ExecutionResult(
                pipeline_id=pipeline.id,
                run_id=run_id,
                status=ExecutionStatus.FAILED,
                errors=[str(e)],
            )

        errors = final_state.get("errors", [])
        status = ExecutionStatus.FAILED if errors else ExecutionStatus.COMPLETED

        logger.info(
            "Pipeline %s finished: %s (%d nodes executed)",
            pipeline.id,
            status.value,
            len(final_state.get("execution_log", [])),
        )

        # Persist node-level results to execution_logs table
        try:
            execution_log = final_state.get("execution_log", [])
            shared_context = final_state.get("shared_context", {})
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
            shared_context=final_state.get("shared_context", {}),
            errors=errors,
        )
