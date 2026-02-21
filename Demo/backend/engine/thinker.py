"""The Thinker — takes user intent, produces Pipeline JSON.

Pipeline: decompose → search → create (if missing) → wire

Each stage has a strict JSON schema (see engine/schemas.py).
Validation happens at every boundary so malformed data fails fast.
"""

import json
import logging

from engine.schemas import validate_stage_output
from engine.state import ThinkerState
from llm.service import call_llm, parse_json_output
from registry.registry import registry

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Prompt builders (shared with thinker_stream)
# ─────────────────────────────────────────────


def _build_block_catalog(blocks: list[dict]) -> str:
    """Build a rich block catalog string including use_when, tags, and one example per block."""
    entries = []
    for b in blocks:
        entry = {
            "id": b["id"],
            "name": b["name"],
            "description": b["description"],
            "input_schema": b.get("input_schema", {}),
            "output_schema": b.get("output_schema", {}),
        }
        if b.get("use_when"):
            entry["use_when"] = b["use_when"]
        if b.get("tags"):
            entry["tags"] = b["tags"]
        examples = b.get("examples", [])
        if examples:
            entry["example"] = examples[0]
        entries.append(entry)
    return json.dumps(entries, indent=2)


def build_decompose_prompts(intent: str) -> tuple[str, str]:
    """Build decompose prompts using example blocks only — no full catalog.

    The LLM freely decides what blocks are needed based on the intent.
    A search step will later find existing matches in the registry.
    """
    system = """You are a task decomposer for AgentFlow, an AI agent platform.
Break the user's intent into atomic blocks.

A block is a unit of work defined by its inputs and outputs:
- **python** blocks: run Python code (good for API calls, calculations, data transforms, web scraping)
- **llm** blocks: send a prompt template to an LLM (good for analysis, generation, summarization, knowledge)

## Example blocks (for format reference only)
- web_search (python): Search the web. Inputs: {query: string}. Outputs: {results: array}
- web_scrape (python): Fetch URL content. Inputs: {url: string}. Outputs: {content: string}
- summarize (llm): Summarize text. Inputs: {content: string}. Outputs: {summary: string}

## Rules
1. Each block does ONE atomic thing
2. List blocks in execution order
3. Think about data flow: what each block needs as input, what it outputs
4. Use "python" for API calls, calculations, sorting, ranking, data transforms, web scraping
5. Use "llm" for knowledge, analysis, text generation, summarization
6. Make blocks generic and reusable (e.g. "extract_fields" not "extract_airpods_price")

## Output
Return ONLY a JSON object (no markdown, no explanation):
{"required_blocks": [
  {"suggested_id": "...", "description": "...", "execution_type": "llm|python",
   "input_schema": {"type": "object", "properties": {...}, "required": [...]},
   "output_schema": {"type": "object", "properties": {...}}}
]}"""

    user = f'User intent: "{intent}"'
    return system, user


