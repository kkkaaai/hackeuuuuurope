# AgentFlow Pipeline Architecture

> How a user's natural-language intent becomes a running, multi-block pipeline.

---

## High-Level Flow

```
User Intent (text)
       │
       ▼
┌─────────────┐    not ready     ┌────────────┐
│  CLARIFIER   │ ◄──────────────► │   User Q&A  │
│  (pre-flight)│    ready         └────────────┘
└──────┬──────┘
       │  refined_intent
       ▼
┌─────────────────────────────────────────────┐
│              T H I N K E R                   │
│                                              │
│  ┌──────────┐  ┌────────┐  ┌────────┐  ┌──────┐ │
│  │ DECOMPOSE│→ │ SEARCH │→ │ CREATE │→ │ WIRE │ │
│  └──────────┘  └────────┘  └────────┘  └──────┘ │
│                                              │
└──────────────────────┬──────────────────────┘
                       │  Pipeline JSON (DAG)
                       ▼
┌─────────────────────────────────────────────┐
│                D O E R                       │
│                                              │
│  Load Memory → Topo-Sort → Execute Nodes    │
│  (parallel batches) → Save Memory           │
│                                              │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
              Execution Results
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/clarify` | POST | Pre-pipeline Q&A — checks if intent is specific enough |
| `/api/create-agent` | POST | Blocking Thinker call — returns complete Pipeline JSON |
| `/api/create-agent/stream` | POST | Streaming Thinker — SSE events for live progress |
| `/api/pipeline/run` | POST | Blocking Doer call — executes a Pipeline JSON |
| `/api/automate` | POST | Full flow: Thinker + Doer in a single call |
| `/api/blocks` | GET/POST | Block registry CRUD |
| `/api/blocks/{id}/source` | GET | Get block source code or prompt template |
| `/api/blocks/search` | POST | Hybrid search (semantic + full-text) |
| `/api/pipelines/*` | CRUD | Pipeline storage & management |
| `/api/executions/*` | GET | Execution history |
| `/api/memory/{user_id}` | GET | User memory retrieval |

---

## Stage 0 — Clarifier

**File:** `engine/clarifier.py`

**Purpose:** Evaluate whether the user's request is specific enough to build a pipeline, and if not, ask clarifying questions.

```
User message
     │
     ▼
┌────────────────┐   not ready    ┌─────────────────┐
│ Evaluate intent │──────────────► │ Ask 1 clarifying │
│ (clear action + │                │ question         │
│  enough context)│                └────────┬────────┘
└───────┬────────┘                          │
        │ ready                             │ user answers
        ▼                                   ▼
┌──────────────────┐              (loop, max 3 rounds)
│ Synthesize entire │
│ conversation into │
│ refined_intent    │
└───────┬──────────┘
        │
        ▼
 { ready: true, refined_intent: "..." }
```

**Key details:**
- After 3+ user messages, forces `ready` and synthesizes from the full conversation.
- Enhanced intent includes: goal, steps, inputs/parameters, outputs, edge cases.

**Output:**
```json
{
  "ready": true,
  "refined_intent": "Detailed, self-contained specification synthesized from conversation..."
}
```

---

## Stage 1 — Decompose

**File:** `engine/thinker_stream.py` (lines ~53-104) + `engine/thinker.py` (prompt builders)

**Purpose:** Break the user's intent into a list of required building blocks, each with typed IO schemas.

```
refined_intent
     │
     ▼
┌──────────────────────────┐
│ LLM Call (gpt-4o)         │
│                           │
│ System: decompose prompt  │
│ User: refined_intent      │
└───────────┬──────────────┘
            │
            ▼
    required_blocks[]
```

**Output — `required_blocks` array:**
```json
[
  {
    "suggested_id": "web_search",
    "description": "Search the web for recent articles on a given topic",
    "execution_type": "python",
    "depends_on": [],
    "input_schema": {
      "type": "object",
      "properties": {
        "query": { "type": "string", "description": "Search query" }
      },
      "required": ["query"]
    },
    "output_schema": {
      "type": "object",
      "properties": {
        "results": { "type": "array", "description": "Search results" }
      }
    }
  }
]
```

