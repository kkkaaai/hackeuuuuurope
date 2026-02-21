# Lovable: LangGraph Orchestration Backbone

## Context

We're building the **graph backbone** for "Lovable" — a framework where non-technical users create AI agents via natural language. A teammate handles decomposition (breaking NL into steps). Our job: the LangGraph-based orchestration engine that chains reusable blocks into executable flows, with memory across runs.

Key requirement: **blocks are reusable and stored in a database**. E.g., an "open Uber Eats" block or a "query memory" block gets created once and reused across many agents. We don't rebuild blocks from scratch every time.

---

## How LangGraph Actually Works

### The Core Primitives

LangGraph has 3 primitives: **State**, **Nodes**, and **Edges**.

**1. State** — A `TypedDict` that is the single source of truth flowing through the graph:
```python
class MyState(TypedDict):
    messages: list[str]
    result: str
```
Every node receives the full state and returns a **partial update** (only the keys it wants to change). LangGraph merges the update into the state automatically.

**2. Nodes** — Python async functions with signature `(state: MyState) -> dict`:
```python
async def my_node(state: MyState) -> dict:
    # Read from state
    messages = state["messages"]
    # Do work...
    # Return ONLY the keys you want to update
    return {"result": "done"}
```
A node is NOT the block itself — a node is the **executor function**. We use ONE generic executor function for all blocks. The block definition (stored in DB) tells the executor what to do.

**3. Edges** — Define control flow between nodes:
```python
builder = StateGraph(MyState)
builder.add_node("step_1", my_node)
builder.add_node("step_2", my_node)
builder.add_edge("step_1", "step_2")        # Linear: step_1 → step_2
builder.add_conditional_edges("step_2", router_fn, {"a": "step_3", "b": "step_4"})  # Branching
```

### How This Maps to Our Blocks

In LangGraph, a node is just a function. **Our blocks are not nodes — blocks are DATA (configuration) that a single generic node function interprets.** This is the key insight:

```
Block Definition (stored in DB)     →  describes WHAT to do
     ↓
Generic Executor Node (code)        →  knows HOW to do it
     ↓
LangGraph Node                      →  a slot in the graph wired by edges
```

A **Block** is defined by:
- **Input keys**: what it reads from the shared state (e.g., `["restaurant_name", "user_preferences"]`)
- **Output keys**: what it writes back to state (e.g., `["order_items", "order_total"]`)
- **Prompt template**: instructions for the LLM, with `{placeholders}` for input keys
- **Tools required**: what capabilities it needs (browser, API, etc.)
- **LLM config**: which provider/model to use

This is **fully compatible with LangGraph** because:
1. The block's **input keys** = what the executor reads from `state`
2. The block's **output keys** = what the executor returns in the partial update dict
3. LangGraph's reducers handle merging outputs into state automatically

### The Generic Executor Pattern

```python
async def block_executor(state: OrchestrationState) -> dict:
    """ONE function that executes ANY block based on its definition."""
    # 1. Read the block definition from state
    block_def = state["current_block"]

    # 2. Extract input values from state using block's input_keys
    inputs = {key: state["shared_context"].get(key) for key in block_def["input_keys"]}

    # 3. Render the prompt template with inputs
    prompt = block_def["prompt_template"].format(**inputs)

    # 4. Call the LLM
    result = await call_llm_json(prompt, tools=block_def["tools"])

    # 5. Return outputs mapped to block's output_keys → merged into shared_context
    return {"shared_context": {key: result[key] for key in block_def["output_keys"]}}
```

### How the Graph Gets Built

When a user creates an agent, the decomposition engine picks blocks from the database and arranges them into a **flow** (a `TaskPlan`). The graph builder then:

1. Creates a `StateGraph` with one node per block in the flow
2. Each node uses the same `block_executor` function
3. Edges are wired based on the dependency order from the TaskPlan
4. The compiled graph runs with `MemorySaver` for interrupt/resume

