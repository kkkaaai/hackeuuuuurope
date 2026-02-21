"""AgentFlow Engine — FastAPI app."""

from pathlib import Path

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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
async def list_blocks(origin: Optional[str] = Query(None, description="Filter by origin: 'system' or 'custom'")):
    if origin == "system":
        return registry.list_system()
    elif origin == "custom":
        return registry.list_custom()
    return registry.list_all()


@app.get("/api/blocks/{block_id}")
async def get_block(block_id: str):
    try:
        return registry.get(block_id)
    except KeyError:
        raise HTTPException(404, f"Block not found: {block_id}")


@app.get("/api/blocks/{block_id}/source")
async def get_block_source(block_id: str):
    """Return the Python source code for a block's entrypoint."""
    try:
        block_def = registry.get(block_id)
    except KeyError:
        raise HTTPException(404, f"Block not found: {block_id}")

    entrypoint = block_def.get("execution", {}).get("entrypoint")
    if not entrypoint:
        raise HTTPException(404, f"Block {block_id} has no Python entrypoint")

    source_path = Path(__file__).parent / entrypoint
    if not source_path.exists():
        raise HTTPException(404, f"Source file not found: {entrypoint}")

    return {"source": source_path.read_text()}


@app.post("/api/blocks")
async def create_block_endpoint(block: dict):
    registry.save(block)
    return {"status": "created", "block_id": block["id"]}


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
