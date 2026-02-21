# Agent Creation Pipeline — Implementation Spec

> This is the complete spec for building the AgentFlow backend.
> It has two LangGraphs: **the Thinker** (creates agents) and **the Doer** (runs them).
> Both are in this repo. This doc has everything a fresh Claude Code instance needs to build it.

---

## 1. The Big Picture

Users describe automations in plain English. The system creates and runs them.

```
User: "Summarize the top Hacker News posts every morning"

                         ┌─────────────────────────────────────┐
                         │                                     │
                         │    LANGGRAPH 1: THE THINKER         │
                         │    (agent creation pipeline)        │
                         │                                     │
                         │    1. Understand the goal            │
                         │    2. Decompose into steps           │
                         │    3. Find matching blocks           │
                         │    4. Wire blocks into Pipeline JSON │
                         │    5. Validate                       │
                         │                                     │
                         └──────────────┬──────────────────────┘
                                        │
                                  Pipeline JSON
                                        │
                         ┌──────────────▼──────────────────────┐
                         │                                     │
                         │    LANGGRAPH 2: THE DOER            │
                         │    (pipeline execution engine)      │
                         │                                     │
                         │    web_search → summarize → notify  │
                         │                                     │
                         └─────────────────────────────────────┘
```

**The Thinker** is an agentic loop — the LLM reasons, searches the block registry, may loop back if something is missing. It outputs Pipeline JSON.

**The Doer** is a deterministic DAG — it takes Pipeline JSON and executes blocks in order. No reasoning about what to do, just dispatching.

**You are building both.**

---

## 2. LangGraph 1: The Thinker

Takes a user's natural language request and produces a Pipeline JSON that the Doer can execute. Everything is in terms of **blocks** — the decomposer outputs required blocks, the matcher checks the registry, the wirer connects them.

### 2.1 Thinker State

```python
from typing import TypedDict, Annotated, Any

def _append(existing: list, new: list) -> list:
    return existing + new

class ThinkerState(TypedDict):
    # ── Input ──
    user_intent: str                    # "Summarize top HN posts every morning"
    user_id: str

    # ── Decomposition (output: list of block specs) ──
    # Each required block is: {"block_id": "web_search", "reason": "need to search HN"}
    # or if no existing block fits: {"description": "scrape HN front page", "inputs": {...}, "outputs": {...}}
    required_blocks: list[dict]

    # ── Matching ──
    matched_blocks: list[dict]          # blocks found in registry (full block definitions)
    missing_blocks: list[dict]          # block specs that had no match in registry

    # ── Pipeline construction ──
    pipeline_json: dict | None          # the final Pipeline JSON output

    # ── Control ──
    status: str                         # "decomposing" | "matching" | "wiring" | "done" | "error"
    error: str | None
    log: Annotated[list[dict], _append]
```

### 2.2 Thinker Nodes

