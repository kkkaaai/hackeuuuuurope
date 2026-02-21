# HackEurope Task Automation System

## Overview

This system provides three core functionalities for building AI-powered task automation:

1. **Task Decomposition** - Break down complex tasks into structured execution plans
2. **Sample Generation** - Generate synthetic tasks for testing and development
3. **Prompt Injection** - Query-powered semantic block retrieval for LLM prompts

---

## Quick Links

- **[Task Decomposition Documentation](./TASK_DECOMPOSITION.md)** - Complete guide to IO-driven task decomposition
- **[Sample Generation Documentation](./SAMPLE_GENERATION.md)** - Generate test task samples
- **[Prompt Injection Documentation](./PROMPT_INJECTION.md)** - Semantic block retrieval and prompt population

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   SAMPLE GENERATION                      │
│                  generate_requests.py                    │
│                          ↓                               │
│                  sample_requests/                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  TASK DECOMPOSITION                      │
│                                                          │
│  clean_requests.py → cleaned_requests/                  │
│         ↓                                                │
│  clean_dd_requests.py → dd_requests/                    │
│         ↓                                                │
│  run_io_dd_decomposition.py → execution_plan + AEB      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  PROMPT INJECTION                        │
│                                                          │
│  block_retriever.py → Semantic block search             │
│         ↓                                                │
│  prompt_injector.py → Dynamic prompt population         │
│         ↓                                                │
│  flow_creator.py → LLM-powered flow generation          │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Generate Sample Tasks

```bash
python Alex/generate_requests.py 50
```

### 2. Decompose Tasks

```bash
# Clean and prepare tasks
python Alex/clean_requests.py
python Alex/clean_dd_requests.py

# Run decomposition
python Alex/io_decomposition/run_io_dd_decomposition.py
```

### 3. Use Prompt Injection

```python
from prompt_injector import inject_prompt

template = load_template()
full_prompt = inject_prompt(template, "search and summarize")
response = llm.call(full_prompt)
```

---

## Project Structure

```
hackeurope-26/
├── docs/                           # Documentation (this folder)
│   ├── README.md                   # This file
│   ├── TASK_DECOMPOSITION.md       # Task decomposition guide
│   ├── SAMPLE_GENERATION.md        # Sample generation guide
│   └── PROMPT_INJECTION.md         # Prompt injection guide
│
├── Alex/                           # Core system implementation
│   ├── sample_requests/            # Generated sample tasks
│   ├── cleaned_requests/           # Cleaned/normalized tasks
│   ├── dd_requests/                # Dependency-driven tasks
│   ├── io_decomposition/           # Decomposition scripts
│   │   ├── run_io_dd_decomposition.py
│   │   └── io_task_decomposer.py
│   ├── generate_requests.py        # Sample generator
│   ├── clean_requests.py           # Request cleaner
│   ├── clean_dd_requests.py        # DD structure creator
│   ├── prompt_injector.py          # Prompt injection logic
│   ├── block_retriever.py          # Block retrieval
│   ├── flow_creator.py             # Flow creation
│   ├── model_tiers.py              # AI model configuration
│   ├── decomposition_engine_v2.json # V2 engine config
│   └── decomposition_engine_v3.json # V3 engine config (current)
│
├── sample_requests/                # Root sample directory
├── Demo/                           # Demo application
│   ├── backend/                    # FastAPI backend
│   └── frontend/                   # Next.js frontend
│
└── Ayman/                          # Architecture specs
    ├── agents.md                   # MotherAgent spec
    └── ARCHITECTURE_GUARDRAILS.md  # Architecture rules
```

---

## Core Technologies

| Component | Technology |
|-----------|-----------|
| Task Decomposition | Python 3.8+, OpenAI SDK |
| Prompt Injection | Python 3.8+, NVIDIA Embeddings |
| Sample Generation | Python 3.8+ |
| Model Selection | Tiered AI (Qwen, DeepSeek) |
| Backend (Demo) | FastAPI, Python 3.11+, uv |
| Frontend (Demo) | Next.js 16, React 19, TypeScript |

---

## Key Features

### Task Decomposition
- ✅ IO-driven execution planning
- ✅ Structured input/output dependencies
- ✅ Dependency chain validation
- ✅ Atomic Execution Block (AEB) analysis
- ✅ Tiered AI model selection
- ✅ V3 leaf-node strategy (recommended)

### Sample Generation
- ✅ Synthetic task generation
- ✅ Multiple complexity levels
- ✅ Various task categories
- ✅ Batch generation support

### Prompt Injection
- ✅ Semantic block retrieval
- ✅ Query-powered search (embeddings)
- ✅ Dynamic prompt population
- ✅ Metadata tracking
- ✅ Flexible API (functions + class)
- ✅ FlowCreator integration

---

## Configuration

### Environment Setup