```python
# Pseudo-code for dynamic graph construction
builder = StateGraph(OrchestrationState)

for block_ref in task_plan.blocks:
    block_def = load_block_from_db(block_ref.block_id)
    # Each node is the SAME function, but state["current_block"] varies
    builder.add_node(f"block_{block_ref.block_id}", block_executor)

# Wire edges based on plan ordering
for i, block_ref in enumerate(task_plan.blocks[:-1]):
    builder.add_edge(f"block_{block_ref.block_id}", f"block_{next_block.block_id}")
```

---

## Block Definition Schema

```python
class BlockDefinition(BaseModel):
    """A reusable block stored in the database."""
    block_id: str                          # Unique ID, e.g., "open_uber_eats"
    name: str                              # Human-readable, e.g., "Open Uber Eats"
    description: str                       # What this block does
    version: int = 1                       # For versioning block updates

    # --- Input/Output Contract ---
    input_keys: list[str]                  # Keys this block reads from shared_context
    output_keys: list[str]                 # Keys this block writes to shared_context

    # --- Execution Config ---
    prompt_template: str                   # LLM prompt with {placeholder} for inputs
    tools_required: list[str] = []         # e.g., ["browser", "http_api"]
    llm_provider: str | None = None        # "openai" / "anthropic" / None (use default)
    llm_model: str | None = None           # Override model per block

    # --- Behavior ---
    block_type: BlockType                  # action / decision / extraction / query_memory
    branches: dict[str, str] | None = None # For decision blocks: {"yes": next_block_id, ...}
    max_retries: int = 2
    timeout_seconds: int = 60

    # --- Metadata ---
    category: str = ""                     # "food_delivery", "memory", "navigation", etc.
    tags: list[str] = []                   # For search/discovery
    created_by: str = "system"
```

### Example Blocks in the Database

**Block: "open_uber_eats"**
```json
{
    "block_id": "open_uber_eats",
    "name": "Open Uber Eats",
    "description": "Navigate to Uber Eats and log in",
    "input_keys": ["uber_eats_credentials"],
    "output_keys": ["session_active", "logged_in"],
    "prompt_template": "Navigate to ubereats.com. Log in using credentials: {uber_eats_credentials}. Confirm you are logged in.",
    "tools_required": ["browser"],
    "block_type": "action"
}
```

**Block: "query_memory"**
```json
{
    "block_id": "query_memory",
    "name": "Query Memory",
    "description": "Search long-term memory for relevant context",
    "input_keys": ["memory_query"],
    "output_keys": ["memory_results"],
    "prompt_template": "Search the user's memory for: {memory_query}. Return relevant preferences, history, and context.",
    "tools_required": [],
    "block_type": "query_memory"
}
```

**Block: "add_to_cart"**
```json
{
    "block_id": "add_to_cart_generic",
    "name": "Add Items to Cart",
    "description": "Add specified items to a shopping cart on any food delivery platform",
    "input_keys": ["items_to_order", "platform_context"],
    "output_keys": ["cart_contents", "cart_total"],
    "prompt_template": "Add these items to the cart: {items_to_order}. Current platform state: {platform_context}. Confirm each item was added.",
    "tools_required": ["browser"],
    "block_type": "action"
}
```

---

## Architecture Overview

```
                    ┌─────────────────┐
                    │  Block Database  │  ← Pre-created reusable blocks
                    │  (BlockDef JSON) │     with input/output contracts
                    └────────┬────────┘
                             │ lookup by block_id
                             ▼
User Intent → [Decomposition] → TaskPlan (ordered block_ids + edges)
                                    │
                                    ▼
                          [Graph Builder]  ← builds StateGraph dynamically
                                    │        one node per block, same executor fn
                                    ▼
                          [Compiled Graph]  ← MemorySaver checkpointer
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              [block_exec]    [block_exec]    [block_exec]
              reads inputs    reads inputs    reads inputs
              from state      from state      from state
              writes outputs  writes outputs  writes outputs
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                          [Long-term Store]  ← preferences & history
```

---

## Project Structure

