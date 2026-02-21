# AgentFlow Backend

An AI agent creation and execution engine. Users describe what they want in natural language, and the system decomposes the intent into composable blocks, wires them into a pipeline DAG, and executes it.

## Architecture

The backend is built around two core pipelines:

```
User Intent (natural language)
        │
        ▼
   ┌─────────┐
   │ THINKER │  intent → Pipeline JSON
   └────┬────┘
        │  decompose → match → create → wire
        ▼
   Pipeline JSON
        │
        ▼
   ┌────────┐
   │  DOER  │  Pipeline JSON → execute blocks → results
   └────┴───┘
        │  load memory → topological execute → save memory
        ▼
   Results + Execution Log
```

**Thinker** — Converts natural language into a Pipeline JSON (a DAG of blocks).
**Doer** — Executes Pipeline JSON by running blocks in topological order with parallel batching.

## Quick Start

```bash
# Install dependencies
uv sync

# Copy env template and fill in API keys
cp .env.example .env

# Run the server
uvicorn main:app --reload

# Run tests
pytest
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes (if using OpenAI) | OpenAI API key |
| `ANTHROPIC_API_KEY` | Yes (if using Anthropic) | Anthropic API key |
| `PAID_API_KEY` | No | Paid.ai key for cost tracing |
| `DEFAULT_PROVIDER` | No | `openai` (default) or `anthropic` |
| `DEFAULT_MODEL` | No | Model ID, e.g. `gpt-4o` |
| `LLM_TEMPERATURE` | No | Temperature for LLM calls (default `0.0`) |

## Directory Structure

```
backend/
├── main.py                  # FastAPI app, all API endpoints
├── pyproject.toml           # Dependencies and project config
│
├── engine/                  # Core orchestration
│   ├── thinker.py           # Thinker pipeline (intent → Pipeline JSON)
│   ├── doer.py              # Doer pipeline (Pipeline JSON → results)
│   ├── state.py             # TypedDict state definitions
│   ├── schemas.py           # Pydantic models + validation
│   ├── resolver.py          # Template resolution ({{n1.field}})
│   ├── executor.py          # Block execution dispatcher
│   └── memory.py            # Memory load/save helpers
│
├── llm/                     # LLM integration
│   └── service.py           # OpenAI/Anthropic clients + Paid.ai tracing
│
├── registry/                # Block registry
│   ├── registry.py          # BlockRegistry class (CRUD + search)
│   └── blocks.json          # Seed block definitions
│
├── storage/                 # Persistence layer
│   └── memory.py            # In-memory store (users, memory, pipelines)
│
├── blocks/                  # Python block implementations
│   ├── filter_threshold/    # Compare value to threshold
│   ├── conditional_branch/  # Route based on boolean condition
│   ├── notify_push/         # Send notification (logs to stdout)
│   ├── memory_read/         # Read from user memory
│   ├── memory_write/        # Write to user memory
│   ├── lookup_price/        # Hardcoded product price lookup (demo)
│   └── generate_budget/     # Random budget within ±N% of price
│
├── schemas/                 # Exported JSON Schema files
│   ├── decompose_output.json
│   ├── match_output.json
│   ├── create_block_output.json
│   ├── wire_output.json
│   ├── pipeline_json.json
│   ├── block_definition.json
│   └── new_block_spec.json
│
└── tests/                   # Test suite
    ├── conftest.py          # Fixtures (sample pipelines)
    ├── test_resolver.py     # Template resolution tests
    ├── test_executor.py     # Block execution tests
    ├── test_thinker.py      # Thinker pipeline tests
    └── test_doer.py         # Doer pipeline tests
