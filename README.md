# AgentFlow

An AI agent creation and execution platform. Users describe automations in plain English, and the system decomposes the intent into composable blocks, wires them into a pipeline DAG, and executes it.

## How It Works

```
User: "Summarize the top Hacker News posts every morning"

        ┌───────────────────────────────┐
        │  THINKER (LangGraph 1)        │
        │  intent → decompose → match   │
        │  → wire → Pipeline JSON       │
        └──────────────┬────────────────┘
                       │
                 Pipeline JSON
                       │
        ┌──────────────▼────────────────┐
        │  DOER (LangGraph 2)           │
        │  web_search → summarize →     │
        │  notify (parallel DAG)        │
        └───────────────────────────────┘
```

**Thinker** — Converts natural language into a Pipeline JSON (a DAG of reusable blocks).
**Doer** — Executes the pipeline by running blocks in topological order with parallel batching.

## Quick Start

```bash
cd backend
uv sync
cp .env.example .env   # fill in API keys
uvicorn main:app --reload
```

## Project Structure

```
backend/          # FastAPI server, engine, blocks, tests
  engine/         # Thinker + Doer pipelines, resolver, executor
  blocks/         # Python block implementations
  registry/       # Block registry + seed definitions
  llm/            # OpenAI/Anthropic integration
  tests/          # Test suite (34 tests)
```

See [backend/README.md](backend/README.md) for full API docs, architecture details, and implementation status.