```
lovable/
├── pyproject.toml
├── lovable/
│   ├── __init__.py
│   ├── config.py                      # Settings (API keys, LLM defaults)
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── block.py                   # BlockDefinition, BlockType, BlockReference
│   │   └── plan.py                    # TaskPlan, PlanStep, ScheduleSpec
│   │
│   ├── blocks/
│   │   ├── __init__.py
│   │   ├── store.py                   # BlockStore — CRUD for block definitions (DB/JSON)
│   │   ├── executor.py               # block_executor() — the ONE generic node function
│   │   └── builtins.py               # Pre-seeded blocks (query_memory, etc.)
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py                   # OrchestrationState (TypedDict + reducers)
│   │   ├── builder.py                 # build_graph_from_plan() — dynamic graph construction
│   │   └── registry.py               # Compiled graph cache
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── checkpointer.py           # get_checkpointer() — MemorySaver
│   │   ├── store.py                   # get_store() — InMemoryStore for long-term memory
│   │   └── manager.py                # MemoryManager — preferences & history
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   └── service.py                # get_llm(), call_llm(), call_llm_json()
│   │
│   └── decomposition/
│       ├── __init__.py
│       └── interface.py              # TaskPlan schema + mock decomposer
│
└── tests/
    ├── conftest.py
    ├── test_block_executor.py
    ├── test_graph_builder.py
    └── test_end_to_end.py
```

---

## Implementation Steps

### Step 1: Project scaffolding + dependencies

**`pyproject.toml`**:
```toml
[project]
name = "lovable"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.4",
    "langchain-openai>=0.3",
    "langchain-anthropic>=0.3",
    "langchain-core",
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.25"]
```

**`config.py`**: Pydantic `Settings` with `openai_api_key`, `anthropic_api_key`, `default_llm_provider`, `default_llm_model`, `llm_temperature`, `environment`.

Create folder structure with all `__init__.py` files.

### Step 2: Block models (`models/block.py`)

- **`BlockType`** enum: `action`, `decision`, `extraction`, `query_memory`, `wait`
- **`BlockDefinition`** (Pydantic): the full schema shown above — `block_id`, `name`, `description`, `input_keys`, `output_keys`, `prompt_template`, `tools_required`, `llm_provider`, `llm_model`, `block_type`, `branches`, `max_retries`, `timeout_seconds`, `category`, `tags`, `version`
- **`BlockReference`** (Pydantic): lightweight reference used in plans — `block_id`, `step_id` (unique within a plan), `input_mappings: dict[str, str] | None` (optional remapping of state keys to block input keys)

### Step 3: Plan models (`models/plan.py`)

- **`PlanStep`**: `step_id`, `block_id`, `depends_on: list[str]` (step_ids), `branches: dict[str, str] | None` (for decision steps — maps outcome to next step_id)
- **`TaskPlan`**: `plan_id`, `user_intent`, `steps: list[PlanStep]`, `entry_step_id`, `schedule: ScheduleSpec | None`
- **`ScheduleSpec`**: `cron_expression`, `timezone`, `human_readable`

The decomposition engine outputs a `TaskPlan` that references `block_id`s from the database. It doesn't define blocks — it just picks and orders them.

### Step 4: Block store (`blocks/store.py`)

`BlockStore` class — stores and retrieves `BlockDefinition`s:
- `get(block_id) -> BlockDefinition`
- `save(block: BlockDefinition)`
- `search(category, tags) -> list[BlockDefinition]`
- `list_all() -> list[BlockDefinition]`

Initial implementation: in-memory dict backed by JSON file. Later: Postgres/SQLite.

**`blocks/builtins.py`**: Pre-seeds the store with system blocks like `query_memory`, `save_to_memory`, etc.

### Step 5: Graph state (`graph/state.py`)

