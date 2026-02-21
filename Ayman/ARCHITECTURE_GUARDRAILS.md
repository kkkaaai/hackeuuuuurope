
# MotherAgent — Architecture Guardrails

These rules are non-negotiable and must be enforced in code review and CI.

---

## 1. LangGraph Everywhere Rule (Execution Engine Invariant)

All executable agents in MotherAgent must run on **LangGraph (Python)**.

This includes:
- User-created agents
- Sub-agents / nested agents
- System agents
- Any future meta-agents

Reject any attempt to introduce:
- A second execution engine
- Direct agent execution in Node/TypeScript
- “Simple mode” bypassing LangGraph

---

## 2. Source of Truth Rule

The only authoritative agent representation is AgentDefinition stored in PostgreSQL.

Execution must bind to an explicit AgentDefinition version.

---

## 3. Control Plane vs Execution Plane Rule

Python FastAPI (Control Plane):
- Owns persistence
- Owns versioning
- Owns validation
- Owns orchestration
- Connects to Supabase/PostgreSQL
- Connects to S3 for file workflows

Python (Execution Plane):
- Owns graph execution only
- Is stateless and ephemeral
- Must not mutate AgentDefinition
- Must not generate new blocks
- Must not connect to Supabase/PostgreSQL
- Must not connect to S3

Node/TypeScript is not a control-plane runtime.

---

## 4. Infrastructure Lock Rule

- Supabase is the system of record for auth + PostgreSQL + pgvector
- S3 is the blob storage for per-user files

---

## 5. Knowledge Substrate Rule

- Block DB + reference packages are the core knowledge substrate
- Retrieval and prompt assembly must use these sources

---

## 6. Embed-Based Prompt Injection Rule

Embed-based prompt injection is the primary intelligence mechanism and must be used for:
- Decomposition
- Block-checker
- Runtime execution

---

## 7. Repo Structure Rule

The repository must preserve this structure:
- `apps/web` (Next.js frontend)
- `apps/api` (Python FastAPI control plane)
- `packages/block_db`
- `packages/reference_packages`
- `packages/prompt_injection`

---

## 8. REST Boundary Rule

All cross-service communication must:
- Be JSON serializable
- Include explicit versions (agent + blocks + schema)
- Be schema validated (Zod in Node, Pydantic in Python)
- Never rely on implicit “latest” lookups

---

## 9. Paid AI Cost Tracing Rule (Native SDK Only)

Paid AI traces costs by intercepting **native provider SDK calls**.

Therefore:
- All LLM calls must use native SDKs directly (OpenAI SDK, Anthropic SDK).
- Do not route LLM calls through wrappers/abstractions that hide SDK calls (LangChain model wrappers, LlamaIndex, similar).
- LLM calls are **non-streaming** (for now).
- LLM calls must be centralized through a shared `llm_utils` module to standardize attribution metadata.

Any PR that introduces wrapper-based LLM routing is a blocker.

---

## 10. Versioning Rule

- Blocks are immutable
- AgentDefinitions are immutable
- All updates create new versions
- No in-place mutation

---

## 11. LangGraph Isolation Rule

- Graph compiled fresh per execution
- No runtime graph mutation
- No dynamic tool injection
- Max step limits enforced
- No self-modifying graphs

---

## 12. Python Dependency Rule (UV)

- All Python dependencies must be managed with UV
- `pyproject.toml` is authoritative
- Lockfile must be committed
- No direct pip installs
- Environments must be reproducible across dev + CI

---

## 13. LLM Containment Rule

LLMs may:
- Generate structured metadata and decomposition outputs

LLMs may NOT:
- Generate executable runtime code
- Bypass schema validation
- Modify persisted data directly

---

## 14. Determinism Rule

Given the same AgentDefinition version and same initial state,
execution must produce identical structured results (excluding timestamps and generated IDs).
