# Merge Plan: Kai + Magnus → Demo

## Context

Two teammates built parallel implementations of AgentFlow — an AI agent creation platform. **Kai** built a polished Next.js frontend + LangGraph-based backend with 35+ blocks. **Magnus** built a simpler backend (no LangChain, direct SDK calls) with SSE streaming and a "Thinker left / Doer right" visualization with a 4-stage progress bar. We need to merge the best of both into `Demo/`.

**Goal**: Use Kai's Next.js frontend as the shell, add Magnus's real-time thinker/doer visualization, use Magnus's backend (no LangChain), port all 35+ of Kai's block definitions, use `uv` for Python deps.

---

## Structure

```
Demo/
├── backend/                    # Magnus's backend (enhanced)
│   ├── main.py                 # FastAPI + new pipeline CRUD endpoints
│   ├── pyproject.toml          # uv-based (already exists)
│   ├── .env.example
│   ├── engine/                 # Thinker (4-stage) + Doer (topological)
│   ├── llm/                    # Direct OpenAI/Anthropic SDK
│   ├── registry/               # Block registry + enriched blocks.json
│   ├── storage/                # In-memory store + pipeline store
│   ├── blocks/                 # Block implementations
│   └── tests/
├── frontend/                   # Kai's Next.js (adapted)
│   ├── src/app/chat/           # REWRITTEN: Agent Studio with split pane
│   ├── src/app/dashboard/      # Adapted for new API
│   ├── src/app/blocks/         # Adapted for Magnus's block format
│   ├── src/app/activity/       # Adapted for new API
│   ├── src/app/pipelines/      # Adapted (edge format fix)
│   ├── src/components/thinker/ # NEW: ThinkerLog + StageProgressBar
│   ├── src/components/pipeline/# Kept from Kai (React Flow)
│   ├── src/lib/sse.ts          # NEW: SSE streaming client
│   ├── src/lib/api.ts          # REWRITTEN for Magnus's API
│   ├── src/lib/types.ts        # EXTENDED with SSE event types
│   └── src/lib/utils.ts        # MODIFIED: edge format normalization
└── README.md
```

---

## Step 1: Copy Magnus's Backend → `Demo/backend/`

Copy entire `/magnus/backend/` to `Demo/backend/`. This includes:
- `main.py` — FastAPI app
- `engine/` — thinker.py, thinker_stream.py, doer.py, executor.py, resolver.py, schemas.py, state.py, memory.py
- `llm/service.py` — OpenAI/Anthropic SDK wrapper
- `registry/` — registry.py, blocks.json, custom_blocks.json
- `storage/memory.py` — in-memory store
- `blocks/` — filter_threshold, conditional_branch, memory_read, memory_write, notify_push, custom/
- `tests/` — full test suite
- `pyproject.toml` — already uv-based

**Key files**: `magnus/backend/main.py`, `magnus/backend/engine/thinker_stream.py`

---

## Step 2: Port Kai's Block Definitions into `blocks.json`

Convert all 35 blocks from Kai's 7 JSON files (`Kai/app/blocks/definitions/*.json`) into Magnus's block format and merge into `Demo/backend/registry/blocks.json`.

**Format conversion per block:**
- Remove Kai-only fields: `organ`, `api_type`, `tier`
- Add Magnus fields: `execution_type` ("llm"), `use_when`, `tags`, `metadata`
- Add `prompt_template` for LLM blocks (derived from description + I/O schema)
- Map Kai categories → Magnus categories where they differ

**Source files**: `Kai/app/blocks/definitions/{triggers,perceive,think,act,communicate,remember,control_flow}.json`
**Target file**: `Demo/backend/registry/blocks.json`

---

## Step 3: Add Pipeline CRUD + Activity Endpoints to Backend

Kai's frontend expects endpoints Magnus doesn't have. Add to `Demo/backend/main.py`:

1. **In-memory pipeline store** (dict in `storage/memory.py`)
2. **`GET /api/pipelines`** — list saved pipelines
3. **`GET /api/pipelines/{id}`** — get pipeline detail
4. **`POST /api/pipelines`** — save pipeline (from thinker output)
5. **`DELETE /api/pipelines/{id}`** — delete pipeline
6. **`POST /api/pipelines/{id}/run`** — run saved pipeline
7. **`POST /api/blocks/search`** — search blocks by query string
8. **`GET /api/executions`** — list recent execution runs
9. **`GET /api/executions/{run_id}`** — get execution detail
10. **`GET /api/notifications`** — list notifications (from notify_push block)
11. **`POST /api/notifications/{id}/read`** — mark read

These are thin wrappers around existing functionality. Store pipelines, executions, and notifications in memory dicts.

---

## Step 4: Copy Kai's Frontend → `Demo/frontend/`