```python
def _append_list(existing: list, new: list) -> list:
    return existing + new

def _merge_dicts(existing: dict, new: dict) -> dict:
    return {**existing, **new}

class OrchestrationState(TypedDict):
    # Identity
    run_id: str
    agent_id: str
    user_id: str

    # Current block being executed (set by graph builder before each node)
    current_block: dict[str, Any]              # Serialized BlockDefinition

    # Results from completed blocks (append reducer)
    block_results: Annotated[list[dict], _append_list]

    # Shared data flowing between blocks (merge reducer)
    # Block reads its input_keys from here, writes its output_keys here
    shared_context: Annotated[dict[str, Any], _merge_dicts]

    # Long-term memory (loaded at start of run)
    user_preferences: dict[str, Any]
    user_history: list[dict[str, Any]]

    # Execution tracking
    status: str                                 # running / paused / completed / failed
    retry_count: int
    last_error: str | None
```

Key: `shared_context` is the shared bus. Every block reads its `input_keys` from here and writes its `output_keys` back here. The `_merge_dicts` reducer ensures outputs accumulate without overwriting.

### Step 6: Block executor (`blocks/executor.py`)

The single generic node function. Every node in the graph calls this:

```python
async def block_executor(state: OrchestrationState) -> dict:
    block = BlockDefinition(**state["current_block"])

    # 1. Gather inputs from shared_context
    inputs = {}
    for key in block.input_keys:
        inputs[key] = state["shared_context"].get(key, "")

    # Also inject user preferences and history
    inputs["user_preferences"] = state.get("user_preferences", {})
    inputs["user_history"] = state.get("user_history", [])

    # 2. Render prompt
    prompt = block.prompt_template.format(**inputs)

    # 3. Call LLM (provider chosen per block)
    result = await call_llm_json(
        system_prompt=f"You are executing: {block.name}. {block.description}",
        user_prompt=prompt,
        provider=block.llm_provider,
        model=block.llm_model,
    )

    # 4. Extract outputs
    outputs = {key: result.get(key) for key in block.output_keys if key in result}

    # 5. Return state update
    return {
        "block_results": [{"block_id": block.block_id, "success": True, "output": outputs}],
        "shared_context": outputs,
    }
```

### Step 7: Graph builder (`graph/builder.py`)

**`build_graph_from_plan(plan: TaskPlan, block_store: BlockStore) -> StateGraph`**:

1. Load all referenced `BlockDefinition`s from the store
2. Add fixed nodes: `load_memory`, `save_memory`, `handle_error`
3. For each `PlanStep`:
   - Create a **wrapper function** that sets `current_block` in state then calls `block_executor`:
     ```python
     def make_node(block_def):
         async def node(state):
             state_with_block = {**state, "current_block": block_def.model_dump()}
             return await block_executor(state_with_block)
         return node
     ```
   - Add as node: `builder.add_node(f"step_{step.step_id}", make_node(block_def))`
4. Wire `START → load_memory → root steps`
5. Wire inter-step edges based on `depends_on` + `branches`
6. Wire terminal steps → `save_memory → END`
7. Compile with `checkpointer=get_checkpointer()`

### Step 8: Memory (`memory/`)

**Checkpointer** (`MemorySaver`): Short-term, within-run. Enables `interrupt()`/`resume`.

**Store** (`InMemoryStore`): Long-term, cross-run. Namespaced:
```
("users", user_id, "preferences")                    → key-value pairs
("users", user_id, "agents", agent_id, "history")    → run summaries
```

**MemoryManager**: High-level interface for `get_preferences()`, `update_preferences()`, `get_history()`, `save_history()`.

### Step 9: LLM service (`llm/service.py`)

Multi-provider:
- `get_llm(provider, model) -> BaseChatModel` — returns `ChatOpenAI` or `ChatAnthropic`
- `call_llm(system, user, provider, model) -> str`
- `call_llm_json(system, user, provider, model, tools) -> dict`

### Step 10: Decomposition interface + mock (`decomposition/interface.py`)

The `TaskPlan` schema is the contract. Include `mock_decompose(intent) -> TaskPlan` that returns a hardcoded plan referencing blocks from the store. Teammate builds the real decomposition graph (a separate `StateGraph`) that outputs a `TaskPlan`.