Create a `.env` file in the `Alex/` directory:

```env
# NVIDIA API Key (for decomposition)
NVAPI_KEY=your_nvidia_api_key

# Optional: Anthropic/OpenAI for other components
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
```

### Model Tier Configuration

Edit `Alex/model_tiers.py` to customize AI model selection:

```python
COMPLEXITY_TIERS = [
    {"min": 80, "max": 100, "model": "AI2", "description": "Very Complex"},
    {"min": 60, "max": 80, "model": "AI1", "description": "Complex"},
    {"min": 40, "max": 60, "model": "AI2", "description": "Moderate"},
    {"min": 0, "max": 40, "model": "AI1", "description": "Simple"},
]

AI_MODELS = {
    "AI1": "qwen/qwen3-235b-a22b",
    "AI2": "deepseek-ai/deepseek-v3.2",
}
```

---

## Common Workflows

### Full Decomposition Pipeline

```bash
# 1. Generate samples
python Alex/generate_requests.py 20

# 2. Clean requests
python Alex/clean_requests.py

# 3. Create DD structure
python Alex/clean_dd_requests.py

# 4. Run decomposition
cd Alex
python -u io_decomposition/run_io_dd_decomposition.py
```

### Single Task Decomposition

```bash
cd Alex
python io_decomposition/run_io_dd_decomposition.py filename.json
```

### Prompt Injection in Code

```python
from prompt_injector import inject_prompt_with_metadata

template = load_template()
full_prompt, metadata = inject_prompt_with_metadata(
    template,
    "search and summarize news",
    num_blocks=5
)

print(f"Retrieved {metadata['num_retrieved']} blocks")
response = llm.call(full_prompt)
```

---

## Performance

| Operation | Time |
|-----------|------|
| Sample generation (100 tasks) | ~1s |
| Task cleaning (100 tasks) | ~2s |
| Single task decomposition | ~3-5s |
| Batch decomposition (59 tasks) | ~5-6 min |
| Block retrieval (query) | ~250ms |
| Prompt injection | ~250ms |

---

## Dependencies

### Core Dependencies
- Python 3.8+
- `openai` - NVIDIA API client
- `numpy` - Numerical operations

### Demo Dependencies
- Python 3.11+ with `uv`
- FastAPI, Pydantic, Uvicorn
- Next.js 16, React 19, TypeScript
- TailwindCSS 4, React Flow 11

---

## Testing

### Test Task Decomposition
```bash
cd Alex
python io_decomposition/run_io_dd_decomposition.py test_task.json
```

### Test Prompt Injection
```bash
cd Alex
python prompt_injector.py
```

### Test Sample Generation
```bash
python Alex/generate_requests.py 10
```

---

## Validation Rules

### Task Decomposition Validation
- ✓ Sequential step numbers (1, 2, 3...)
- ✓ All step inputs reference valid sources
- ✓ All outputs are observable and verifiable
- ✓ Proper dependency chaining
- ✓ Structured input metadata

### Prompt Injection Validation
- ✓ Similarity threshold filtering (default: 0.4)
- ✓ Top-K block retrieval (default: 5)
- ✓ Placeholder replacement
- ✓ Query appending

---

## Troubleshooting

### Task Decomposition Issues

**Problem:** Decomposition fails with API error
**Solution:** Check your `NVAPI_KEY` in `.env` file

**Problem:** Invalid dependency chains
**Solution:** Use V3 engine (leaf-node strategy) for cleaner results

### Prompt Injection Issues

**Problem:** No blocks retrieved
**Solution:** Lower similarity threshold or use more generic query

**Problem:** Wrong blocks retrieved
**Solution:** Improve block descriptors to be more specific

---

## Migration Notes

### From V2 to V3 Decomposition Engine

V3 (leaf-node terminal) is now the recommended strategy:
- Stops at USER-CONTROLLED and SYSTEM-RETRIEVABLE inputs
- No recursive decomposition of DERIVABLE inputs
- Cleaner, more practical execution plans

To switch to V3 (default):
```python
# In io_task_decomposer.py
decompose_task_io(..., engine_version="v3")
```

---

## Contributing

When adding new functionality:

1. **Task Decomposition** - Add to `Alex/io_decomposition/`
2. **Sample Generation** - Extend `generate_requests.py`
3. **Prompt Injection** - Extend `prompt_injector.py` or `block_retriever.py`

Update corresponding documentation in `docs/`.

---

## License

[Add license information]

---

## Support

For issues or questions:
- Check the detailed documentation in `docs/`
- Review example outputs in `dd_requests/`
- Test with sample generation first

---

## Version History

- **v3.0** - Leaf-node terminal strategy (current)
- **v2.0** - Recursive derivable strategy (deprecated)
- **v1.0** - Initial IO-driven decomposition

---

**Last Updated:** 2026-02-21
