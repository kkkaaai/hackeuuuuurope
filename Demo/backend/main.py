"""AgentFlow Engine — FastAPI app."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from engine.clarifier import clarify
from engine.doer import run_pipeline
from engine.thinker import run_thinker
from engine.thinker_stream import run_thinker_stream
from registry.registry import registry
from storage.memory import memory_store

app = FastAPI(title="AgentFlow Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ──


class CreateAgentRequest(BaseModel):
    intent: str
    user_id: str


class CreateAgentResponse(BaseModel):
    pipeline_json: dict | None
    status: str
    log: list[dict]
    missing_blocks: list[dict]


class ClarifyRequest(BaseModel):
    message: str
    history: list[dict] = []


class ClarifyResponseModel(BaseModel):
    ready: bool
    refined_intent: str | None = None
    question: str | None = None


class RunPipelineRequest(BaseModel):
    pipeline: dict
    user_id: str


class RunPipelineResponse(BaseModel):
    run_id: str
    status: str
    results: dict
    log: list[dict]


# ── Health ──


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Clarify user intent (Q&A before pipeline creation) ──


@app.post("/api/clarify", response_model=ClarifyResponseModel)
async def clarify_endpoint(req: ClarifyRequest):
    """Evaluate if the user's request is specific enough for pipeline creation."""
    result = await clarify(req.message, req.history)
    return ClarifyResponseModel(
        ready=result.get("ready", True),
        refined_intent=result.get("refined_intent"),
        question=result.get("question"),
    )


# ── Create an agent (runs the Thinker) ──


@app.post("/api/create-agent", response_model=CreateAgentResponse)
async def create_agent(req: CreateAgentRequest):
    """Run the Thinker: user intent → Pipeline JSON."""
    try:
        result = await run_thinker(req.intent, req.user_id)
    except NotImplementedError as e:
        raise HTTPException(501, detail=str(e))

    return CreateAgentResponse(
        pipeline_json=result.get("pipeline_json"),
        status=result["status"],
        log=result["log"],
        missing_blocks=result.get("missing_blocks", []),
    )


# ── Streaming create agent (SSE) ──