```python
# ── Node 1: DECOMPOSE ──
# Breaks user intent into a list of required blocks.
# Each block must be granular enough to be one-shotted by an executor with no errors.
#
# TODO: Teammate fills in the actual decomposition logic (LLM call with registry context).
# For now this is a stub that must be replaced.

async def decompose_intent(state: ThinkerState) -> dict:
    """Decompose user intent into a list of required blocks.

    Should return blocks like:
      [
        {"block_id": "web_search", "reason": "search for top HN posts"},
        {"block_id": "claude_summarize", "reason": "summarize the results"},
        {"block_id": "notify_push", "reason": "send summary to user"},
      ]

    If a needed block doesn't exist in the registry, describe what it should do:
      [
        {"description": "scrape HN front page", "suggested_id": "scrape_hn",
         "inputs": {"url": "string"}, "outputs": {"posts": "array"}},
      ]

    Blocks must be granular — each one does ONE thing that can be
    executed in a single shot with no ambiguity.
    """
    # TODO: Replace with actual decomposition logic
    raise NotImplementedError("Teammate: implement decomposition logic here")


# ── Node 2: MATCH BLOCKS ──
# Checks which required blocks exist in the registry.
# This is real code — it's just a registry lookup.

async def match_blocks(state: ThinkerState) -> dict:
    """Check registry for each required block. Split into matched vs missing."""
    matched = []
    missing = []

    for req in state["required_blocks"]:
        block_id = req.get("block_id")
        if block_id:
            try:
                block_def = registry.get(block_id)
                matched.append(block_def)
            except KeyError:
                missing.append(req)
        else:
            # No block_id — decomposer described a block that doesn't exist yet
            missing.append(req)

    return {
        "matched_blocks": matched,
        "missing_blocks": missing,
        "status": "wiring" if not missing else "error",
        "log": [{"step": "match",
                 "matched": [b["id"] for b in matched],
                 "missing": missing}],
    }


# ── Node 3: WIRE PIPELINE ──
# Connects matched blocks into a Pipeline JSON with {{template}} references.
#
# TODO: Teammate fills in the actual wiring logic (LLM call that produces pipeline JSON).
# For now this is a stub that must be replaced.

async def wire_pipeline(state: ThinkerState) -> dict:
    """Wire matched blocks into Pipeline JSON.

    Must produce:
    {
        "id": "pipeline_<short_name>",
        "name": "Human Readable Name",
        "user_prompt": "<original user request>",
        "nodes": [
            {"id": "n1", "block_id": "web_search", "inputs": {"query": "top HN posts today"}},
            {"id": "n2", "block_id": "claude_summarize", "inputs": {"content": "{{n1.results}}"}},
        ],
        "edges": [
            {"from": "n1", "to": "n2"}
        ],
        "memory_keys": []
    }

    Rules:
    - Each node has sequential id: n1, n2, n3...
    - Wire outputs → inputs using {{n1.field_name}} syntax
    - First node gets literal inputs, subsequent nodes reference previous outputs
    - Edges define execution order
    """
    # TODO: Replace with actual wiring logic
    raise NotImplementedError("Teammate: implement pipeline wiring logic here")
```

### 2.3 Thinker Graph

```python
from langgraph.graph import StateGraph, START, END

def build_thinker_graph() -> CompiledGraph:
    builder = StateGraph(ThinkerState)

    builder.add_node("decompose", decompose_intent)
    builder.add_node("match", match_blocks)
    builder.add_node("wire", wire_pipeline)

    # START → decompose → match
    builder.add_edge(START, "decompose")
    builder.add_edge("decompose", "match")

    # After match: all found → wire. Missing → error (future: build them).
    def route_after_match(state):
        if state["missing_blocks"]:
            return "error"
        return "wire"

    builder.add_conditional_edges("match", route_after_match, {
        "wire": "wire",
        "error": END,
    })

    builder.add_edge("wire", END)
    return builder.compile()
```

### 2.4 Thinker Flow

```
START
  │
  ▼
[decompose]  "Summarize top HN posts daily"             ← TODO: teammate implements
  │           → required_blocks:
  │             [{"block_id": "web_search"}, {"block_id": "claude_summarize"}, {"block_id": "notify_push"}]
  ▼
[match]      Check registry for each block               ← implemented (registry lookup)
  │           → matched: [web_search, claude_summarize, notify_push]
  │           → missing: []
  │
  ├─ missing? ──YES──► END (status: "error", missing_blocks: [...])
  │                     │
  NO              Future: route to [create_block] node
  │               which builds the missing block,
  ▼               registers it, then loops back to [match]
[wire]       Connect blocks into Pipeline JSON            ← TODO: teammate implements
  │           → pipeline_json: {"nodes": [...], "edges": [...]}
  ▼
END          → pipeline_json ready for the Doer
```

### 2.5 Future: Block Creation Loop

When block creation is implemented, the graph gains a loop:

```
[match] ──missing──► [create_block] ──► [match]   ← LOOP
   │                   creates the missing
   no missing          block and registers it
   │
   ▼
[wire]
```

LangGraph supports this loop natively. `create_block` could be its own sub-LangGraph (a Builder agent that generates block code, tests it, registers it). For now we stop with an error listing what's missing.

---

## 3. LangGraph 2: The Doer