```

---

## API Endpoints

### `POST /api/create-agent`

Run the Thinker: convert user intent into Pipeline JSON.

**Request:**
```json
{
  "intent": "Summarize top HN posts daily",
  "user_id": "user_123"
}
```

**Response:**
```json
{
  "pipeline_json": { "id": "...", "nodes": [...], "edges": [...] },
  "status": "done",
  "log": [{"step": "match", "matched": ["web_search", "claude_summarize"]}],
  "missing_blocks": []
}
```

### `POST /api/pipeline/run`

Run the Doer: execute a Pipeline JSON and return results.

**Request:**
```json
{
  "pipeline": {
    "id": "pipeline_hn_summary",
    "name": "HN Daily Summary",
    "user_prompt": "Summarize top HN posts",
    "nodes": [
      {"id": "n1", "block_id": "web_search", "inputs": {"query": "top HN posts"}},
      {"id": "n2", "block_id": "claude_summarize", "inputs": {"content": "{{n1.results}}"}}
    ],
    "edges": [{"from": "n1", "to": "n2"}],
    "memory_keys": []
  },
  "user_id": "user_123"
}
```

**Response:**
```json
{
  "run_id": "pipeline_hn_summary",
  "status": "completed",
  "results": {
    "n1": {"results": [...]},
    "n2": {"summary": "..."}
  },
  "log": [
    {"step": "_load_memory", "user_id": "user_123"},
    {"node": "n1", "block": "web_search", "output": {"results": [...]}},
    {"node": "n2", "block": "claude_summarize", "output": {"summary": "..."}},
    {"step": "_save_memory", "user_id": "user_123"}
  ]
}
```

### `POST /api/automate`

Full flow: create an agent (Thinker) then immediately execute it (Doer).

**Request:** Same as `/api/create-agent`.

**Response:**
```json
{
  "status": "completed",
  "pipeline": { "id": "...", "nodes": [...], "edges": [...] },
  "results": { "n1": {...}, "n2": {...} },
  "log": [...]
}
```

### `GET /api/blocks`

List all registered blocks.

### `GET /api/blocks/{block_id}`

Get a single block definition by ID.

### `POST /api/blocks`

Register a new block definition. Body is a block definition object (see [Block Definition](#block-definition) below).

### `GET /api/memory/{user_id}`

Get the stored memory for a user.

### `GET /health`

Health check. Returns `{"status": "ok"}`.

---

## Core Concepts

### Pipeline JSON

The intermediate representation that connects the Thinker to the Doer. A directed acyclic graph (DAG) of block nodes:

```json
{
  "id": "pipeline_hn_summary",
  "name": "HN Daily Summary",
  "user_prompt": "Summarize the top Hacker News posts every morning",
  "nodes": [
    {"id": "n1", "block_id": "web_search", "inputs": {"query": "top HN posts today"}},
    {"id": "n2", "block_id": "claude_summarize", "inputs": {"content": "{{n1.results}}"}},
    {"id": "n3", "block_id": "notify_push", "inputs": {"title": "HN Daily", "body": "{{n2.summary}}"}}
  ],
  "edges": [
    {"from": "n1", "to": "n2"},
    {"from": "n2", "to": "n3"}
  ],
  "memory_keys": []
}
```

- **nodes**: Each has a sequential ID (`n1`, `n2`, ...), a `block_id` referencing a registered block, and `inputs` that can be literals or template references.
- **edges**: Define execution dependencies. The Doer uses these to build the topological execution order.
- **memory_keys**: Which user memory keys this pipeline reads/writes.

### Template References

Inputs use `{{namespace.path}}` syntax to reference outputs from earlier nodes or user context:

| Reference | Resolves to |
|---|---|
| `{{n1.results}}` | Output field `results` from node `n1` |
| `{{n2.summary}}` | Output field `summary` from node `n2` |
| `{{memory.preferences.theme}}` | Nested value in user memory |
| `{{user.name}}` | Field from user profile |

**Type preservation**: A whole-string reference like `"{{n1.results}}"` preserves the original type (list, dict, etc.). A mixed reference like `"Count: {{n2.count}}"` is stringified.

### Block Definition

A block is a single-purpose, reusable unit of work:

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
      "query": {"type": "string"},
      "num_results": {"type": "integer", "default": 5}
    },
    "required": ["query"]
  },
  "output_schema": {
    "type": "object",
    "properties": {"results": {"type": "array"}}
  },
  "prompt_template": "Search the web for: {query}. Return the top {num_results} results.",
  "metadata": {"created_by": "system", "tier": 1}
}
```