Copy entire `/Kai/frontend/` to `Demo/frontend/`. This brings:
- Next.js 16 + React 19 + Tailwind 4 + React Flow 11 + Framer Motion
- All 5 pages: /chat, /dashboard, /pipelines/[id], /blocks, /activity
- Components: PipelineGraph, BlockNode, PipelineResultDisplay, Sidebar
- Dark theme and all styling

**No changes yet** — just the copy.

---

## Step 5: Update TypeScript Types (`lib/types.ts`)

Extend the existing types to support Magnus's API format:

- Add SSE event types: `ThinkerStage`, `SSEEvent`, `StageEvent`, `StageResultEvent`, `LLMPromptEvent`, `LLMResponseEvent`, `BlockCreatedEvent`, `CompleteEvent`
- Add Magnus pipeline types: `MagnusPipelineNode` (same as existing but without `config`), `MagnusPipelineEdge` (`{from, to}` instead of `{from_node, to_node}`)
- Update `BlockDefinition` to include `execution_type`, `use_when`, `tags`, `prompt_template` (Magnus fields)
- Keep all existing types for backward compat with other pages

---

## Step 6: Create SSE Client (`lib/sse.ts`) — NEW FILE

Reusable SSE client for streaming from Magnus's `/api/create-agent/stream`:

- `streamSSE(url, body, onEvent, onError?, onComplete?)` function
- Uses `fetch()` with `ReadableStream` reader
- Parses `event:` and `data:` lines from SSE format
- Calls `onEvent(eventType, parsedData)` for each event

Port logic from Magnus's `static/index.html` event rendering (lines 950-973) into TypeScript.

---

## Step 7: Rewrite API Client (`lib/api.ts`)

Replace all API functions to target Magnus's backend:

| Kai Function | → | Magnus Endpoint |
|---|---|---|
| `sendChat({message})` | → | `createAgentStream(intent)` via SSE |
| `savePipeline(pipeline)` | → | `POST /api/pipelines` |
| `runPipeline(id)` | → | `POST /api/pipelines/{id}/run` |
| `listPipelines()` | → | `GET /api/pipelines` |
| `deletePipeline(id)` | → | `DELETE /api/pipelines/{id}` |
| `listBlocks()` | → | `GET /api/blocks` (same) |
| `searchBlocks(query)` | → | `POST /api/blocks/search` |
| `listExecutions()` | → | `GET /api/executions` |
| `getExecution(id)` | → | `GET /api/executions/{run_id}` |
| `listNotifications()` | → | `GET /api/notifications` |

Also add `createAgent(intent)` (non-streaming) and `runPipelineDirect(pipeline, userId)` for the direct pipeline run.

---

## Step 8: Update `lib/utils.ts` — Edge Format Normalization

The `layoutPipeline()` function currently reads `e.from_node` / `e.to_node`. Magnus's backend returns `e.from` / `e.to`.

Fix: Normalize edges in `layoutPipeline()`:
```ts
const from = (e as any).from_node || (e as any).from;
const to = (e as any).to_node || (e as any).to;
```

Also modify `setBlockMetadata()` to **merge** instead of **replace** (needed for incremental SSE updates):
```ts
export function addBlockMetadata(blocks) {
  for (const b of blocks) {
    blockMetadataCache[b.id] = { name: b.name, category: b.category };
  }
}
```

---

## Step 9: Create Thinker Components — NEW FILES

### `components/thinker/StageProgressBar.tsx`
- Horizontal bar with 4 stages: Decompose → Match → Create → Wire
- Animated dots (pulse on active, green on complete, gray on pending)
- Connecting lines between stages
- Props: `currentStage`, `completedStages: Set<string>`

### `components/thinker/ThinkerLog.tsx`
- Scrollable log panel showing SSE events in real-time
- Each event type gets styled differently:
  - `stage` → Header with stage name
  - `llm_prompt` → Collapsible system/user prompt
  - `llm_response` → Collapsible raw response + elapsed time
  - `match_found` → Green badge with block name
  - `match_missing` → Orange badge
  - `block_created` → Purple badge with new block name
  - `validation` → Check/X icon
  - `complete` → Success message
- Auto-scrolls to bottom on new events
- Empty state: brain icon + "Waiting for Thinker..."

Port styling from Magnus's `static/index.html` event rendering (lines 983-1073).

---

## Step 10: Rewrite Chat Page as Agent Studio (`app/chat/page.tsx`)

This is the core merge — replace Kai's chat-style interface with the split-pane thinker/doer layout.

