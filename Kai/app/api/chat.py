"""POST /api/chat — Natural language -> pipeline via Orchestra Agent."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.builder import BuilderAgent
from app.agents.orchestra import OrchestraAgent
from app.api.dependencies import get_registry
from app.engine.runner import PipelineRunner
from app.memory.store import memory_store

logger = logging.getLogger("agentflow.api.chat")
router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Natural language automation request")
    auto_execute: bool = Field(default=False, description="Execute immediately without approval")


class ChatResponse(BaseModel):
    pipeline_id: str
    user_intent: str
    trigger_type: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    missing_blocks: list[dict[str, Any]]
    execution_result: dict[str, Any] | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Decompose a natural language request into a pipeline and optionally execute it."""
    registry = get_registry()
    orchestra = OrchestraAgent(registry)

    # Decompose
    try:
        decomposition = await orchestra.decompose(request.message)
    except Exception:
        logger.exception("Decomposition failed for message: %.200s", request.message)
        raise HTTPException(
            status_code=500,
            detail="Failed to decompose your request. Please try rephrasing.",
        )

    # Handle missing blocks
    missing = decomposition.get("missing_blocks", [])
    if missing:
        builder = BuilderAgent(registry)
        await builder.create_missing_blocks(missing)

    # Build pipeline
    pipeline = orchestra.build_pipeline(request.message, decomposition)

    response = ChatResponse(
        pipeline_id=pipeline.id,
        user_intent=pipeline.user_intent,
        trigger_type=pipeline.trigger.type.value,
        nodes=[n.model_dump() for n in pipeline.nodes],
        edges=[e.model_dump() for e in pipeline.edges],
        missing_blocks=missing,
    )

    # Auto-execute if requested
    if request.auto_execute:
        runner = PipelineRunner(registry=registry, memory=memory_store)
        result = await runner.run(pipeline)
        response.execution_result = result.model_dump()

    return response