Takes Pipeline JSON (output of the Thinker) and executes it.

### 3.1 Doer State

```python
from typing import TypedDict, Annotated, Any

def _merge(existing: dict, new: dict) -> dict:
    return {**existing, **new}

def _append(existing: list, new: list) -> list:
    return existing + new

class PipelineState(TypedDict):
    user_id: str
    pipeline_id: str

    # ── DATA BUS ── every block reads/writes here
    results: Annotated[dict[str, Any], _merge]
    # {"n1": {"results": [...]}, "n2": {"summary": "..."}}

    user: dict[str, Any]          # user profile
    memory: dict[str, Any]        # user memory (preferences, history)
    current_node: dict[str, Any]  # set per-node by graph builder
    log: Annotated[list[dict], _append]
```

### 3.2 Template Resolver

Turns `{{n1.results}}` into actual values from state.

```python
import re
from typing import Any

def resolve_templates(inputs: dict, state: dict) -> dict:
    resolved = {}
    for key, value in inputs.items():
        if isinstance(value, str):
            resolved[key] = _resolve_string(value, state)
        else:
            resolved[key] = value
    return resolved

def _resolve_string(value: str, state: dict) -> Any:
    # Whole string is a single {{ref}} → return raw value (preserves type: list, dict, etc.)
    match = re.fullmatch(r"\{\{(\w+)\.(\w+(?:\.\w+)*)\}\}", value.strip())
    if match:
        return _lookup(match.group(1), match.group(2), state)

    # Mixed text + refs → string interpolation
    def replacer(m):
        result = _lookup(m.group(1), m.group(2), state)
        return str(result) if result is not None else ""
    return re.sub(r"\{\{(\w+)\.(\w+(?:\.\w+)*)\}\}", replacer, value)

def _lookup(namespace: str, path: str, state: dict) -> Any:
    keys = path.split(".")
    if namespace in ("memory", "user"):
        obj = state.get(namespace, {})
    else:
        obj = state.get("results", {}).get(namespace, {})
    for k in keys:
        if isinstance(obj, dict):
            obj = obj.get(k)
        else:
            return None
    return obj
```

### 3.3 Block Executor

One function runs every block. Dispatches on `execution_type`.

```python
async def block_node(state: PipelineState) -> dict:
    node_def = state["current_node"]
    block = registry.get(node_def["block_id"])

    resolved_inputs = resolve_templates(node_def["inputs"], state)
    context = {"user": state.get("user", {}), "memory": state.get("memory", {})}

    match block["execution_type"]:
        case "llm":
            output = await run_llm_block(block, resolved_inputs, context)
        case "python":
            module = _import_block(block["execution"]["entrypoint"])
            output = await module.execute(resolved_inputs, context)
        case "mcp":
            raise NotImplementedError("MCP blocks — implement when needed")
        case "browser":
            raise NotImplementedError("Browser blocks — implement when needed")
        case _:
            raise ValueError(f"Unknown execution_type: {block['execution_type']}")

    return {
        "results": {node_def["id"]: output},
        "log": [{"node": node_def["id"], "block": block["id"], "output": output}],
    }


async def run_llm_block(block: dict, inputs: dict, context: dict) -> dict:
    prompt = block["prompt_template"].format(**inputs)
    system = f"You are executing: {block['name']}. {block['description']}\n"
    system += f"Return ONLY valid JSON matching: {json.dumps(block['output_schema'])}"

    tools = []
    if block.get("web_search_enabled"):
        tools = [web_search_tool]

    response = await call_llm(system=system, user=prompt, tools=tools)
    return parse_json_output(response, block["output_schema"])
```

### 3.4 Graph Builder

Pipeline JSON → compiled LangGraph.

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