| Field | Description |
|---|---|
| `id` | Unique identifier |
| `name` | Human-readable name |
| `description` | What the block does |
| `category` | `input`, `process`, `action`, or `memory` |
| `execution_type` | `llm`, `python`, `mcp` (stub), or `browser` (stub) |
| `input_schema` | JSON Schema for inputs |
| `output_schema` | JSON Schema for outputs |
| `prompt_template` | For LLM blocks: prompt with `{input_name}` placeholders |
| `execution` | For Python blocks: `{"runtime": "python", "entrypoint": "blocks/x/main.py"}` |
| `metadata` | Arbitrary metadata (`created_by`, `tier`, etc.) |

---

## Engine Components

### Thinker (`engine/thinker.py`)

Converts user intent into Pipeline JSON through 4 stages:

| Stage | Function | Status | Description |
|---|---|---|---|
| 1. Decompose | `decompose_intent()` | Stub | Break intent into required blocks |
| 2. Match | `match_blocks()` | Implemented | Look up blocks in registry, split matched vs missing |
| 3. Create | `create_block()` | Stub | Generate missing block definitions via LLM |
| 4. Wire | `wire_pipeline()` | Stub | Connect blocks into Pipeline JSON via LLM |

**Orchestrator: `run_thinker(intent, user_id)`**

Executes stages sequentially with schema validation at each boundary. If blocks are missing after the match stage, routes through the create stage before wiring. Returns a `ThinkerState` dict.

**Flow:**
```
decompose → match ──┬──→ wire → done
                    │
                    └──→ create → wire → done
                  (if missing blocks)
```

### Doer (`engine/doer.py`)

Executes Pipeline JSON as a parallel DAG.

**`run_pipeline(pipeline, user_id)`**:
1. Build dependency graph from edges
2. Load user memory from storage
3. Execute nodes in topological order using `graphlib.TopologicalSorter`
4. Independent nodes at the same level run concurrently via `asyncio.gather`
5. Save memory after execution
6. Return results + execution log

### Template Resolver (`engine/resolver.py`)

**`resolve_templates(inputs, state)`** — Resolves `{{ref}}` templates in a node's inputs against pipeline state.

Three namespaces:
- `n1`, `n2`, etc. — node results from `state["results"]`
- `memory` — user memory from `state["memory"]`
- `user` — user profile from `state["user"]`

Supports dotted paths for nested access: `{{memory.preferences.theme}}`.

### Block Executor (`engine/executor.py`)

**`execute_block(node_def, state)`** — Dispatches block execution by `execution_type`:

| Type | Behavior |
|---|---|
| `llm` | Fill prompt template with inputs, call LLM, parse JSON response |
| `python` | Dynamic import of entrypoint module, call `execute(inputs, context)` |
| `mcp` | Not yet implemented |
| `browser` | Not yet implemented |

For LLM blocks, `run_llm_block()` fills default values from the block's `input_schema`, formats the prompt template, calls the LLM with a system prompt enforcing JSON output, and parses the response.

For Python blocks, `_import_block()` dynamically imports the module from its file path and calls its async `execute(inputs, context)` function.

### Schemas (`engine/schemas.py`)

Pydantic models for every stage boundary. Used by `validate_stage_output(stage, data)` to enforce contracts at each step.

| Model | Used at |
|---|---|
| `ExistingBlockRef` | Decompose output — reference to known block |
| `NewBlockSpec` | Decompose output — spec for block that needs creation |
| `DecomposeOutput` | After decompose stage |
| `MatchOutput` | After match stage |
| `BlockDefinition` | Create stage — full block definition |
| `CreateBlockOutput` | After create stage |
| `PipelineNode` | Wire stage — single node in DAG |
| `PipelineEdge` | Wire stage — directed edge |
| `PipelineJSON` | After wire stage — complete pipeline |
| `WireOutput` | Wire stage wrapper |