**Validated against:** `DecomposeOutput` Pydantic model in `engine/schemas.py`.

**SSE events emitted:** `stage`, `llm_prompt`, `llm_response`, `stage_result`, `decompose_blocks`, `validation`.

---

## Stage 2 — Search

**File:** `engine/thinker_stream.py` (lines ~106-166)

**Purpose:** For each required block, search the registry for an existing match. Split into matched vs. missing.

```
required_blocks[]
     │
     ▼
┌─────────────────────────────────┐
│ For each block:                  │
│   registry.search(description)   │
│   → hybrid (semantic + text)     │
│   → validate match quality       │
└──────────┬──────────────────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
matched[]    missing[]
```

**Search mechanism:**
1. Generate embedding for the block description using **OpenAI text-embedding-3-small**.
2. Call Supabase RPC `search_blocks(query_text, query_embedding, limit=5)`.
3. Validate match with `_is_good_match()` — checks `execution_type` compatibility.
4. Fallback to case-insensitive text search on embedding errors.

**SSE events emitted:** `search_found` or `search_missing` per block.

---

## Stage 3 — Create (conditional)

**File:** `engine/thinker_stream.py` (lines ~168-281)

**Purpose:** Generate, test, and register new blocks for any specs not found in the registry.

```
missing[]
   │
   ▼
┌─────────────────────────────────────────┐
│ For each missing block:                  │
│                                          │
│  1. LLM generates block definition       │
│  2. _finalize_created_block()            │
│     - validate JSON structure            │
│     - compile() check for Python blocks  │
│  3. _test_block() with sample inputs     │
│     - up to 3 retries on failure         │
│     - error from previous attempt        │
│       fed back to LLM                    │
│  4. Save to registry (if test passes)    │
└──────────┬──────────────────────────────┘
           │
           ▼
       created[]
```

**Two block types generated:**

| Type | Contains | Validation |
|------|----------|------------|
| **Python** | `source_code` with `async def execute(inputs, context) -> dict` | `compile()` check, sample execution |
| **LLM** | `prompt_template` with `{placeholder}` syntax | Template parsing, sample LLM call |

**Allowed Python modules:**
```
json, math, statistics, collections, itertools, functools,
re, datetime, random, os (env vars only), httpx
```

**SSE events emitted:** `creating_block`, `block_created`, `block_test_passed` / `block_test_failed`, `block_create_failed`.

---

## Stage 4 — Wire

**File:** `engine/thinker_stream.py` (lines ~283-328)

**Purpose:** Assemble all blocks (matched + created) into a Pipeline JSON — a directed acyclic graph with data-flow wiring.

```
matched[] + created[] + user_intent
     │
     ▼
┌──────────────────────────┐
│ LLM Call (gpt-4o)         │
│                           │
│ System: wire prompt        │
│ User: blocks + intent     │
└───────────┬──────────────┘
            │
            ▼
      Pipeline JSON
```

**Output — Pipeline JSON:**
```json
{
  "id": "market_research_pipeline",
  "name": "Market Research Pipeline",
  "user_prompt": "Research competitors in the AI space",
  "nodes": [
    {
      "id": "n1",
      "block_id": "web_search",
      "inputs": { "query": "AI competitor analysis 2025" }
    },
    {
      "id": "n2",
      "block_id": "summarizer",
      "inputs": { "text": "{{n1.results}}" }
    }
  ],
  "edges": [
    { "from": "n1", "to": "n2" }
  ],
  "memory_keys": ["last_research_topic"]
}
```

**Template syntax:** `{{n1.field_name}}` — references output of node `n1`.

**Validated against:** `PipelineJSON` Pydantic model in `engine/schemas.py`.

---

## Stage 5 — Execute (Doer)

**File:** `engine/doer.py`

**Purpose:** Execute the Pipeline JSON as a parallel DAG.