def build_doer_graph(pipeline: dict) -> CompiledGraph:
    builder = StateGraph(PipelineState)

    # One node per block
    for node in pipeline["nodes"]:
        def make_node(node_def):
            async def run(state):
                return await block_node({**state, "current_node": node_def})
            return run
        builder.add_node(node["id"], make_node(node))

    # Memory load/save
    builder.add_node("_load_memory", load_memory_node)
    builder.add_node("_save_memory", save_memory_node)

    # START → load → first blocks
    builder.add_edge(START, "_load_memory")
    targets = {e["to"] for e in pipeline.get("edges", [])}
    for n in pipeline["nodes"]:
        if n["id"] not in targets:
            builder.add_edge("_load_memory", n["id"])

    # Pipeline edges
    for edge in pipeline.get("edges", []):
        if edge.get("condition"):
            builder.add_conditional_edges(edge["from"], make_router(edge["from"]), edge["branches"])
        else:
            builder.add_edge(edge["from"], edge["to"])

    # Last blocks → save → END
    sources = {e["from"] for e in pipeline.get("edges", [])}
    for n in pipeline["nodes"]:
        if n["id"] not in sources:
            builder.add_edge(n["id"], "_save_memory")
    builder.add_edge("_save_memory", END)

    return builder.compile(checkpointer=MemorySaver())
```

---

## 4. How They Connect — Full Flow

```
User: "Summarize top HN posts daily"
  │
  ▼
┌─────────────────────────────────────────────────┐
│  POST /api/create-agent                         │
│  body: { "intent": "...", "user_id": "..." }    │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │  THINKER GRAPH  │  ← LangGraph 1
         │                 │
         │  decompose      │  "I need: search, summarize, notify"
         │     ↓           │
         │  match          │  found: web_search, claude_summarize, notify_push
         │     ↓           │
         │  wire           │  outputs Pipeline JSON
         │                 │
         └────────┬────────┘
                  │
            Pipeline JSON
                  │
                  ▼
         ┌─────────────────┐
         │  DOER GRAPH     │  ← LangGraph 2 (built dynamically from the JSON)
         │                 │
         │  _load_memory   │
         │     ↓           │
         │  n1: web_search │  → {"results": [...5 HN posts...]}
         │     ↓           │
         │  n2: summarize  │  → {"summary": "1. Post about..."}
         │     ↓           │
         │  n3: notify     │  → {"delivered": true}
         │     ↓           │
         │  _save_memory   │
         │                 │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │  Response:      │
         │  {              │
         │    results: {}, │
         │    log: [...]   │
         │  }              │
         └─────────────────┘
```

---

## 5. The Block Model

A reusable unit stored in the registry. Has typed inputs/outputs and an `execution_type`.

```json
{
  "id": "web_search",
  "name": "Web Search",
  "description": "Search the web for information on a topic",
  "category": "input",
  "execution_type": "llm",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": { "type": "string" },
      "num_results": { "type": "integer", "default": 5 }
    },
    "required": ["query"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "results": { "type": "array" }
    }
  },
  "prompt_template": "Search the web for: {query}. Return the top {num_results} results with title, url, snippet.",
  "web_search_enabled": true,
  "metadata": { "created_by": "system", "tier": 1 }
}
```

### execution_type

| Type | What happens | Examples |
|---|---|---|
| `"llm"` | Claude API call with prompt template. Optional web search. | `web_search`, `claude_summarize`, `claude_decide` |
| `"python"` | Pure Python function. No LLM. | `filter_threshold`, `conditional_branch`, `notify_push` |
| `"mcp"` | Claude + MCP tools. For acting on services. | `slack_send`, `gmail_send` (future) |
| `"browser"` | Claude controls Playwright browser. | `browser_navigate` (future) |

**For now: implement `llm` and `python`. Stub `mcp` and `browser`.**

---

## 6. LLM Service

```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_provider: str = "anthropic"
    default_model: str = "claude-sonnet-4-5-20250929"
    llm_temperature: float = 0.0
    model_config = {"env_file": ".env"}

def get_llm(provider: str | None = None, model: str | None = None):
    settings = Settings()
    p = provider or settings.default_provider
    m = model or settings.default_model
    if p == "anthropic":
        return ChatAnthropic(model=m, api_key=settings.anthropic_api_key, temperature=settings.llm_temperature)
    elif p == "openai":
        return ChatOpenAI(model=m, api_key=settings.openai_api_key, temperature=settings.llm_temperature)
    raise ValueError(f"Unknown provider: {p}")