@app.post("/api/create-agent/stream")
async def create_agent_stream(req: CreateAgentRequest):
    """Run the Thinker with SSE streaming — yields events for each stage."""
    return StreamingResponse(
        run_thinker_stream(req.intent, req.user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Run a pipeline (runs the Doer) ──


@app.post("/api/pipeline/run", response_model=RunPipelineResponse)
async def run_pipeline_endpoint(req: RunPipelineRequest):
    """Run the Doer: Pipeline JSON → execute blocks → results."""
    try:
        result = await run_pipeline(req.pipeline, req.user_id)
    except Exception as e:
        raise HTTPException(500, detail=str(e))

    return RunPipelineResponse(
        run_id=result.get("pipeline_id", "unknown"),
        status="completed",
        results=result["results"],
        log=result["log"],
    )


# ── Full flow: create + run in one call ──


@app.post("/api/automate")
async def automate(req: CreateAgentRequest):
    """Create agent (Thinker) then immediately run it (Doer)."""
    try:
        thinker_result = await run_thinker(req.intent, req.user_id)
    except NotImplementedError as e:
        raise HTTPException(501, detail=str(e))

    if thinker_result["status"] != "done" or not thinker_result.get("pipeline_json"):
        return {
            "status": "failed",
            "reason": "Could not create pipeline",
            "missing_blocks": thinker_result.get("missing_blocks", []),
            "log": thinker_result["log"],
        }

    try:
        doer_result = await run_pipeline(thinker_result["pipeline_json"], req.user_id)
    except Exception as e:
        raise HTTPException(500, detail=str(e))

    return {
        "status": "completed",
        "pipeline": thinker_result["pipeline_json"],
        "results": doer_result["results"],
        "log": thinker_result["log"] + doer_result["log"],
    }


# ── Block registry CRUD ──


@app.get("/api/blocks")
async def list_blocks():
    """List all blocks from Supabase."""
    return registry.list_all()


@app.get("/api/blocks/{block_id}")
async def get_block(block_id: str):
    try:
        return registry.get(block_id)
    except KeyError:
        raise HTTPException(404, f"Block not found: {block_id}")


@app.get("/api/blocks/{block_id}/source")
async def get_block_source(block_id: str):
    """Return the source_code or prompt_template for a block."""
    try:
        block_def = registry.get(block_id)
    except KeyError:
        raise HTTPException(404, f"Block not found: {block_id}")

    if block_def.get("source_code"):
        return {"source": block_def["source_code"], "type": "python"}
    if block_def.get("prompt_template"):
        return {"source": block_def["prompt_template"], "type": "llm"}
    raise HTTPException(404, f"Block {block_id} has no source code or prompt template")


@app.post("/api/blocks")
async def create_block_endpoint(block: dict):
    await registry.save(block)
    return {"status": "created", "block_id": block["id"]}


# ── Block Search ──


class BlockSearchRequest(BaseModel):
    query: str


@app.post("/api/blocks/search")
async def search_blocks_endpoint(req: BlockSearchRequest):
    """Hybrid search: full-text + semantic via Supabase."""
    return await registry.search(req.query)


# ── Pipeline CRUD ──


class SavePipelineRequest(BaseModel):
    pipeline: dict


@app.get("/api/pipelines")
async def list_pipelines_endpoint():
    return memory_store.list_pipelines()


@app.get("/api/pipelines/{pipeline_id}")
async def get_pipeline_endpoint(pipeline_id: str):
    data = memory_store.get_pipeline(pipeline_id)
    if not data:
        raise HTTPException(404, f"Pipeline not found: {pipeline_id}")
    return data


@app.post("/api/pipelines")
async def save_pipeline_endpoint(req: SavePipelineRequest):
    pipeline = req.pipeline
    pipeline_id = pipeline.get("id", str(uuid.uuid4()))
    pipeline["id"] = pipeline_id
    memory_store.save_pipeline(pipeline_id, pipeline)
    return {"id": pipeline_id, "status": "created"}


@app.delete("/api/pipelines/{pipeline_id}", status_code=204)
async def delete_pipeline_endpoint(pipeline_id: str):
    memory_store.delete_pipeline(pipeline_id)


@app.post("/api/pipelines/{pipeline_id}/run")
async def run_saved_pipeline_endpoint(pipeline_id: str):
    pipeline_data = memory_store.get_pipeline(pipeline_id)
    if not pipeline_data:
        raise HTTPException(404, f"Pipeline not found: {pipeline_id}")

    run_id = str(uuid.uuid4())
    try:
        result = await run_pipeline(pipeline_data, "default_user")
        status = "completed"
    except Exception as e:
        result = {"results": {}, "log": [{"error": str(e)}]}
        status = "failed"

    # Build shared_context and node_results
    results_data = result.get("results", {})
    shared_context = results_data if isinstance(results_data, dict) else {}
    node_results = []
    errors = []

    for node in pipeline_data.get("nodes", []):
        node_id = node["id"]
        node_output = shared_context.get(node_id)
        node_results.append({
            "id": len(node_results) + 1,
            "node_id": node_id,
            "status": "completed" if node_output is not None else "failed",
            "output_data": node_output,
            "error": None,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })

    execution = {
        "run_id": run_id,
        "pipeline_id": pipeline_id,
        "pipeline_intent": pipeline_data.get("user_prompt", pipeline_data.get("name", "")),
        "pipeline_name": pipeline_data.get("name", ""),
        "node_count": len(pipeline_data.get("nodes", [])),
        "status": status,
        "nodes": node_results,
        "shared_context": shared_context,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    memory_store.save_execution(run_id, execution)

    # Update pipeline status
    pipeline_data["status"] = status
    memory_store.save_pipeline(pipeline_id, pipeline_data)

    return {
        "pipeline_id": pipeline_id,
        "run_id": run_id,
        "status": status,
        "shared_context": shared_context,
        "node_results": node_results,
        "errors": errors,
    }


# ── Executions ──


@app.get("/api/executions")
async def list_executions_endpoint(limit: int = Query(50)):
    return memory_store.list_executions(limit)


@app.get("/api/executions/{run_id}")
async def get_execution_endpoint(run_id: str):
    data = memory_store.get_execution(run_id)
    if not data:
        raise HTTPException(404, f"Execution not found: {run_id}")
    return data


# ── Notifications ──


@app.get("/api/notifications")
async def list_notifications_endpoint(limit: int = Query(50)):
    return memory_store.list_notifications(limit)


@app.post("/api/notifications/{notif_id}/read")
async def mark_notification_read_endpoint(notif_id: int):
    memory_store.mark_notification_read(notif_id)
    return {"status": "ok"}


# ── Memory ──


@app.get("/api/memory/{user_id}")
async def get_memory(user_id: str):
    return memory_store.get_memory(user_id) or {}


# ── Static files (frontend) ──

static_dir = Path(__file__).parent / "static"


@app.get("/")
async def serve_frontend():
    index = static_dir / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "AgentFlow API", "docs": "/docs"}


if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
