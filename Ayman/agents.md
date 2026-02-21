# MotherAgent — Modular AI Agent Construction Platform

## 1. System Purpose

MotherAgent converts natural language intent into structured, versioned, executable, and observable automation agents composed of reusable atomic blocks.

MotherAgent is an **agent-construction system** (“an agent to make agents”):
- It **constructs** agent graphs (decomposition → validation → versioning → persistence) in the Control Plane.
- It **does not execute** constructed agents directly.
- It **delegates all execution** to the Python Execution Plane.

All runtime execution is **non-streaming**.

---

## 2. Execution Engine Invariant (Non-Negotiable)

**All executable agents in MotherAgent must run on LangGraph (Python).**

This includes:
- User-created agents
- System agents (internal orchestration agents)
- Sub-agents / nested agents
- Any future meta-agents that perform runtime steps

There is **no alternative execution path** (no “lightweight” executor, no direct Node execution).

---

## 3. Cost Attribution Constraint (Paid AI)

MotherAgent uses **Paid AI** for cost tracing and margin tracking.

Paid traces LLM costs by **intercepting native provider SDK calls**. Therefore:

- **All LLM calls must use native SDKs directly** (e.g., OpenAI SDK, Anthropic SDK).
- **Do not route LLM calls through abstraction layers** that wrap/replace SDK calls (e.g., LangChain LLM wrappers, LlamaIndex, similar).
- LLM calls should be centralized through a shared **`llm_utils`** module that calls provider SDKs directly.
- LLM calls are **non-streaming**.

This ensures Paid cost attribution is complete and accurate.

---

## 4. System Architecture (Control Plane vs Execution Plane)

### Control Plane (Node/TypeScript)
Owns:
- AgentDefinition (canonical source of truth)
- Block definitions + versioning
- Prompt intake + decomposition requests
- Validation + safety checks
- Memory persistence orchestration
- Triggering/scheduling orchestration
- Execution request assembly + dispatch (REST)

Node/TypeScript never executes an agent DAG.

### Execution Plane (Python/LangGraph)
Owns:
- DAG → LangGraph compilation at runtime
- Deterministic graph execution (non-streaming LLM calls)
- State transitions + routing
- Block/tool invocation
- Structured execution results

Python runtime is **stateless and ephemeral**:
- Receives an explicit AgentDefinition version + inputs
- Executes
- Returns structured results
- Does not persist to PostgreSQL

---

## 5. High-Level Architecture

User
  ↓
Frontend (Next.js)
  ↓
Backend API (Node/TypeScript)
  ↓
PostgreSQL (AgentDefinition — Source of Truth)
  ↓
Trigger Fires
  ↓
REST Call → Python LangGraph Runtime
  ↓
Graph Execution (LangGraph)
  ↓
Execution Result Returned
  ↓
Node Persists Execution Logs + Memory Writes

---

## 6. Tech Stack

### Frontend
- Next.js (App Router)
- React
- TypeScript
- TailwindCSS

### Control Plane (Node/TypeScript)
- Node.js
- TypeScript
- Fastify or NestJS
- Prisma ORM
- PostgreSQL
- Redis
- Zod validation
- OpenAI / Anthropic for **decomposition only** (non-streaming)

### Execution Plane (Python)
- Python 3.11+
- FastAPI (REST)
- LangGraph
- Pydantic
- Uvicorn
- **UV** (dependency + environment management)
- Native provider SDKs only:
  - OpenAI Python SDK
  - Anthropic Python SDK (if used)

Python dependency management:
- All Python dependencies managed via `uv`
- `pyproject.toml` is authoritative
- Lockfile must be committed
- No ad-hoc `pip install` in dev/CI

---

## 7. Canonical Models

### 7.1 AgentDefinition (Source of Truth)

```ts
interface AgentDefinition {
  id: string
  version: string
  dag: DAG
  triggers: Trigger[]
  createdAt: Date
}
```

Execution binds to a specific version.

### 7.2 Block (Versioned & Immutable)

```ts
interface Block {
  id: string
  version: string
  name: string
  type: BlockType
  inputSchema: JSONSchema
  outputSchema: JSONSchema
  executionType: "http" | "internal" | "llm"
  executionConfig: object
}
```

Rules:
- Blocks are immutable once published
- Any change creates a new block version
- Blocks do not call other blocks directly

---

## 8. REST Execution Contract (Node → Python)

### 8.1 Execution Request

```json
{
  "agentId": "uuid",
  "version": "1.2.0",
  "dag": { },
  "blocks": { },
  "initialState": { },
  "executionId": "uuid"
}
```

### 8.2 Execution Response

```json
{
  "executionId": "uuid",
  "status": "success",
  "finalState": { },
  "blockLogs": [
    {
      "blockId": "block_x",
      "status": "success",
      "durationMs": 1234,
      "output": { }
    }
  ],
  "error": null
}
```

Python never writes to the database directly.

---

## 9. Execution Model

Trigger
  → Load AgentDefinition (explicit version)
  → Load Memory Snapshot
  → Send REST ExecutionRequest
  → Python compiles DAG → LangGraph
  → Execute LangGraph (non-streaming LLM calls via native SDKs)
  → Return ExecutionResponse
  → Node persists execution logs + memory writes

Graph is compiled per execution and never persisted as a runtime artifact.

---

## 10. Determinism Rules

Given:
- Same AgentDefinition version
- Same initial state

Execution must produce identical structured outputs (excluding timestamps and generated IDs).

---

## 11. Non-Goals

- Any executor other than LangGraph
- Streaming responses (for now)
- LLM abstraction layers that prevent Paid SDK interception
- Python persistence to PostgreSQL
- Self-modifying graphs
- Runtime graph mutation
