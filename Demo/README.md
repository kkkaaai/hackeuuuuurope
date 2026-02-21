# AgentFlow Demo

Type what you want automated. We build and run it.

AgentFlow is an AI-powered automation platform that decomposes user intent into executable pipelines using a Thinker/Doer architecture.

## Quick Start

### Backend

```bash
cd backend
cp .env.example .env   # Fill in your API keys
uv sync
uv run uvicorn main:app --reload --port 8000
```

### Frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to use the Agent Studio.

## Architecture

- **Thinker**: Decomposes user intent into a pipeline through 4 stages (Decompose, Match, Create, Wire)
- **Doer**: Executes the pipeline DAG in topological order
- **SSE Streaming**: Real-time progress events during pipeline creation
- **Block Library**: 42 reusable blocks across 7 categories

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.11+, uv |
| Frontend | Next.js 16, React 19, TypeScript |
| Visualization | React Flow, dagre, Framer Motion |
| Styling | Tailwind CSS 4 (dark theme) |
| LLM | OpenAI / Anthropic SDK (direct, no LangChain) |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/create-agent/stream` | SSE streaming agent creation |
| `POST /api/create-agent` | Non-streaming agent creation |
| `POST /api/pipeline/run` | Execute a pipeline |
| `GET /api/blocks` | List all blocks |
| `GET /api/pipelines` | List saved pipelines |
| `POST /api/pipelines/{id}/run` | Run a saved pipeline |
| `GET /api/executions` | Execution history |
| `GET /api/notifications` | Notifications |