def build_create_block_prompt(spec: dict) -> tuple[str, str]:
    exec_type = spec.get("execution_type", "llm")

    reuse_rules = """
## REUSABILITY RULES (CRITICAL)
- The block MUST be generic and reusable, not task-specific. Name it for the general capability, not the specific use case.
- Every property in input_schema and output_schema MUST have a "description" field explaining what it is.
- output_schema MUST have a "required" array listing mandatory output fields.
- You MUST include "use_when" (string) — guidance on when to use this block.
- You MUST include "tags" (list of strings) — semantic keywords for discovery.
- You MUST include "examples" (list) — at least one sample input/output pair.
"""

    if exec_type in ("code", "python"):
        system = f"""You are a block creator for AgentFlow. Create a complete PYTHON block definition.

A python block has a `source_code` field containing a Python module with an `async def execute(inputs, context) -> dict` function.
- `inputs` is a dict with keys matching the input_schema properties.
- `context` has `user`, `memory`, `user_id`, and `supabase` sub-keys.
- The function must return a dict matching the output_schema.
- Available modules in exec namespace: json, math, statistics, collections, itertools, functools, re, datetime, random, os (for env vars), httpx.
{reuse_rules}
Return ONLY a JSON object (no markdown, no explanation).
The JSON must include a "source_code" field containing the complete Python module source code."""

        user = f"""Create a python block for:
- ID: {spec.get('suggested_id', 'new_block')}
- Description: {spec.get('description', 'No description')}
- Input schema: {json.dumps(spec.get('input_schema', {}))}
- Output schema: {json.dumps(spec.get('output_schema', {}))}

Return:
{{
  "id": "{spec.get('suggested_id', 'new_block')}",
  "name": "Human Readable Name",
  "description": "...",
  "category": "process",
  "execution_type": "python",
  "input_schema": {json.dumps(spec.get('input_schema', {}))},
  "output_schema": {json.dumps(spec.get('output_schema', {}))},
  "source_code": "\\\"\\\"\\\"Docstring.\\\"\\\"\\\"\\n\\nasync def execute(inputs: dict, context: dict) -> dict:\\n    ...\\n    return {{...}}\\n",
  "use_when": "When to use this block",
  "tags": ["tag1", "tag2"],
  "examples": [{{"inputs": {{...}}, "outputs": {{...}}}}],
  "metadata": {{"created_by": "thinker", "tier": 2}}
}}"""
    else:
        system = f"""You are a block creator for AgentFlow. Create a complete LLM block definition.

An LLM block has a prompt_template with {{placeholder}} syntax matching its input_schema property names.
When executed, the template is filled with actual values and sent to an LLM which returns JSON matching the output_schema.

IMPORTANT: The prompt_template uses simple {{key}} substitution. Only use {{input_name}} placeholders where input_name matches a property in input_schema. Do NOT use nested braces, ICU MessageFormat, or conditional syntax like {{key, select, ...}}. Keep templates as plain text with simple {{key}} placeholders.
{reuse_rules}
Return ONLY a JSON object (no markdown, no explanation)."""

        user = f"""Create a block for:
- ID: {spec.get('suggested_id', 'new_block')}
- Description: {spec.get('description', 'No description')}
- Input schema: {json.dumps(spec.get('input_schema', {}))}
- Output schema: {json.dumps(spec.get('output_schema', {}))}

Return:
{{
  "id": "{spec.get('suggested_id', 'new_block')}",
  "name": "Human Readable Name",
  "description": "...",
  "category": "process",
  "execution_type": "llm",
  "input_schema": {json.dumps(spec.get('input_schema', {}))},
  "output_schema": {json.dumps(spec.get('output_schema', {}))},
  "prompt_template": "... with {{input_name}} placeholders matching input_schema properties ...",
  "use_when": "When to use this block",
  "tags": ["tag1", "tag2"],
  "examples": [{{"inputs": {{...}}, "outputs": {{...}}}}],
  "metadata": {{"created_by": "thinker", "tier": 2}}
}}"""
    return system, user


def build_wire_prompts(intent: str, blocks: list[dict]) -> tuple[str, str]:
    blocks_detail = _build_block_catalog(blocks)

    system = f"""You are a pipeline wirer for AgentFlow. Connect blocks into an executable Pipeline JSON.

## Wiring Rules
- Node IDs are sequential: n1, n2, n3...
- First node gets LITERAL input values derived from the user's intent.
- Later nodes reference earlier outputs with {{{{nX.field_name}}}} syntax.
  The field_name must come from the output_schema of node nX.
- Edges define execution dependencies: {{"from": "n1", "to": "n2"}} means n2 runs after n1.
- A node can depend on multiple previous nodes.

## Blocks (in suggested order)
{blocks_detail}

## Output
Return ONLY a JSON object (no markdown, no explanation)."""

    user = f"""User intent: "{intent}"

Wire the blocks above into a pipeline. Return:
{{
  "id": "pipeline_<short_snake_case_name>",
  "name": "Human Readable Name",
  "user_prompt": "{intent}",
  "nodes": [
    {{"id": "n1", "block_id": "...", "inputs": {{...}}}},
    ...
  ],
  "edges": [{{"from": "n1", "to": "n2"}}, ...],
  "memory_keys": []
}}"""
    return system, user