async def call_llm(system: str, user: str, tools: list | None = None,
                    provider: str | None = None, model: str | None = None) -> str:
    llm = get_llm(provider, model)
    if tools:
        llm = llm.bind_tools(tools)
    response = await llm.ainvoke([("system", system), ("human", user)])
    return response.content

def parse_json_output(text: str, schema: dict | None = None) -> dict:
    import json, re
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        return json.loads(json_match.group())
    return {}
```

---

## 7. Block Registry

```python
import json
from pathlib import Path

class BlockRegistry:
    def __init__(self, path: str = "registry/blocks.json"):
        self.path = Path(path)
        self._blocks: dict[str, dict] = {}
        if self.path.exists():
            with open(self.path) as f:
                self._blocks = {b["id"]: b for b in json.load(f)}

    def get(self, block_id: str) -> dict:
        if block_id not in self._blocks:
            raise KeyError(f"Block not found: {block_id}")
        return self._blocks[block_id]

    def save(self, block: dict):
        self._blocks[block["id"]] = block
        with open(self.path, "w") as f:
            json.dump(list(self._blocks.values()), f, indent=2)

    def list_all(self) -> list[dict]:
        return list(self._blocks.values())
```

---

## 8. Memory Store

```python
class MemoryStore:
    def __init__(self):
        self._users: dict[str, dict] = {}
        self._memory: dict[str, dict] = {}
        self._pipelines: dict[str, dict] = {}

    def get_user(self, user_id: str) -> dict | None:
        return self._users.get(user_id)

    def save_user(self, user_id: str, data: dict):
        self._users[user_id] = data

    def get_memory(self, user_id: str) -> dict | None:
        return self._memory.get(user_id)

    def save_memory(self, user_id: str, data: dict):
        self._memory[user_id] = data

    def get_pipeline(self, pipeline_id: str) -> dict | None:
        return self._pipelines.get(pipeline_id)

    def save_pipeline(self, pipeline_id: str, data: dict):
        self._pipelines[pipeline_id] = data

memory_store = MemoryStore()
```

---

## 9. FastAPI App

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="AgentFlow Engine")

# ── Create an agent (runs the Thinker) ──

class CreateAgentRequest(BaseModel):
    intent: str
    user_id: str

class CreateAgentResponse(BaseModel):
    pipeline_json: dict | None
    status: str
    log: list[dict]
    missing_blocks: list[dict]

@app.post("/api/create-agent", response_model=CreateAgentResponse)
async def create_agent(req: CreateAgentRequest):
    """Run the Thinker graph: user intent → Pipeline JSON."""
    thinker = build_thinker_graph()
    result = await thinker.ainvoke({
        "user_intent": req.intent,
        "user_id": req.user_id,
        "required_blocks": [],
        "matched_blocks": [],
        "missing_blocks": [],
        "pipeline_json": None,
        "status": "decomposing",
        "error": None,
        "log": [],
    })
    return CreateAgentResponse(
        pipeline_json=result.get("pipeline_json"),
        status=result["status"],
        log=result["log"],
        missing_blocks=result.get("missing_blocks", []),
    )

# ── Run a pipeline (runs the Doer) ──

class RunPipelineRequest(BaseModel):
    pipeline: dict
    user_id: str

class RunPipelineResponse(BaseModel):
    run_id: str
    status: str
    results: dict
    log: list[dict]

@app.post("/api/pipeline/run", response_model=RunPipelineResponse)
async def run_pipeline(req: RunPipelineRequest):
    """Run the Doer graph: Pipeline JSON → execute blocks → results."""
    graph = build_doer_graph(req.pipeline)
    result = await graph.ainvoke({
        "user_id": req.user_id,
        "pipeline_id": req.pipeline["id"],
        "results": {},
        "user": {},
        "memory": {},
        "current_node": {},
        "log": [],
    })
    return RunPipelineResponse(
        run_id=req.pipeline["id"],
        status="completed",
        results=result["results"],
        log=result["log"],
    )

# ── Full flow: create + run in one call ──

@app.post("/api/automate")
async def automate(req: CreateAgentRequest):
    """Create agent (Thinker) then immediately run it (Doer)."""
    # Step 1: Thinker
    create_result = await create_agent(req)
    if create_result.status != "done" or not create_result.pipeline_json:
        return {"status": "failed", "reason": "Could not create pipeline",
                "missing_blocks": create_result.missing_blocks, "log": create_result.log}

    # Step 2: Doer
    run_req = RunPipelineRequest(pipeline=create_result.pipeline_json, user_id=req.user_id)
    run_result = await run_pipeline(run_req)

    return {"status": "completed", "pipeline": create_result.pipeline_json,
            "results": run_result.results, "log": create_result.log + run_result.log}

# ── Block registry CRUD ──

@app.get("/api/blocks")
async def list_blocks():
    return registry.list_all()

@app.get("/api/blocks/{block_id}")
async def get_block(block_id: str):
    try:
        return registry.get(block_id)
    except KeyError:
        raise HTTPException(404, f"Block not found: {block_id}")

@app.post("/api/blocks")
async def create_block(block: dict):
    registry.save(block)
    return {"status": "created", "block_id": block["id"]}

@app.get("/api/memory/{user_id}")
async def get_memory(user_id: str):
    return memory_store.get_memory(user_id) or {}
```

