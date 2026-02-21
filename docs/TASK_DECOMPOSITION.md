# Task Decomposition System

## Overview

The task decomposition system breaks down complex tasks into structured, executable plans with explicit input/output dependencies and proper dependency chaining. It uses IO-driven execution planning based on inputs, outputs, and ordered steps.

---

## System Architecture

### Core Components

1. **Task Input** → `sample_requests/` directory
2. **Request Cleaning** → `cleaned_requests/` directory  
3. **Dependency-Driven (DD) Structure** → `dd_requests/` directory
4. **Execution Planning** → V2 (recursive) and V3 (leaf-node) engines

### Directory Structure

```
Alex/
├── sample_requests/         # Generated sample tasks
├── cleaned_requests/        # Cleaned/normalized tasks
├── dd_requests/             # Dependency-driven decompositions (final output)
├── io_decomposition/        # Core decomposition scripts
│   ├── run_io_dd_decomposition.py   # Main batch runner
│   └── io_task_decomposer.py        # Decomposition logic
├── logs/                    # System logs
├── decomposition_engine_v2.json     # Recursive derivable strategy
├── decomposition_engine_v3.json     # Leaf-node terminal strategy (CURRENT)
├── clean_requests.py        # Request cleaner
├── clean_dd_requests.py     # DD structure generator
├── generate_requests.py     # Sample task generator
├── model_tiers.py           # AI model tier configuration
└── complexity_evaluator.py  # Task complexity analysis
```

---

## Execution Workflow

### 1. Generate Sample Tasks
```bash
python Alex/generate_requests.py [count]
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
python -u io_decomposition/run_io_dd_decomposition.py [filename] [max_depth]
```

This processes tasks and populates:
- **execution_plan**: Contains inputs, outputs, and ordered steps
- **aeb_analysis**: Atomic Execution Block validation

---

## Decomposition Strategies

### V2: Recursive Derivable (Deprecated)
- Decomposes ALL inputs recursively
- Continues decomposing DERIVABLE inputs until all leaves are USER/SYSTEM
- More detailed but verbose

### V3: Leaf-Node Terminal (Current - RECOMMENDED)
- Only decomposes DERIVABLE inputs
- Stops immediately at USER-CONTROLLED and SYSTEM-RETRIEVABLE inputs
- Cleaner, more practical execution plans

**Use V3 for all new decompositions.**

---

## Task JSON Structure

### Root Level

```json
{
  "task_id": "unique_identifier",
  "input": "Task description / what needs to be accomplished",
  "required_inputs": [],
  "outputs": ["result"],
  "subtasks": [],
  "dependency_structure": {
    "type": "dependency_driven",
    "graph": {},
    "total_subtasks": 0
  },
  "execution_plan": { ... },
  "aeb_analysis": { ... },
  "io_decomposed": true
}
```

### Execution Plan Structure

```json
{
  "execution_plan": {
    "model_used": "AI1",
    "model_endpoint": "qwen/qwen3-235b-a22b",
    "inputs": [ ... ],
    "outputs": [ ... ],
    "steps": [ ... ],
    "step_count": 10,
    "dependency_validated": true
  }
}
```

---

## Inputs Structure

### Input Object (Structured Format)

Each input is a complete object with metadata:

```json
{
  "name": "Sales Targets",
  "source_type": "USER-CONTROLLED",
  "source_origin": "Marketing Leadership Team",
  "input_data": "Numeric revenue targets per product category",
  "bound_reference": "None"
}
```

### Required Fields

- **`name`** (string): Input identifier/label
- **`source_type`** (string): One of:
  - `USER-CONTROLLED` - Must be provided by user explicitly
  - `SYSTEM-RETRIEVABLE` - Retrieved from external API/database/system
  - `DERIVABLE` - Computed from other inputs (marked [DEPTH STOP])

- **`source_origin`** (string): Where it comes from
  - Examples: "Salesforce CRM API", "Marketing Team", "Google Analytics API"

- **`input_data`** (string): What data is required
  - Concrete description of what information is needed

- **`bound_reference`** (string): Links to related inputs
  - References to other input names or dependencies
  - "None" if no references

### Input Type Guidelines

**USER-CONTROLLED:**
- Marketing strategy documents
- Configuration parameters provided by user
- Approval decisions
- Business rules/thresholds
- API keys provided by user

**SYSTEM-RETRIEVABLE:**
- CRM customer data
- Analytics metrics
- API responses
- Database records
- File system contents

**DERIVABLE:**
- Calculated metrics (averages, percentiles)
- Generated reports
- Synthesized insights from multiple inputs
- Transformed data
- Note: Should be marked [DEPTH STOP] - not further decomposed

---

## Outputs Structure

### Output List (Simple Array)

Outputs are a clean list of observable, verifiable deliverables:

```json
"outputs": [
  "Customer Insights Report",
  "Content Production Pipeline",
  "Multi-channel Publishing Schedule",
  "Engagement Metrics Dashboard",
  "Sales Target Achievement Forecast"
]
```

### Output Guidelines

**Valid Outputs:**
- Generated documents (reports, analyses)
- Created assets (content, designs)
- Updated systems (database records, configurations)
- Observable metrics (dashboards, KPIs)
- Action triggers (alerts, notifications)
- Published artifacts (posts, emails, files)

**Invalid Outputs:**
- Vague abstractions ("success", "completion")
- Intermediate data ("processed data")
- Internal states (system flags)
- Undocumented side effects

---

## Steps Structure

### Step Object (Dependency Chained)

Each step explicitly defines inputs, action, and outputs:

```json
{
  "step_number": 1,
  "action": "Extract and clean customer profiles from CRM",
  "uses": "Customer Data",
  "produces": "Cleaned customer dataset",
  "full_description": "Step 1:\nUses: Customer Data\nAction: Extract and clean customer profiles from CRM\nProduces: Cleaned customer dataset\nStores/Sends To: Internal analytics database"
}
```

### Required Step Fields

- **`step_number`** (integer): Sequential order (1, 2, 3, ...)
- **`action`** (string): What the step does (executable, concrete action)
- **`uses`** (string): Input(s) consumed
  - Reference to input name from `inputs` array, OR
  - Reference to a previous step's `produces` output
- **`produces`** (string): Output produced
  - Becomes available for next step's `uses`
- **`full_description`** (string): Complete step text

### Critical Constraint: Dependency Chaining

**Each step's `uses` MUST reference:**
1. An input from the `inputs` array, OR
2. A `produces` output from a previous step

**Invalid example:**
```json
{
  "step_number": 3,
  "action": "Apply clustering to customer segments",
  "uses": "Mystery Input",  // ❌ NOT in inputs array, NOT produced by earlier step
  "produces": "Customer segments"
}
```

**Valid example:**
```json
[
  {
    "step_number": 1,
    "action": "Extract customer data",
    "uses": "CRM Database Access",  // ✓ From inputs array
    "produces": "Raw customer data"
  },
  {
    "step_number": 2,
    "action": "Clean customer data",
    "uses": "Raw customer data",  // ✓ From step 1's produces
    "produces": "Cleaned customer data"
  }
]
```

---

## AEB Analysis Structure

### Purpose

Atomic Execution Block (AEB) analysis validates that each step is:
- Single intent
- Single system boundary interaction
- No branching or sequencing
- Implementable as single function/API call

### Structure

```json
"aeb_analysis": {
  "steps_count": 10,
  "aeb_analysis_raw": "Detailed AEB analysis of each step...",
  "analysis_complete": true
}
```

---

## Model Tiers

The system uses **tiered AI models** to optimize task decomposition based on task complexity.

### Default Tier Configuration

| Complexity Range | Model | Description |
|------------------|-------|-------------|
| 80-100 | AI2 | Very Complex (premium model) |
| 60-80 | AI1 | Complex (standard model) |
| 40-60 | AI2 | Moderate (premium model) |
| 0-40 | AI1 | Simple (standard model) |

### Default Model Mappings

- **AI1**: `qwen/qwen3-235b-a22b` (standard model)
- **AI2**: `deepseek-ai/deepseek-v3.2` (premium model)

### How It Works

1. When a task is decomposed, its **complexity_score** is evaluated first
2. Based on the score, the appropriate AI model is automatically selected
3. The task is decomposed using that model
4. Logs show which model was used for each decomposition

### Example Output

```
[DECOMP] d694a9e573a0: Decomposing (complexity 75)...
[DECOMP] d694a9e573a0: Using model AI2 (Very Complex (80-100))
[DECOMP] d694a9e573a0: Created 5 subtasks
```

### API Reference

#### `get_model_for_complexity(complexity_score)`
Returns the model key for a given complexity score.

```python
from model_tiers import get_model_for_complexity
model = get_model_for_complexity(75)  # Returns "AI2"
```

#### `get_model_endpoint(model_key)`
Returns the full model identifier/endpoint.

```python
from model_tiers import get_model_endpoint
endpoint = get_model_endpoint("AI2")  # Returns "deepseek-ai/deepseek-v3.2"
```

#### `get_tier_info(complexity_score)`
Returns detailed tier information.

```python
from model_tiers import get_tier_info
info = get_tier_info(75)
```

---

## Validation Rules

### Input Validation

✓ **Valid:**
- All inputs have `name`, `source_type`, `source_origin`, `input_data`
- Source types are one of: USER-CONTROLLED, SYSTEM-RETRIEVABLE, DERIVABLE
- Source origins are specific (not vague like "system" or "database")

✗ **Invalid:**
- Missing required fields
- source_type not in allowed list
- Empty or null values in critical fields

### Output Validation

✓ **Valid:**
- All outputs are observable, verifiable deliverables
- No vague abstractions
- Clear, specific descriptions

✗ **Invalid:**
- Outputs like "success", "completion"
- Outputs that are inputs

### Step Validation

✓ **Valid:**
- Sequential step_number (1, 2, 3, ...)
- Each `uses` references input or previous step's `produces`
- Clear, actionable `action` description
- Concrete `produces` output

✗ **Invalid:**
- Gap in step numbers (1, 3, 5)
- `uses` references non-existent input or output
- Vague action descriptions
- Missing `produces`

### Dependency Chain Validation

```
Inputs → Step 1 → Step 2 → Step 3 → ... → Outputs
  ↑        ↓        ↓        ↓              ↓
  └─────────────────────────────────────────┘
         (All references must be valid)
```

---

## Common Tasks

### Process a Single Task
```bash
python io_decomposition/run_io_dd_decomposition.py filename.json
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

---

## Dependencies

- Python 3.8+
- `openai`: NVIDIA API client
- `numpy`: Numerical operations
- `.env` file with `NVAPI_KEY` set

---

## Key Principles

1. **No Raw Response**: Final JSON contains only parsed, structured data
2. **Explicit Dependencies**: Every step input is traceable to source
3. **Chainable Execution**: Can implement as sequential block execution
4. **Complete Context**: All information needed to implement steps is present
5. **Verifiable Outputs**: Each output is observable and measurable

---

## Notes

- All operations preserve UTF-8 encoding
- API rate limiting: 5 seconds between calls
- Batch processing takes ~5-6 minutes for 59 tasks
- No raw_response in final outputs (except for debugging)
- Each task is independent; can be processed in parallel