# ─────────────────────────────────────────────
# Shared helper: finalize a created block
# ─────────────────────────────────────────────


def _finalize_created_block(parsed: dict, spec: dict) -> dict:
    """Finalize a block created by the LLM.

    For python blocks: validates source_code via compile(), stores it on the block dict.
    No filesystem operations — everything goes to Supabase via registry.save().
    """
    block_id = parsed.get("id", spec.get("suggested_id", "new_block"))
    parsed.setdefault("id", block_id)
    parsed.setdefault("name", block_id.replace("_", " ").title())
    parsed.setdefault("description", spec.get("description", ""))
    parsed.setdefault("category", spec.get("category", "process"))
    parsed.setdefault("execution_type", spec.get("execution_type", "llm"))
    parsed.setdefault("input_schema", spec.get("input_schema", {}))
    parsed.setdefault("output_schema", spec.get("output_schema", {}))
    parsed.setdefault("metadata", {"created_by": "thinker", "tier": 2})
    parsed.setdefault("use_when", None)
    parsed.setdefault("tags", [])
    parsed.setdefault("examples", [])

    # Handle python_source → source_code (normalize field name)
    python_source = parsed.pop("python_source", None)
    if python_source:
        parsed["source_code"] = python_source
        parsed["execution_type"] = "python"

    # Validate source_code compiles
    source_code = parsed.get("source_code")
    if source_code:
        try:
            compile(source_code, f"<block:{block_id}>", "exec")
            logger.info("Block %s: source_code validated via compile()", block_id)
        except SyntaxError as exc:
            logger.warning(
                "Block %s: source_code failed compile() (%s), falling back to llm type",
                block_id, exc,
            )
            parsed.pop("source_code", None)
            parsed["execution_type"] = "llm"

    return parsed


# ─────────────────────────────────────────────
# Stage 1: DECOMPOSE
# ─────────────────────────────────────────────


async def decompose_intent(state: ThinkerState) -> ThinkerState:
    """Decompose user intent into a list of required blocks using LLM."""
    system, user = build_decompose_prompts(state["user_intent"])
    response = await call_llm(system=system, user=user)
    parsed = parse_json_output(response)
    required_blocks = parsed.get("required_blocks", [])

    return {
        **state,
        "required_blocks": required_blocks,
        "status": "searching",
        "log": state["log"] + [{"step": "decompose", "required_blocks": required_blocks}],
    }


# ─────────────────────────────────────────────
# Stage 2: SEARCH (hybrid search, no LLM needed)
# ─────────────────────────────────────────────


def _is_good_match(candidate: dict, req: dict) -> bool:
    """Check if a search candidate is a good match for the required block.

    Compares description keywords and IO schema overlap.
    """
    # Compare execution type if specified
    req_exec = req.get("execution_type")
    if req_exec and candidate.get("execution_type") != req_exec:
        return False

    # Check description keyword overlap
    req_desc = (req.get("description", "") + " " + req.get("suggested_id", "")).lower()
    cand_desc = (candidate.get("description", "") + " " + candidate.get("id", "")).lower()
    req_words = set(req_desc.replace("_", " ").split())
    cand_words = set(cand_desc.replace("_", " ").split())
    # Remove common stop words
    stop = {"a", "an", "the", "to", "of", "for", "and", "or", "in", "on", "is", "it", "that", "with"}
    req_words -= stop
    cand_words -= stop
    if req_words and cand_words:
        overlap = len(req_words & cand_words) / len(req_words)
        if overlap >= 0.3:
            return True

    # Check IO schema overlap (property names)
    req_inputs = set(req.get("input_schema", {}).get("properties", {}).keys())
    cand_inputs = set(candidate.get("input_schema", {}).get("properties", {}).keys())
    req_outputs = set(req.get("output_schema", {}).get("properties", {}).keys())
    cand_outputs = set(candidate.get("output_schema", {}).get("properties", {}).keys())

    if req_inputs and cand_inputs and req_inputs & cand_inputs:
        return True
    if req_outputs and cand_outputs and req_outputs & cand_outputs:
        return True

    return False