---

## 10. Starter Blocks (seed registry/blocks.json)

```json
[
  {
    "id": "web_search",
    "name": "Web Search",
    "description": "Search the web for information on a topic",
    "category": "input",
    "execution_type": "llm",
    "input_schema": {
      "type": "object",
      "properties": {
        "query": { "type": "string" },
        "num_results": { "type": "integer", "default": 5 }
      },
      "required": ["query"]
    },
    "output_schema": {
      "type": "object",
      "properties": { "results": { "type": "array" } }
    },
    "prompt_template": "Search the web for: {query}. Return the top {num_results} results as JSON array with fields: title, url, snippet.",
    "web_search_enabled": true,
    "metadata": { "created_by": "system", "tier": 1 }
  },
  {
    "id": "claude_summarize",
    "name": "Summarize Content",
    "description": "Summarize text content in a given style",
    "category": "process",
    "execution_type": "llm",
    "input_schema": {
      "type": "object",
      "properties": {
        "content": { "type": "string" },
        "style": { "type": "string", "default": "concise" },
        "max_length": { "type": "integer", "default": 300 }
      },
      "required": ["content"]
    },
    "output_schema": {
      "type": "object",
      "properties": { "summary": { "type": "string" } }
    },
    "prompt_template": "Summarize the following in {style} style, max {max_length} words:\n\n{content}",
    "metadata": { "created_by": "system", "tier": 1 }
  },
  {
    "id": "claude_decide",
    "name": "Make a Decision",
    "description": "Choose between options based on criteria",
    "category": "process",
    "execution_type": "llm",
    "input_schema": {
      "type": "object",
      "properties": {
        "options": { "type": "string" },
        "criteria": { "type": "string" },
        "context": { "type": "string", "default": "" }
      },
      "required": ["options", "criteria"]
    },
    "output_schema": {
      "type": "object",
      "properties": { "selected": { "type": "string" }, "reasoning": { "type": "string" } }
    },
    "prompt_template": "Options:\n{options}\n\nCriteria: {criteria}\nContext: {context}\n\nPick the best option.",
    "metadata": { "created_by": "system", "tier": 1 }
  },
  {
    "id": "claude_analyze",
    "name": "Analyze Data",
    "description": "Analyze or compare data and return insights",
    "category": "process",
    "execution_type": "llm",
    "input_schema": {
      "type": "object",
      "properties": {
        "data": { "type": "string" },
        "analysis_type": { "type": "string", "default": "general" }
      },
      "required": ["data"]
    },
    "output_schema": {
      "type": "object",
      "properties": { "analysis": { "type": "string" }, "key_findings": { "type": "array" } }
    },
    "prompt_template": "Analyze ({analysis_type}):\n\n{data}\n\nReturn analysis and key findings.",
    "metadata": { "created_by": "system", "tier": 1 }
  },
  {
    "id": "claude_generate",
    "name": "Generate Content",
    "description": "Generate text content from a prompt",
    "category": "process",
    "execution_type": "llm",
    "input_schema": {
      "type": "object",
      "properties": {
        "prompt": { "type": "string" },
        "format": { "type": "string", "default": "paragraph" }
      },
      "required": ["prompt"]
    },
    "output_schema": {
      "type": "object",
      "properties": { "content": { "type": "string" } }
    },
    "prompt_template": "{prompt}\n\nFormat: {format}",
    "metadata": { "created_by": "system", "tier": 1 }
  },
  {
    "id": "filter_threshold",
    "name": "Compare Value to Threshold",
    "description": "Check if a value passes a comparison",
    "category": "process",
    "execution_type": "python",
    "input_schema": {
      "type": "object",
      "properties": {
        "value": { "type": "number" },
        "operator": { "type": "string", "enum": ["<", "<=", ">", ">=", "==", "!="] },
        "threshold": { "type": "number" }
      },
      "required": ["value", "operator", "threshold"]
    },
    "output_schema": {
      "type": "object",
      "properties": { "passed": { "type": "boolean" }, "value": { "type": "number" } }
    },
    "execution": { "runtime": "python", "entrypoint": "blocks/filter_threshold/main.py" },
    "metadata": { "created_by": "system", "tier": 1 }
  },
  {
    "id": "conditional_branch",
    "name": "Conditional Branch",
    "description": "Route to different paths based on a condition",
    "category": "process",
    "execution_type": "python",
    "input_schema": {
      "type": "object",
      "properties": { "condition": { "type": "boolean" }, "data": {} },
      "required": ["condition"]
    },
    "output_schema": {
      "type": "object",
      "properties": { "branch": { "type": "string" }, "data": {} }
    },
    "execution": { "runtime": "python", "entrypoint": "blocks/conditional_branch/main.py" },
    "metadata": { "created_by": "system", "tier": 1 }
  },
  {
    "id": "notify_push",
    "name": "Send Notification",
    "description": "Send a notification to the user (logs for hackathon)",
    "category": "action",
    "execution_type": "python",
    "input_schema": {
      "type": "object",
      "properties": { "title": { "type": "string" }, "body": { "type": "string" } },
      "required": ["title", "body"]
    },
    "output_schema": {
      "type": "object",
      "properties": { "delivered": { "type": "boolean" } }
    },
    "execution": { "runtime": "python", "entrypoint": "blocks/notify_push/main.py" },
    "metadata": { "created_by": "system", "tier": 1 }
  },
  {
    "id": "memory_read",
    "name": "Read Memory",
    "description": "Read a value from user memory",
    "category": "memory",
    "execution_type": "python",
    "input_schema": {
      "type": "object",
      "properties": { "key": { "type": "string" } },
      "required": ["key"]
    },
    "output_schema": {
      "type": "object",
      "properties": { "value": {} }
    },
    "execution": { "runtime": "python", "entrypoint": "blocks/memory_read/main.py" },
    "metadata": { "created_by": "system", "tier": 1 }
  },
  {
    "id": "memory_write",
    "name": "Write Memory",
    "description": "Write a value to user memory",
    "category": "memory",
    "execution_type": "python",
    "input_schema": {
      "type": "object",
      "properties": { "key": { "type": "string" }, "value": {} },
      "required": ["key", "value"]
    },
    "output_schema": {
      "type": "object",
      "properties": { "success": { "type": "boolean" } }
    },
    "execution": { "runtime": "python", "entrypoint": "blocks/memory_write/main.py" },
    "metadata": { "created_by": "system", "tier": 1 }
  }
]
```