Export all schemas as JSON files:
```bash
python -m engine.schemas
```

### State Definitions (`engine/state.py`)

TypedDict definitions for pipeline state:

**`ThinkerState`** — State flowing through the Thinker:
- `user_intent`, `user_id` — inputs
- `required_blocks` — decompose output
- `matched_blocks`, `missing_blocks` — match output
- `pipeline_json` — wire output
- `status` — `decomposing | matching | creating | wiring | done | error`
- `error`, `log` — control fields

**`PipelineState`** — State flowing through the Doer:
- `user_id`, `pipeline_id` — identifiers
- `results` — `{node_id: output_dict}` data bus
- `user`, `memory` — user context
- `log` — execution trace

### Memory Helpers (`engine/memory.py`)

Thin wrappers around the storage layer:
- `load_memory(user_id)` — returns `(user_dict, memory_dict)`
- `save_memory(user_id, memory, pipeline_id, results)` — persists memory and pipeline results

---

## LLM Service (`llm/service.py`)

Unified interface for calling OpenAI or Anthropic models.

**`get_client(provider)`** — Returns an LLM client, optionally wrapped with Paid.ai for cost tracing.

**`call_llm(system, user, provider, model)`** — Makes an LLM call with system + user messages. Reads config from environment variables.

**`parse_json_output(text, schema)`** — Extracts the first JSON object from LLM text output. Returns `{"raw": text}` if parsing fails.

---

## Block Registry (`registry/registry.py`)

Manages block definitions, persisted to `registry/blocks.json`.

| Method | Description |
|---|---|
| `get(block_id)` | Retrieve block by ID. Raises `KeyError` if not found. |
| `save(block)` | Register a block and persist to JSON file. |
| `list_all()` | Return all registered blocks. |
| `search(query)` | Case-insensitive search across `id`, `name`, `description`. |

Module-level singleton: `registry`.

### Seed Blocks

The registry ships with 10 pre-registered blocks in `blocks.json`:

| Block ID | Type | Category | Description |
|---|---|---|---|
| `web_search` | LLM | input | Search the web for information |
| `claude_summarize` | LLM | process | Summarize text in a given style |
| `claude_decide` | LLM | process | Choose between options based on criteria |
| `claude_analyze` | LLM | process | Analyze data and return insights |
| `claude_generate` | LLM | process | Generate text content from a prompt |
| `filter_threshold` | Python | process | Compare value against threshold with operator |
| `conditional_branch` | Python | process | Route to yes/no path based on boolean |
| `notify_push` | Python | action | Send notification (logs to stdout for now) |
| `memory_read` | Python | memory | Read a value from user memory |
| `memory_write` | Python | memory | Write a value to user memory |

---

## Storage (`storage/memory.py`)

In-memory key-value store for users, memory, and pipelines. Designed to be swapped for a real database later.

| Method | Description |
|---|---|
| `get_user(user_id)` / `save_user(user_id, data)` | User profile CRUD |
| `get_memory(user_id)` / `save_memory(user_id, data)` | Per-user memory CRUD |
| `get_pipeline(pipeline_id)` / `save_pipeline(pipeline_id, data)` | Pipeline result CRUD |

Module-level singleton: `memory_store`.

---

## Python Block Implementations

Each Python block is an async function with the signature:

```python
async def execute(inputs: dict, context: dict) -> dict
```

- `inputs` — Resolved input values (after template resolution)
- `context` — `{"user": {...}, "memory": {...}}`
- Returns an output dict matching the block's `output_schema`

### `filter_threshold`
Compares a numeric value against a threshold using an operator (`<`, `<=`, `>`, `>=`, `==`, `!=`).
Returns `{"passed": bool, "value": float}`.

