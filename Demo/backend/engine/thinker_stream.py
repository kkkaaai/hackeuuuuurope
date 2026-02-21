"""Streaming Thinker — yields SSE events as it runs each stage.

Reuses prompt builders and logic from thinker.py but yields events
between each LLM call so the frontend can show live progress,
including the full prompts sent and raw LLM responses received.
"""

import asyncio
import json
import time
from typing import AsyncGenerator

from engine.schemas import validate_stage_output
from engine.state import ThinkerState
from engine.thinker import (
    _finalize_created_block,
    build_create_block_prompt,
    build_decompose_prompts,
    build_wire_prompts,
)
from llm.service import call_llm, parse_json_output
from registry.registry import registry


def _event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    payload = json.dumps({"type": event_type, "ts": time.time(), **data})
    return f"event: {event_type}\ndata: {payload}\n\n"


async def run_thinker_stream(intent: str, user_id: str) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE events for each Thinker stage."""

    state: ThinkerState = {
        "user_intent": intent,
        "user_id": user_id,
        "required_blocks": [],
        "matched_blocks": [],
        "missing_blocks": [],
        "pipeline_json": None,
        "status": "decomposing",
        "error": None,
        "log": [],
    }

    yield _event("start", {"intent": intent, "user_id": user_id})
    await asyncio.sleep(0)

    # ── Stage 1: DECOMPOSE ──
    yield _event("stage", {"stage": "decompose", "status": "running",
                           "message": "Breaking intent into atomic blocks..."})
    await asyncio.sleep(0)

    blocks_available = registry.list_all()
    system, user = build_decompose_prompts(intent, blocks_available)

    yield _event("llm_prompt", {"stage": "decompose", "system": system, "user": user})
    await asyncio.sleep(0)

    t0 = time.time()
    response = await call_llm(system=system, user=user)
    elapsed = round(time.time() - t0, 2)

    yield _event("llm_response", {"stage": "decompose", "raw": response, "elapsed_s": elapsed})
    await asyncio.sleep(0)

    parsed = parse_json_output(response)
    required_blocks = parsed.get("required_blocks", [])

    state = {
        **state,
        "required_blocks": required_blocks,
        "status": "matching",
        "log": state["log"] + [{"step": "decompose", "required_blocks": required_blocks}],
    }

    yield _event("stage_result", {
        "stage": "decompose",
        "status": "done",
        "required_blocks": required_blocks,
        "count": len(required_blocks),
    })
    await asyncio.sleep(0)

    try:
        validate_stage_output("decompose", {"required_blocks": required_blocks})
        yield _event("validation", {"stage": "decompose", "valid": True})
    except Exception as e:
        yield _event("validation", {"stage": "decompose", "valid": False, "error": str(e)})
    await asyncio.sleep(0)

    # ── Stage 2: MATCH ──
    yield _event("stage", {"stage": "match", "status": "running",
                           "message": "Matching blocks against registry..."})
    await asyncio.sleep(0)

    matched = []
    missing = []
    for req in state["required_blocks"]:
        block_id = req.get("block_id")
        description = req.get("description", "")
        if block_id:
            try:
                block_def = registry.get(block_id)
                matched.append(block_def)
                yield _event("match_found", {
                    "block_id": block_id,
                    "name": block_def["name"],
                    "description": block_def.get("description", description),
                    "block_def": block_def,
                })
            except KeyError:
                missing.append(req)
                yield _event("match_missing", {
                    "block_id": block_id,
                    "description": description,
                })
        else:
            missing.append(req)
            yield _event("match_missing", {
                "suggested_id": req.get("suggested_id", "?"),
                "description": description or "new block",
            })
        await asyncio.sleep(0)

    state = {
        **state,
        "matched_blocks": matched,
        "missing_blocks": missing,
        "status": "creating" if missing else "wiring",
        "log": state["log"] + [{
            "step": "match",
            "matched": [b["id"] for b in matched],
            "missing": [m.get("suggested_id") or m.get("block_id", "?") for m in missing],
        }],
    }

    yield _event("stage_result", {
        "stage": "match",
        "status": "done",
        "matched": len(matched),
        "missing": len(missing),
        "next": "create" if missing else "wire",
    })
    await asyncio.sleep(0)

    # ── Stage 3: CREATE (if needed) ──
    if not state["missing_blocks"]:
        yield _event("stage", {"stage": "create", "status": "skipped",
                                "message": "All blocks found in registry — skipping create."})
        await asyncio.sleep(0)
        yield _event("stage_result", {"stage": "create", "status": "skipped"})
        await asyncio.sleep(0)

    if state["status"] == "creating" and state["missing_blocks"]:
        yield _event("stage", {"stage": "create", "status": "running",
                               "message": f"Creating {len(missing)} new block(s)..."})
        await asyncio.sleep(0)

        created = []
        for i, spec in enumerate(state["missing_blocks"]):
            block_name = spec.get("suggested_id", f"block_{i}")
            yield _event("creating_block", {
                "index": i,
                "total": len(state["missing_blocks"]),
                "suggested_id": block_name,
                "description": spec.get("description", ""),
            })
            await asyncio.sleep(0)

            system, user = build_create_block_prompt(spec)

            yield _event("llm_prompt", {"stage": f"create:{block_name}", "system": system, "user": user})
            await asyncio.sleep(0)

            t0 = time.time()
            response = await call_llm(system=system, user=user)
            elapsed = round(time.time() - t0, 2)

            yield _event("llm_response", {"stage": f"create:{block_name}", "raw": response, "elapsed_s": elapsed})
            await asyncio.sleep(0)

            parsed = parse_json_output(response)

            parsed = _finalize_created_block(parsed, spec)
            block_id = parsed["id"]

            registry.save(parsed)
            created.append(parsed)

            yield _event("block_created", {
                "block_id": block_id,
                "name": parsed["name"],
                "description": parsed.get("description", ""),
                "execution_type": parsed["execution_type"],
                "has_prompt": bool(parsed.get("prompt_template")),
                "has_python_file": parsed.get("execution_type") == "python",
                "block_def": parsed,
            })
            await asyncio.sleep(0)

        state = {
            **state,
            "matched_blocks": state["matched_blocks"] + created,
            "missing_blocks": [],
            "status": "wiring",
            "log": state["log"] + [{"step": "create", "created": [b["id"] for b in created]}],
        }

        yield _event("stage_result", {
            "stage": "create",
            "status": "done",
            "created": [b["id"] for b in created],
        })
        await asyncio.sleep(0)

    # ── Stage 4: WIRE ──
    yield _event("stage", {"stage": "wire", "status": "running",
                           "message": "Wiring blocks into executable pipeline..."})
    await asyncio.sleep(0)

    system, user = build_wire_prompts(state["user_intent"], state["matched_blocks"])

    yield _event("llm_prompt", {"stage": "wire", "system": system, "user": user})
    await asyncio.sleep(0)

    t0 = time.time()
    response = await call_llm(system=system, user=user)
    elapsed = round(time.time() - t0, 2)

    yield _event("llm_response", {"stage": "wire", "raw": response, "elapsed_s": elapsed})
    await asyncio.sleep(0)

    parsed = parse_json_output(response)

    parsed.setdefault("id", "pipeline_generated")
    parsed.setdefault("name", "Generated Pipeline")
    parsed.setdefault("user_prompt", state["user_intent"])
    parsed.setdefault("nodes", [])
    parsed.setdefault("edges", [])
    parsed.setdefault("memory_keys", [])

    state = {
        **state,
        "pipeline_json": parsed,
        "status": "done",
        "log": state["log"] + [{"step": "wire", "pipeline_id": parsed.get("id")}],
    }

    try:
        validate_stage_output("wire", {"pipeline_json": parsed})
        yield _event("validation", {"stage": "wire", "valid": True})
    except Exception as e:
        yield _event("validation", {"stage": "wire", "valid": False, "error": str(e)})
    await asyncio.sleep(0)

    yield _event("stage_result", {
        "stage": "wire",
        "status": "done",
        "pipeline_json": parsed,
    })
    await asyncio.sleep(0)

    # ── Done ──
    yield _event("complete", {
        "status": state["status"],
        "pipeline": state["pipeline_json"],
        "log": state["log"],
    })