```
Pipeline JSON + user_id
        │
        ▼
┌───────────────────┐
│  1. Load Memory    │  ← Supabase user_memory table
└───────┬───────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  2. Build Dependency Graph             │
│     edges → adjacency map              │
│     graphlib.TopologicalSorter         │
└───────┬───────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  3. Execute in Batches                 │
│                                        │
│  Level 0: [n1, n2]  ← parallel        │
│  Level 1: [n3]      ← depends on n1   │
│  Level 2: [n4, n5]  ← parallel        │
│                                        │
│  For each node:                        │
│    a. Resolve {{templates}} → values   │
│    b. execute_block(block, inputs)     │
│    c. Store result in state            │
│    d. Skip if upstream failed          │
└───────┬───────────────────────────────┘
        │
        ▼
┌───────────────────┐
│  4. Save Memory    │  → Supabase
│  5. Save Execution │  → Supabase executions table
└───────┬───────────┘
        │
        ▼
   PipelineState
```

**Output — PipelineState:**
```json
{
  "pipeline_id": "market_research_pipeline",
  "results": {
    "n1": { "results": [...], "query_used": "...", "count": 5 },
    "n2": { "summary": "..." }
  },
  "user": {},
  "memory": { "last_research_topic": "AI competitors" },
  "log": [
    { "node": "n1", "block": "web_search", "output": { "..." } },
    { "node": "n2", "block": "summarizer", "output": { "..." } }
  ]
}
```

---

## Block Execution Engine

**File:** `engine/executor.py`

Two execution paths depending on `execution_type`:

### LLM Block Execution

```
block.prompt_template + resolved inputs
        │
        ▼
┌───────────────────────────────┐
│ 1. _safe_format() template    │  Fill {placeholders} with inputs
│ 2. Build system prompt        │  Block metadata + output schema
│ 3. call_llm(system, filled)   │  → gpt-4o / claude
│ 4. parse_json_output()        │  Extract JSON from response
│ 5. Validate against schema    │
└───────────┬───────────────────┘
            ▼
        output dict
```

### Python Block Execution

```
block.source_code + resolved inputs + context
        │
        ▼
┌───────────────────────────────┐
│ 1. compile(source_code)       │
│ 2. exec() in restricted ns   │  Whitelisted imports only
│ 3. call execute(inputs, ctx)  │  async def execute(inputs, context)
│ 4. Return result dict         │
└───────────┬───────────────────┘
            ▼
        output dict
```

**Context object passed to every block:**
```python
{
  "user": {},                 # User profile
  "memory": { ... },          # Persistent key-value memory
  "user_id": "user_123",      # User identifier
  "supabase": <Client>        # Direct Supabase access
}
```

---

## Template Resolution

**File:** `engine/resolver.py`

**Syntax:** `{{namespace.dotted.path}}`

| Namespace | Resolves to |
|-----------|------------|
| `memory` | `state["memory"]` |
| `user` | `state["user"]` |
| `n1`, `n2`, ... | `state["results"]["n1"]`, etc. |

**Behaviors:**
- Whole-string match (`"{{n1.results}}"`) → returns raw value (preserves type: list, dict, int).
- Mixed text + refs (`"Search for {{n1.topic}}"`) → string interpolation.
- Nested paths (`"{{n1.results.0.data}}"`) → dot-traversal with index support.
- Missing references → `None` (safe fallback, no crash).

---

## SSE Event Stream

**Endpoint:** `GET /api/create-agent/stream`

Real-time progress events during Thinker pipeline:

```
event: start
data: {"type": "start", "ts": 1708000000}

event: stage
data: {"type": "stage", "stage": "decompose", "ts": ...}

event: llm_prompt
data: {"type": "llm_prompt", "prompts": [...], "ts": ...}

event: llm_response
data: {"type": "llm_response", "response": "...", "elapsed": 2.3, "ts": ...}

event: decompose_blocks
data: {"type": "decompose_blocks", "blocks": [...], "ts": ...}

event: search_found
data: {"type": "search_found", "block_id": "web_search", "ts": ...}

event: search_missing
data: {"type": "search_missing", "suggested_id": "new_block", "ts": ...}

event: creating_block
data: {"type": "creating_block", "suggested_id": "...", "ts": ...}

event: block_created
data: {"type": "block_created", "block": {...}, "ts": ...}

event: block_test_passed
data: {"type": "block_test_passed", "block_id": "...", "ts": ...}

event: complete
data: {"type": "complete", "result": { pipeline_json, status, log }, "ts": ...}
```

