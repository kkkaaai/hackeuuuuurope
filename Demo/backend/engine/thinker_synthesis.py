"""The Thinker (Synthesis Edition) — takes user intent, produces Pipeline JSON via SSE stream.

Pipeline: decompose → search → create (via Docker-sandboxed synthesis) → wire

This version replaces the one-shot LLM block generation with iterative
Docker-sandboxed synthesis from block_synthesis/. Benefits:
- Full container isolation vs Python exec() namespace
- Dynamic pip install support
- Output validation against expected results
- Up to 6 repair iterations (vs 3)

Yields SSE events between each LLM call so the frontend can show live
progress. Shared helpers (prompts, block finalization, testing) live in
thinker.py.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import AsyncGenerator

from engine.schemas import validate_stage_output
from engine.state import ThinkerState
from engine.thinker import (
    _is_good_match,
    _generate_test_inputs,
    build_decompose_prompts,
    build_wire_prompts,
)
from llm.service import call_llm, parse_json_output
from registry.registry import registry

# Add block_synthesis to path
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from block_synthesis import (
    BlockRequest,
    BlockSynthesizer,
    BlockValidator,
    MaxIterationsError,
    Orchestrator,
    SandboxManager,
)


def _event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    payload = json.dumps({"type": event_type, "ts": time.time(), **data})
    return f"event: {event_type}\ndata: {payload}\n\n"


def _generate_expected_output(schema: dict) -> dict:
    """Generate expected output structure from output schema."""
    properties = schema.get("properties", {})
    output = {}
    for key, prop in properties.items():
        prop_type = prop.get("type", "string")
        if prop_type == "string":
            output[key] = ""
        elif prop_type == "number":
            output[key] = 0.0
        elif prop_type == "integer":
            output[key] = 0
        elif prop_type == "boolean":
            output[key] = True
        elif prop_type == "array":
            output[key] = []
        elif prop_type == "object":
            output[key] = {}
        else:
            output[key] = ""
    return output


async def run_thinker_stream(
    intent: str,
    user_id: str,
    provider: str = "openai",
    model: str = "gpt-4o",
    max_iterations: int = 6,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE events for each Thinker stage.
    
    Uses Docker-sandboxed block synthesis for the CREATE stage.
    """

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

    system, user = build_decompose_prompts(intent)

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
        "status": "searching",
        "log": state["log"] + [{"step": "decompose", "required_blocks": required_blocks}],
    }

    yield _event("stage_result", {
        "stage": "decompose",
        "status": "done",
        "required_blocks": required_blocks,
        "count": len(required_blocks),
    })
    await asyncio.sleep(0)

    # Emit decompose_blocks summary for the UI
    yield _event("decompose_blocks", {
        "blocks": [
            {"suggested_id": b.get("suggested_id", "?"),
             "description": b.get("description", ""),
             "execution_type": b.get("execution_type", "python")}
            for b in required_blocks
        ]
    })
    await asyncio.sleep(0)

    try:
        validate_stage_output("decompose", {"required_blocks": required_blocks})
        yield _event("validation", {"stage": "decompose", "valid": True})
    except Exception as e:
        yield _event("validation", {"stage": "decompose", "valid": False, "error": str(e)})
    await asyncio.sleep(0)

    # ── Stage 2: SEARCH ──
    yield _event("stage", {"stage": "search", "status": "running",
                           "message": "Searching registry for matching blocks..."})
    await asyncio.sleep(0)

    matched = []
    missing = []
    for req in state["required_blocks"]:
        description = req.get("description", "")
        suggested_id = req.get("suggested_id", req.get("block_id", "?"))

        # Search by description only — compare desired functionality to existing
        query = description or suggested_id.replace("_", " ")

        # Hybrid search in Supabase
        candidates = await registry.search(
            query,
            limit=5,
            input_schema=req.get("input_schema"),
            output_schema=req.get("output_schema"),
        )

        # Find the best match
        found = False
        for candidate in candidates:
            if _is_good_match(candidate, req):
                matched.append(candidate)
                yield _event("search_found", {
                    "suggested_id": suggested_id,
                    "matched_block_id": candidate["id"],
                    "name": candidate["name"],
                    "description": candidate.get("description", description),
                    "block_def": candidate,
                })
                found = True
                break

        if not found:
            missing.append(req)
            yield _event("search_missing", {
                "suggested_id": suggested_id,
                "description": description or "new block",
                "candidates_checked": len(candidates),
            })
        await asyncio.sleep(0)

    state = {
        **state,
        "matched_blocks": matched,
        "missing_blocks": missing,
        "status": "creating" if missing else "wiring",
        "log": state["log"] + [{
            "step": "search",
            "matched": [b["id"] for b in matched],
            "missing": [m.get("suggested_id") or m.get("block_id", "?") for m in missing],
        }],
    }

    yield _event("stage_result", {
        "stage": "search",
        "status": "done",
        "matched": len(matched),
        "missing": len(missing),
        "next": "create" if missing else "wire",
    })
    await asyncio.sleep(0)

    # ── Stage 3: CREATE (via Docker-sandboxed synthesis) ──
    if not state["missing_blocks"]:
        yield _event("stage", {"stage": "create", "status": "skipped",
                                "message": "All blocks found in registry — skipping create."})
        await asyncio.sleep(0)
        yield _event("stage_result", {"stage": "create", "status": "skipped"})
        await asyncio.sleep(0)

    if state["status"] == "creating" and state["missing_blocks"]:
        yield _event("stage", {"stage": "create", "status": "running",
                               "message": f"Creating {len(missing)} new block(s) via Docker synthesis..."})
        await asyncio.sleep(0)

        created = []
        creation_failures = []
        
        for i, spec in enumerate(state["missing_blocks"]):
            block_name = spec.get("suggested_id", f"block_{i}")
            description = spec.get("description", "")
            input_schema = spec.get("input_schema", {})
            output_schema = spec.get("output_schema", {})
            
            yield _event("creating_block", {
                "index": i,
                "total": len(state["missing_blocks"]),
                "suggested_id": block_name,
                "description": description,
                "method": "docker_synthesis",
            })
            await asyncio.sleep(0)

            # Convert spec to BlockRequest for synthesis
            test_input = _generate_test_inputs(input_schema)
            expected_output = _generate_expected_output(output_schema)
            
            # Build purpose string with schema details
            purpose = description
            if input_schema.get("properties"):
                purpose += "\n\nInput specifications:"
                for k, v in input_schema.get("properties", {}).items():
                    purpose += f"\n- {k} ({v.get('type', 'any')}): {v.get('description', '')}"
            if output_schema.get("properties"):
                purpose += "\n\nOutput specifications:"
                for k, v in output_schema.get("properties", {}).items():
                    purpose += f"\n- {k} ({v.get('type', 'any')}): {v.get('description', '')}"
            
            request = BlockRequest(
                inputs=list(input_schema.get("properties", {}).keys()),
                outputs=list(output_schema.get("properties", {}).keys()),
                purpose=purpose,
                test_input=test_input,
                expected_output=expected_output,
            )
            
            yield _event("synthesis_request", {
                "block_id": block_name,
                "inputs": request.inputs,
                "outputs": request.outputs,
                "test_input": test_input,
            })
            await asyncio.sleep(0)

            # Run Docker-sandboxed synthesis
            t0 = time.time()
            try:
                synthesizer = BlockSynthesizer(provider=provider, model=model)
                sandbox = SandboxManager(backend="docker", allow_pip_install=True)
                validator = BlockValidator()
                
                orchestrator = Orchestrator(
                    synthesizer=synthesizer,
                    sandbox=sandbox,
                    validator=validator,
                    max_iterations=max_iterations,
                )
                
                source_code = await orchestrator.run(request)
                elapsed = round(time.time() - t0, 2)
                
                yield _event("synthesis_success", {
                    "block_id": block_name,
                    "elapsed_s": elapsed,
                    "iterations": "unknown",  # Orchestrator doesn't expose this currently
                })
                await asyncio.sleep(0)
                
                # Build block definition
                block_def = {
                    "id": block_name,
                    "name": block_name.replace("_", " ").title(),
                    "description": description,
                    "category": "process",
                    "execution_type": "python",
                    "input_schema": input_schema,
                    "output_schema": output_schema,
                    "source_code": source_code,
                    "use_when": f"When you need to {description.lower()}",
                    "tags": [],
                    "examples": [{"inputs": test_input, "outputs": expected_output}],
                    "metadata": {"created_by": "thinker_synthesis", "tier": 2},
                }
                
                yield _event("block_created", {
                    "block_id": block_name,
                    "name": block_def["name"],
                    "description": description,
                    "execution_type": "python",
                    "has_source_code": True,
                    "block_def": block_def,
                })
                await asyncio.sleep(0)
                
                yield _event("block_test_passed", {"block_id": block_name})
                await asyncio.sleep(0)
                
                await registry.save(block_def)
                created.append(block_def)
                
            except MaxIterationsError as e:
                elapsed = round(time.time() - t0, 2)
                error_msg = str(e)
                
                yield _event("synthesis_failed", {
                    "block_id": block_name,
                    "error": error_msg,
                    "elapsed_s": elapsed,
                })
                await asyncio.sleep(0)
                
                yield _event("block_create_failed", {
                    "block_id": block_name,
                    "error": error_msg,
                    "message": f"Docker synthesis failed after {max_iterations} iterations.",
                })
                await asyncio.sleep(0)
                
                creation_failures.append(block_name)
                
            except Exception as e:
                elapsed = round(time.time() - t0, 2)
                error_msg = str(e)
                
                yield _event("synthesis_error", {
                    "block_id": block_name,
                    "error": error_msg,
                    "elapsed_s": elapsed,
                })
                await asyncio.sleep(0)
                
                yield _event("block_create_failed", {
                    "block_id": block_name,
                    "error": error_msg,
                    "message": "Docker synthesis encountered an unexpected error.",
                })
                await asyncio.sleep(0)
                
                creation_failures.append(block_name)

        state = {
            **state,
            "matched_blocks": state["matched_blocks"] + created,
            "missing_blocks": [],
            "status": "wiring",
            "log": state["log"] + [{
                "step": "create",
                "method": "docker_synthesis",
                "created": [b["id"] for b in created],
                "failed": creation_failures,
            }],
        }

        yield _event("stage_result", {
            "stage": "create",
            "status": "done",
            "method": "docker_synthesis",
            "created": [b["id"] for b in created],
            "failed": creation_failures,
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


async def run_thinker(
    intent: str,
    user_id: str,
    provider: str = "openai",
    model: str = "gpt-4o",
    max_iterations: int = 6,
) -> dict:
    """Run the full Thinker pipeline via the stream, return the final state.

    Consumes all SSE events and extracts the result from the 'complete' event.
    Used by non-streaming API endpoints that still need the final result.
    """
    result: dict = {"pipeline_json": None, "status": "error", "log": [], "missing_blocks": []}
    async for event_str in run_thinker_stream(intent, user_id, provider, model, max_iterations):
        # Each event_str is "event: ...\ndata: {...}\n\n"
        for line in event_str.strip().split("\n"):
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if data.get("type") == "complete":
                    result["pipeline_json"] = data.get("pipeline")
                    result["status"] = data.get("status", "done")
                    result["log"] = data.get("log", [])
    return result
