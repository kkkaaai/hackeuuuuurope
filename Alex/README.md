# Alex Task Decomposition System

## Overview

This system decomposes complex tasks into structured, executable plans with explicit input/output dependencies and proper chaining.

## System Architecture

### Core Components

1. **Task Input** → `sample_requests/` directory
2. **Request Cleaning** → `cleaned_requests/` directory  
3. **Dependency-Driven (DD) Structure** → `dd_requests/` directory
4. **Execution Planning** → V2 (recursive) and V3 (leaf-node) engines

### Directory Structure

```
Alex/
├── cleaned_requests/        # Cleaned/normalized tasks
├── dd_requests/             # Dependency-driven decompositions (final output)
├── io_decomposition/        # Core decomposition scripts
│   ├── run_io_dd_decomposition.py   # Main batch runner
│   ├── io_task_decomposer.py        # Decomposition logic
│   └── run_recursive_requirements.py # Recursive decomposer
├── logs/                    # System logs
├── decomposition_engine_v2.json     # Recursive derivable strategy
├── decomposition_engine_v3.json     # Leaf-node terminal strategy
├── clean_requests.py        # Request cleaner
├── clean_dd_requests.py     # DD structure generator
├── generate_requests.py     # Sample task generator
├── model_tiers.py           # AI model tier configuration
└── complexity_evaluator.py  # Task complexity analysis
```

## Execution Workflow

### 1. Generate Sample Tasks
```bash
python Alex/generate_requests.py
```
Generates sample tasks in `sample_requests/` directory.

### 2. Clean Requests
```bash
python Alex/clean_requests.py
```
Normalizes tasks and saves to `cleaned_requests/`.

### 3. Create DD Structure
```bash
python Alex/clean_dd_requests.py
```
Converts cleaned tasks to dependency-driven format in `dd_requests/`.
Each task has:
- `task_id`: Unique identifier
- `input`: Task description
- `required_inputs`: [] (initially empty)
- `outputs`: ["result"]
- `subtasks`: [] (flat structure)
- `dependency_structure`: Dependency graph

### 4. Run IO Decomposition
```bash
cd "c:\Users\AlexL\OneDrive\Documents\Repos\hackeurope-new\hackeurope-26\Alex"
python -u io_decomposition/run_io_dd_decomposition.py
```

This processes all 59 tasks and populates:
- **execution_plan**: Contains inputs, outputs, and ordered steps
- **aeb_analysis**: Atomic Execution Block validation

## Decomposition Strategies

### V2: Recursive Derivable (Deprecated - use V3)
- Decomposes ALL inputs recursively
- Continues decomposing DERIVABLE inputs until all leaves are USER/SYSTEM
- More detailed but verbose

### V3: Leaf-Node Terminal (Current)
- Only decomposes DERIVABLE inputs
- Stops immediately at USER-CONTROLLED and SYSTEM-RETRIEVABLE inputs
- Cleaner, more practical execution plans

**Use V3 for all new decompositions.**

## Input/Output Structure

### Parsed Inputs (Structured Format)

Each input is parsed into a structured object:

```json
{
  "name": "Sales Targets",
  "source_type": "USER-CONTROLLED",
  "source_origin": "Marketing Leadership Team",
  "input_data": "Numeric revenue targets per product category",
  "bound_reference": "None"
}
```

**Source Types:**
- `USER-CONTROLLED`: Requires explicit user provision
- `SYSTEM-RETRIEVABLE`: Retrieved from external API/database
- `DERIVABLE`: Computed from other inputs (marked [DEPTH STOP])

### Outputs

Clean list of observable, verifiable outputs:
```json
[
  "Customer Insights Report",
  "Content Production Pipeline",
  "Multi-channel Publishing Schedule"
]
```

### Steps (Dependency Chained)

Each step explicitly references inputs and produces outputs:

```json
{
  "step_number": 1,
  "action": "Extract customer transaction history from Salesforce CRM",
  "uses": "CRM Database Access",
  "produces": "Raw customer behavior dataset",
  "full_description": "Complete step description with details"
}
```

**Key Requirement:** Each step's `uses` field references either:
- Initial `inputs` list, OR
- A previous step's `produces` output

This ensures proper dependency chaining and executability.

## Current Status (as of 2026-02-21)

- ✓ 59 tasks in `dd_requests/`
- ✓ All tasks decomposed with V3 (leaf-node) strategy
- ✓ Inputs parsed with structured metadata
- ✓ Steps with explicit dependency chains
- ✓ Outputs extracted as clean lists
- ✓ AEB (Atomic Execution Block) analysis included

## Configuration Files

### `model_tiers.py`
Defines AI model selection based on task complexity:
- AI1: Basic tasks
- AI2: Moderate complexity
- AI3: Complex tasks

Endpoints: NVIDIA API for Qwen models

### `decomposition_engine_v3.json`
Prompt template and rules for V3 decomposition:
- Input classification (USER/SYSTEM/DERIVABLE)
- Output requirements
- Step construction rules
- Depth stop conditions

## Common Tasks

### Process a Single Task
```bash
python io_decomposition/run_io_dd_decomposition.py --task filename.json
```

### Clear and Re-decompose All Tasks
```bash
cd "c:\Users\AlexL\OneDrive\Documents\Repos\hackeurope-new\hackeurope-26\Alex"
python -c "
import json, os
for f in os.listdir('dd_requests'):
    if f.endswith('.json'):
        path = f'dd_requests/{f}'
        with open(path, encoding='utf-8') as fp:
            task = json.load(fp)
        for key in ['execution_plan', 'aeb_analysis', 'io_decomposed']:
            if key in task:
                del task[key]
        with open(path, 'w', encoding='utf-8') as fp:
            json.dump(task, fp, indent=2)
"
python -u io_decomposition/run_io_dd_decomposition.py
```

## Dependencies

- Python 3.8+
- `openai`: NVIDIA API client
- `numpy`: Numerical operations
- `.env` file with `NVAPI_KEY` set

## Notes

- All operations preserve UTF-8 encoding
- API rate limiting: 5 seconds between calls
- Batch processing takes ~5-6 minutes for 59 tasks
- No raw_response in final outputs (except for debugging)
- Each task is independent; can be processed in parallel