---

## 11. File Structure

```
backend/
├── pyproject.toml                 # Dependencies (use `uv sync`)
├── .env                           # ANTHROPIC_API_KEY, OPENAI_API_KEY
├── main.py                        # FastAPI app (section 9)
│
├── engine/                        # Both LangGraphs live here
│   ├── __init__.py
│   ├── thinker.py                 # ThinkerState + decompose/match/wire nodes + build_thinker_graph() (section 2)
│   ├── state.py                   # PipelineState TypedDict + reducers (section 3.1)
│   ├── resolver.py                # resolve_templates() (section 3.2)
│   ├── executor.py                # block_node(), run_llm_block() (section 3.3)
│   ├── graph_builder.py           # build_doer_graph() (section 3.4)
│   └── memory.py                  # load_memory_node(), save_memory_node()
│
├── llm/
│   ├── __init__.py
│   └── service.py                 # get_llm(), call_llm(), parse_json_output() (section 6)
│
├── registry/
│   ├── __init__.py
│   ├── registry.py                # BlockRegistry class (section 7)
│   └── blocks.json                # Seed data (section 10)
│
├── storage/
│   ├── __init__.py
│   └── memory.py                  # MemoryStore + singleton (section 8)
│
├── blocks/                        # Python block implementations (execution_type: "python")
│   ├── filter_threshold/main.py   # async def execute(inputs, context) → {"passed": bool, "value": num}
│   ├── conditional_branch/main.py # → {"branch": "yes"|"no", "data": ...}
│   ├── notify_push/main.py        # Mock: print + return {"delivered": true}
│   ├── memory_read/main.py        # Read from context["memory"]
│   └── memory_write/main.py       # Write to context["memory"]
│
└── tests/
    ├── conftest.py
    ├── test_resolver.py
    ├── test_executor.py
    ├── test_thinker.py            # Thinker graph: mock LLM, verify decompose→match→wire flow
    ├── test_doer.py               # Doer graph: mock blocks, verify pipeline execution
    └── test_end_to_end.py         # Full: intent → thinker → pipeline JSON → doer → results
```