---

## Storage Layer

**Files:** `storage/supabase_client.py`, `storage/memory.py`, `storage/embeddings.py`

### Supabase Tables

| Table | Purpose |
|-------|---------|
| `blocks` | Block definitions + embedding vectors |
| `user_memory` | Per-user key-value persistent memory |
| `pipelines` | Saved pipeline JSON definitions |
| `executions` | Execution run history with results |
| `notifications` | User notifications |

### Embedding Pipeline

```
Block saved
    │
    ▼
block_to_search_text()    ← description + use_when + tags only
    │
    ▼
generate_embedding()      ← OpenAI text-embedding-3-small
    │
    ▼
Stored in blocks.embedding column
```

Only semantic content is embedded (no IO schemas) to keep the vector space aligned with natural-language queries.

---

## Models & External Services

| Component | Model / Service | Purpose |
|-----------|----------------|---------|
| Thinker LLM | gpt-4o (default) or claude-opus-4-6 | Decompose, create, wire |
| LLM Blocks | Same provider as Thinker | Runtime text processing |
| Embeddings | OpenAI text-embedding-3-small | Semantic block search |
| Database | Supabase (PostgreSQL) | All persistent storage |
| Cost Tracking | Paid.ai (optional) | LLM cost tracing |

---

## Error Handling & Resilience

| Scenario | Behavior |
|----------|----------|
| Block creation fails test | Retry up to **3 times**, feeding error back to LLM each retry |
| All retries exhausted | Block marked `test_passed: false`, **not** saved to registry |
| Upstream node fails | Downstream dependents **skipped** (not executed) |
| Template ref missing | Returns `None` (safe fallback) |
| Embedding search fails | Falls back to case-insensitive **text search** |
| Pipeline has any failed node | Overall status = `"failed"`, independent nodes still execute |

---

## Block Definition Schema

```json
{
  "id": "block_id",
  "name": "Human Readable Name",
  "description": "What this block does",
  "category": "input | process | action | memory | trigger",
  "execution_type": "llm | python",

  "input_schema": {
    "type": "object",
    "properties": { "field": { "type": "string", "description": "..." } },
    "required": ["field"]
  },
  "output_schema": { "..." },

  "prompt_template": "...",    // LLM blocks only
  "source_code": "...",        // Python blocks only

  "use_when": "When to use this block",
  "tags": ["tag1", "tag2"],
  "examples": [{ "inputs": {}, "outputs": {} }],
  "metadata": { "created_by": "thinker", "tier": 2 }
}
```

---

## File Map

```
Demo/backend/
├── main.py                    # FastAPI app — all endpoints
├── engine/
│   ├── thinker.py             # Shared prompt builders & helpers
│   ├── thinker_stream.py      # Thinker orchestration (SSE streaming)
│   ├── clarifier.py           # Pre-pipeline intent clarification
│   ├── doer.py                # Pipeline executor (DAG runner)
│   ├── executor.py            # Individual block execution (LLM + Python)
│   ├── resolver.py            # {{template}} resolution
│   ├── schemas.py             # Pydantic validation models
│   ├── state.py               # TypedDict state definitions
│   └── memory.py              # Memory load/save delegation
├── storage/
│   ├── supabase_client.py     # Singleton Supabase client
│   ├── memory.py              # SupabaseStore (memory, pipelines, executions)
│   └── embeddings.py          # OpenAI embedding generation
├── registry/
│   └── registry.py            # Block registry (CRUD, search, cache)
└── llm/
    └── service.py             # LLM provider abstraction (OpenAI / Anthropic)
```