**Layout:**
```
┌─────────────────────────────────────────────────┐
│  Header: "Agent Studio" + description           │
├─────────────────────────────────────────────────┤
│  Input bar: textarea + "Create Agent" button    │
├─────────────────────────────────────────────────┤
│  StageProgressBar (Decompose → Match → ... )    │
├────────────────────┬────────────────────────────┤
│  ThinkerLog (left) │ PipelineGraph (right)      │
│  SSE event stream  │ React Flow DAG             │
│                    │                             │
├────────────────────┴────────────────────────────┤
│  [Run Pipeline] button when pipeline ready      │
├─────────────────────────────────────────────────┤
│  Execution Results (PipelineResultDisplay)      │
└─────────────────────────────────────────────────┘
```

**State machine** (`useReducer`):
- Phases: `idle` → `thinking` → `ready` → `executing` → `complete` → `error`
- State: `events[]`, `currentStage`, `completedStages`, `pipeline`, `blockDefs`, `nodeStatuses`, `executionResult`

**Flow:**
1. User types intent → clicks "Create Agent"
2. `streamSSE("/api/create-agent/stream", ...)` opens
3. SSE events populate left panel (ThinkerLog) + progress bar animates
4. On `match_found` / `block_created` → block metadata cached
5. On `complete` → pipeline renders in right panel (PipelineGraph)
6. User clicks "Run Pipeline" → `POST /api/pipelines/{id}/run`
7. Nodes animate running → completed in the graph
8. Results display below in PipelineResultDisplay

Keep example prompts from Kai's idle state UI.

---

## Step 11: Adapt Remaining Pages

### `/blocks` page
- Remove Kai-specific `organ`, `tier` references
- Show `execution_type` badge (LLM / Python) instead
- Show `use_when` and `tags` in expanded view
- Category mapping: Magnus's `input`→`perceive`, `process`→`think`, `action`→`act`

### `/dashboard` page
- Update to call new pipeline CRUD endpoints
- Show `user_prompt` instead of `user_intent` from pipeline data
- Run pipeline calls `POST /api/pipelines/{id}/run`

### `/pipelines/[id]` page
- Edge format normalization (handled by Step 8 utils fix)
- Load pipeline from `GET /api/pipelines/{id}`

### `/activity` page
- Update to call `GET /api/executions` and `GET /api/notifications`
- Adapt response shape to match Magnus's format

### `Sidebar.tsx`
- Update footer text to dynamically show block count or "AgentFlow Demo"

---

## Step 12: Update `next.config.ts`

Add specific SSE route before the wildcard to prevent buffering:
```ts
rewrites() {
  return [
    { source: "/api/create-agent/stream", destination: "http://localhost:8000/api/create-agent/stream" },
    { source: "/api/:path*", destination: "http://localhost:8000/api/:path*" },
    { source: "/health", destination: "http://localhost:8000/health" },
  ];
}
```

---

## Step 13: Create `.env.example` and `README.md`

**`Demo/.env.example`:**
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_PROVIDER=openai
DEFAULT_MODEL=gpt-4o
LLM_TEMPERATURE=0.0
PAID_API_KEY=
```

**`Demo/README.md`:** Quick start instructions for running the demo.

---

## Verification

1. **Backend health**: `curl http://localhost:8000/health` → `{"status": "ok"}`
2. **Block count**: `curl http://localhost:8000/api/blocks | python -c "import sys,json; print(len(json.load(sys.stdin)))"` → 35+
3. **SSE streaming**: `curl -X POST http://localhost:8000/api/create-agent/stream -H 'Content-Type: application/json' -d '{"intent":"search for AI news","user_id":"test"}'` → stream of events
4. **Frontend renders**: Open http://localhost:3000 → Agent Studio loads
5. **Full flow**: Type intent → stage bar animates → thinker log streams → pipeline appears → run → results display
6. **Secondary pages**: /blocks shows enriched library, /dashboard lists pipelines, /activity shows runs

**Startup:**
```bash
# Backend
cd Demo/backend
cp .env.example .env   # Fill in API keys
uv sync
uv run uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd Demo/frontend
npm install
npm run dev
```

---

## Implementation Order

| # | Step | Depends On | Parallelizable |
|---|------|-----------|----------------|
| 1 | Copy Magnus backend | - | Yes |
| 4 | Copy Kai frontend | - | Yes with 1 |
| 2 | Port Kai's block definitions | 1 | Yes with 4 |
| 3 | Add pipeline CRUD endpoints | 1 | Yes with 4-6 |
| 5 | Update TypeScript types | 4 | Yes with 2-3 |
| 6 | Create SSE client | 4 | Yes with 2-3 |
| 7 | Rewrite API client | 5 | - |
| 8 | Fix utils.ts edge format | 5 | Yes with 7 |
| 9 | Create Thinker components | 5, 6 | Yes with 7-8 |
| 10 | Rewrite Agent Studio page | 7, 8, 9 | - |
| 11 | Adapt remaining pages | 7, 8 | Yes with 10 |
| 12 | Update next.config.ts | 4 | Yes with anything |
| 13 | Create .env.example + README | 1 | Yes with anything |