### pyproject.toml

```toml
[project]
name = "agentflow"
version = "0.1.0"
description = "LangGraph backbone for AI agent creation and execution"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.4",
    "langchain-openai>=0.3",
    "langchain-anthropic>=0.3",
    "langchain-core",
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "python-dotenv>=1.0",
    "fastapi>=0.115",
    "uvicorn>=0.34",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.25"]
mcp = ["langchain-mcp-adapters>=0.1"]
browser = ["browser-use>=0.1", "playwright>=1.40"]
```

### Setup

```bash
cd backend/
uv sync
cp .env.example .env  # add your ANTHROPIC_API_KEY
uv run pytest
uv run uvicorn main:app --reload
```

---

## 12. Example: Full Flow

**User:** "Summarize the top Hacker News posts every morning"

**Step 1 — Thinker runs:**
```
POST /api/create-agent
{"intent": "Summarize the top Hacker News posts every morning", "user_id": "user_1"}

Thinker graph:
  decompose → required_blocks:
                [{"block_id": "web_search"}, {"block_id": "claude_summarize"}, {"block_id": "notify_push"}]
  match     → all 3 found in registry, 0 missing
  wire      → Pipeline JSON:
    {
      "id": "hn_summary",
      "nodes": [
        {"id": "n1", "block_id": "web_search", "inputs": {"query": "top Hacker News posts today"}},
        {"id": "n2", "block_id": "claude_summarize", "inputs": {"content": "{{n1.results}}"}},
        {"id": "n3", "block_id": "notify_push", "inputs": {"title": "HN Daily", "body": "{{n2.summary}}"}}
      ],
      "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}]
    }
```

**Step 2 — Doer runs the Pipeline JSON:**
```
_load_memory → n1 (web_search) → n2 (summarize) → n3 (notify) → _save_memory

State after each node:
  results["n1"] = {"results": [{title: "Show HN: ...", url: "...", snippet: "..."}, ...]}
  results["n2"] = {"summary": "1. Show HN: New framework for...\n2. Ask HN: Best way to..."}
  results["n3"] = {"delivered": true}
```

**Response:**
```json
{
  "status": "completed",
  "pipeline": { "id": "hn_summary", "nodes": [...], "edges": [...] },
  "results": {
    "n1": { "results": [...] },
    "n2": { "summary": "..." },
    "n3": { "delivered": true }
  }
}
```