async def search_blocks(state: ThinkerState) -> ThinkerState:
    """Search registry for each required block using hybrid search."""
    matched = []
    missing = []

    for req in state["required_blocks"]:
        # Build search query from the block's description + suggested_id
        query_parts = []
        if req.get("suggested_id"):
            query_parts.append(req["suggested_id"].replace("_", " "))
        if req.get("description"):
            query_parts.append(req["description"])
        query = " ".join(query_parts) or req.get("block_id", "block")

        # Hybrid search in Supabase
        candidates = await registry.search(query, limit=3)

        # Find the best match
        found = False
        for candidate in candidates:
            if _is_good_match(candidate, req):
                matched.append(candidate)
                logger.info("Search found block '%s' for requirement '%s'",
                            candidate["id"], req.get("suggested_id", req.get("block_id", "?")))
                found = True
                break

        if not found:
            missing.append(req)
            logger.info("Search found no match for requirement '%s'",
                        req.get("suggested_id", req.get("block_id", "?")))

    has_missing = len(missing) > 0

    return {
        **state,
        "matched_blocks": matched,
        "missing_blocks": missing,
        "status": "creating" if has_missing else "wiring",
        "error": None,
        "log": state["log"] + [{
            "step": "search",
            "matched": [b["id"] for b in matched],
            "missing": [m.get("suggested_id") or m.get("block_id", "?") for m in missing],
        }],
    }


# ─────────────────────────────────────────────
# Stage 3: CREATE BLOCK
# ─────────────────────────────────────────────


async def create_block(state: ThinkerState) -> ThinkerState:
    """Create missing block definitions using LLM and register them."""
    created = []

    for spec in state["missing_blocks"]:
        system, user = build_create_block_prompt(spec)
        response = await call_llm(system=system, user=user)
        parsed = parse_json_output(response)

        parsed = _finalize_created_block(parsed, spec)
        logger.info("Block '%s' created and verified (type=%s)", parsed["id"], parsed["execution_type"])

        await registry.save(parsed)
        created.append(parsed)

    return {
        **state,
        "matched_blocks": state["matched_blocks"] + created,
        "missing_blocks": [],
        "status": "wiring",
        "log": state["log"] + [{"step": "create", "created": [b["id"] for b in created]}],
    }


# ─────────────────────────────────────────────
# Stage 4: WIRE PIPELINE
# ─────────────────────────────────────────────


async def wire_pipeline(state: ThinkerState) -> ThinkerState:
    """Wire matched blocks into Pipeline JSON using LLM."""
    system, user = build_wire_prompts(state["user_intent"], state["matched_blocks"])
    response = await call_llm(system=system, user=user)
    parsed = parse_json_output(response)

    # Ensure required fields
    parsed.setdefault("id", "pipeline_generated")
    parsed.setdefault("name", "Generated Pipeline")
    parsed.setdefault("user_prompt", state["user_intent"])
    parsed.setdefault("nodes", [])
    parsed.setdefault("edges", [])
    parsed.setdefault("memory_keys", [])

    return {
        **state,
        "pipeline_json": parsed,
        "status": "done",
        "log": state["log"] + [{"step": "wire", "pipeline_id": parsed.get("id")}],
    }


# ─────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────


async def run_thinker(intent: str, user_id: str) -> ThinkerState:
    """Run the full Thinker pipeline: decompose → search → create → wire."""
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

    # Step 1: Decompose
    state = await decompose_intent(state)
    validate_stage_output("decompose", {"required_blocks": state["required_blocks"]})

    # Step 2: Search
    state = await search_blocks(state)

    # Step 3: Create missing blocks (if any)
    if state["status"] == "creating" and state["missing_blocks"]:
        state = await create_block(state)
        if state["missing_blocks"]:
            state["status"] = "error"
            state["error"] = f"Still missing after creation: {state['missing_blocks']}"
            return state

    # Step 4: Wire
    if state["status"] == "wiring":
        state = await wire_pipeline(state)
        if state.get("pipeline_json"):
            validate_stage_output("wire", {"pipeline_json": state["pipeline_json"]})

    return state
