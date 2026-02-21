"""Pipeline CRUD and execution endpoints."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_registry
from app.database import get_db
from app.engine.runner import PipelineRunner
from app.memory.store import memory_store
from app.models.execution import ExecutionResult
from app.models.pipeline import Pipeline

logger = logging.getLogger("agentflow.api.pipelines")
router = APIRouter(prefix="/api", tags=["pipelines"])


class PipelineCreate(BaseModel):
    pipeline: Pipeline


class PipelineListItem(BaseModel):
    id: str
    user_intent: str
    status: str
    trigger_type: str
    node_count: int


@router.post("/pipelines")
async def create_pipeline(request: PipelineCreate) -> dict[str, str]:
    """Store a pipeline definition."""
    p = request.pipeline
    with get_db() as conn:
        conn.execute(
            "INSERT INTO pipelines (id, user_intent, definition, status) VALUES (?, ?, ?, ?)",
            (p.id, p.user_intent, p.model_dump_json(), p.status.value),
        )
        conn.commit()
    return {"id": p.id, "status": "created"}


@router.get("/pipelines", response_model=list[PipelineListItem])
async def list_pipelines() -> list[PipelineListItem]:
    """List all pipelines."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, user_intent, status, definition FROM pipelines ORDER BY created_at DESC"
        ).fetchall()

    items = []
    for row in rows:
        defn = json.loads(row["definition"])
        items.append(PipelineListItem(
            id=row["id"],
            user_intent=row["user_intent"],
            status=row["status"],
            trigger_type=defn.get("trigger", {}).get("type", "manual"),
            node_count=len(defn.get("nodes", [])),
        ))
    return items


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str) -> dict[str, Any]:
    """Get a pipeline by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM pipelines WHERE id = ?", (pipeline_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    return {
        "id": row["id"],
        "user_intent": row["user_intent"],
        "status": row["status"],
        "definition": json.loads(row["definition"]),
        "created_at": row["created_at"],
    }


@router.post("/pipelines/{pipeline_id}/run")
async def run_pipeline(pipeline_id: str) -> ExecutionResult:
    """Execute a stored pipeline."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT definition FROM pipelines WHERE id = ?", (pipeline_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    pipeline = Pipeline(**json.loads(row["definition"]))
    registry = get_registry()
    runner = PipelineRunner(registry=registry, memory=memory_store)
    result = await runner.run(pipeline)

    # Update status
    with get_db() as conn:
        conn.execute(
            "UPDATE pipelines SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (result.status.value, pipeline_id),
        )
        conn.commit()

    return result


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: str) -> dict[str, str]:
    """Delete a pipeline."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM pipelines WHERE id = ?", (pipeline_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pipeline not found")

    return {"id": pipeline_id, "status": "deleted"}