### `conditional_branch`
Routes to `"yes"` or `"no"` based on a boolean `condition`.
Returns `{"branch": "yes"|"no", "data": <passthrough>}`.

### `notify_push`
Logs a notification to stdout. Placeholder for real push notification delivery.
Returns `{"delivered": true}`.

### `memory_read`
Reads a key from `context["memory"]`.
Returns `{"value": <any>}`.

### `memory_write`
Writes a key/value pair to `context["memory"]` (mutates the context dict in-place).
Returns `{"success": true}`.

### `lookup_price`
Returns a hardcoded product price from a demo lookup table (airpods, iphone, macbook).
Returns `{"product": str, "price": float, "currency": "USD"}`.

### `generate_budget`
Generates a random budget within +/-N% variance of a given price.
Returns `{"budget": float, "range_low": float, "range_high": float}`.

---

## End-to-End Example

**User intent:** "Summarize top Hacker News posts every morning"

### Step 1: Thinker decomposes intent into blocks
```
decompose_intent() → [
  {"block_id": "web_search", "reason": "search for top HN posts"},
  {"block_id": "claude_summarize", "reason": "summarize results"},
  {"block_id": "notify_push", "reason": "send summary to user"}
]
```

### Step 2: Thinker matches blocks against registry
```
match_blocks() → all 3 found → status: "wiring"
```

### Step 3: Thinker wires blocks into Pipeline JSON
```json
{
  "id": "pipeline_hn_summary",
  "name": "HN Daily Summary",
  "user_prompt": "Summarize top HN posts every morning",
  "nodes": [
    {"id": "n1", "block_id": "web_search", "inputs": {"query": "top Hacker News posts today"}},
    {"id": "n2", "block_id": "claude_summarize", "inputs": {"content": "{{n1.results}}"}},
    {"id": "n3", "block_id": "notify_push", "inputs": {"title": "HN Daily", "body": "{{n2.summary}}"}}
  ],
  "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}],
  "memory_keys": []
}
```

### Step 4: Doer executes the DAG
```
_load_memory("user_123")
  ↓
n1: web_search → {"results": [{"title": "Show HN: ...", "url": "..."}]}
  ↓
n2: claude_summarize → {"summary": "Top posts include..."}
  ↓  ({{n1.results}} resolved to actual list)
n3: notify_push → {"delivered": true}
  ↓  ({{n2.summary}} resolved to actual string)
_save_memory("user_123")
```

---

## Tests

Run the full test suite:
```bash
pytest
```

| File | Covers | Tests |
|---|---|---|
| `test_resolver.py` | Template resolution: type preservation, namespaces, nested paths, missing refs, mixed interpolation | 11 |
| `test_executor.py` | Block dispatch: Python blocks, LLM blocks (mocked), error handling, dynamic import | 7 |
| `test_thinker.py` | Thinker pipeline: match logic, stub behavior, schema validation at each stage | 11 |
| `test_doer.py` | Doer pipeline: sequential chains, parallel nodes, memory lifecycle, state structure | 5 |

Test fixtures in `conftest.py` provide sample pipelines:
- `sample_pipeline_json` — 2-node sequential (filter → notify)
- `three_node_pipeline` — 3-node chain (filter → branch → notify)
- `parallel_pipeline` — 2 independent roots merging into a sink node

---

## Implementation Status

### Implemented
- FastAPI endpoints (full CRUD + orchestration)
- Block registry (load, save, search, list)
- In-memory storage (users, memory, pipelines)
- Template resolver with type preservation
- Block executor (Python + LLM dispatch)
- Doer pipeline (parallel DAG execution)
- Pydantic schema validation at every stage boundary
- 7 Python block implementations
- 5 LLM block definitions (seed)
- Test suite (34 tests)

### Stubs (to be implemented)
- `decompose_intent()` — LLM breaks intent into required blocks
- `create_block()` — LLM generates missing block definitions
- `wire_pipeline()` — LLM wires matched blocks into Pipeline JSON
- MCP block execution type
- Browser block execution type