---

## How Blocks Flow Through LangGraph — Step by Step

Given this plan: `query_memory → open_uber_eats → add_to_cart → place_order`

**1. Graph builder creates:**
```
START → load_memory → step_1 → step_2 → step_3 → step_4 → save_memory → END
         (infra)      (query    (open     (add to   (place    (infra)
                       memory)   UE)       cart)     order)
```

**2. Each step node is the same `block_executor` function**, but with a different `current_block` injected.

**3. Data flows through `shared_context`:**
```
load_memory:
  shared_context = {}  (empty)
  user_preferences = {"fav_restaurant": "Chipotle"}  (from store)

step_1 (query_memory):
  reads: shared_context["memory_query"]  →  "what did I order last time?"
  writes: shared_context["memory_results"]  →  "Chicken Bowl from Chipotle"

step_2 (open_uber_eats):
  reads: shared_context["uber_eats_credentials"]  →  loaded from preferences
  writes: shared_context["session_active"]  →  true

step_3 (add_to_cart):
  reads: shared_context["items_to_order"]  →  derived from memory_results
  reads: shared_context["platform_context"]  →  from session state
  writes: shared_context["cart_contents"], shared_context["cart_total"]

step_4 (place_order):
  reads: shared_context["cart_contents"], shared_context["cart_total"]
  writes: shared_context["order_confirmation_id"]

save_memory:
  persists shared_context to long-term store
```

**4. The `_merge_dicts` reducer** means each block's outputs accumulate without overwriting previous outputs. After all steps:
```python
shared_context = {
    "memory_results": "Chicken Bowl from Chipotle",
    "session_active": True,
    "cart_contents": [...],
    "cart_total": "$12.50",
    "order_confirmation_id": "UE-12345",
}
```

---

## End-to-End Example

**"Order my lunch from Uber Eats every Tuesday arriving at 1pm"**

1. Decomposition picks blocks from DB: `query_memory`, `open_uber_eats`, `check_previous_order` (decision), `select_restaurant`, `navigate_to_restaurant`, `add_to_cart`, `set_delivery_time`, `place_order`
2. Outputs `TaskPlan` with dependency edges and branch for the decision block
3. `build_graph_from_plan()` creates: `load_memory → step_1 → step_2 → step_3(decision) → step_4|step_5 → step_6 → step_7 → step_8 → save_memory`
4. **Run 1**: No memory → "no_preference" branch → `interrupt()` asks user → preferences saved
5. **Run 2**: Memory loaded → "has_preference" → fully automatic → history updated

---

## Verification

1. **Block executor**: Mock LLM, run `block_executor` with a block def → verify it reads inputs, calls LLM, writes outputs
2. **Graph builder**: Build graph from 3-step plan → verify topology (nodes, edges)
3. **E2E linear flow**: 3-block linear plan + mocked LLM → run graph → verify `shared_context` accumulates correctly
4. **Decision routing**: Plan with decision block → mock LLM returns each branch → verify correct path
5. **Memory round-trip**: Run → check store → new run → verify preferences loaded
6. **Interrupt/resume**: Block that fails → verify `interrupt()` → `Command(resume=...)` resumes

---

## Critical Files

| File | Purpose |
|---|---|
| `lovable/models/block.py` | BlockDefinition — the reusable block schema |
| `lovable/models/plan.py` | TaskPlan, PlanStep — how blocks are arranged into flows |
| `lovable/blocks/executor.py` | The ONE generic node function that runs any block |
| `lovable/blocks/store.py` | BlockStore — CRUD for block definitions |
| `lovable/graph/state.py` | OrchestrationState TypedDict + reducers |
| `lovable/graph/builder.py` | Dynamic graph construction from TaskPlan + block defs |
| `lovable/memory/manager.py` | Long-term memory via LangGraph Store |
| `lovable/llm/service.py` | Multi-provider LLM wrapper (OpenAI + Anthropic) |
