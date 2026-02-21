# IO-Driven Task Decomposition Format

## Overview

The IO decomposition system breaks down complex tasks into structured execution plans with explicit input/output dependencies and ordered execution steps.

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

## Execution Plan Structure

The `execution_plan` field contains the decomposed task with inputs, outputs, and dependency-chained steps.

### Complete Example

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
  - Examples: "Customer demographics, purchase history, support interactions"

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

### Example Inputs Array

```json
"inputs": [
  {
    "name": "Customer Data",
    "source_type": "SYSTEM-RETRIEVABLE",
    "source_origin": "CRM Database (Salesforce API)",
    "input_data": "Customer demographics, purchase history, support interactions",
    "bound_reference": "None"
  },
  {
    "name": "Sales Targets",
    "source_type": "USER-CONTROLLED",
    "source_origin": "Marketing Leadership Team",
    "input_data": "Numeric revenue targets per product category",
    "bound_reference": "None"
  },
  {
    "name": "Customer Personas",
    "source_type": "DERIVABLE",
    "source_origin": "Derived from Customer Data and Survey Results",
    "input_data": "Clustered customer segments with behavioral patterns",
    "bound_reference": "[Inputs: Customer Data, Survey Results]"
  }
]
```

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

### Example Outputs

```json
"outputs": [
  "Market Research Report (PDF)",
  "Content Calendar (Excel spreadsheet)",
  "Blog articles (5 posts, ~2000 words each)",
  "Social media graphics (15 assets)",
  "Video scripts (3 documents)",
  "Performance analytics dashboard",
  "Lead generation tracking configuration"
]
```

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
- **`action`** (string): What the step does
  - Executable, concrete action
  - Examples: "Extract customer data", "Apply clustering algorithm", "Generate report"

- **`uses`** (string): Input(s) consumed
  - Reference to input name from `inputs` array, OR
  - Reference to a previous step's `produces` output
  - Multiple inputs: comma-separated or pipe-separated

- **`produces`** (string): Output produced
  - Intermediate or final artifact
  - Becomes available for next step's `uses`
  - Examples: "Cleaned customer dataset", "Customer segmentation model"

- **`full_description`** (string): Complete step text
  - Original multi-line step description from LLM
  - Includes stores/sends location

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
  },
  {
    "step_number": 3,
    "action": "Apply clustering",
    "uses": "Cleaned customer data",  // ✓ From step 2's produces
    "produces": "Customer segments"
  }
]
```

### Example Steps Array

```json
"steps": [
  {
    "step_number": 1,
    "action": "Extract customer transaction history and interaction logs from Salesforce CRM",
    "uses": "CRM Database Access",
    "produces": "Raw customer behavior dataset",
    "full_description": "Step 1:\nUses: CRM Database Access\nAction: Extract customer transaction history and interaction logs from Salesforce CRM\nProduces: Raw customer behavior dataset\nStores/Sends To: Data warehouse (Snowflake) - Table: raw_crm_export"
  },
  {
    "step_number": 2,
    "action": "Apply clustering algorithm to combine CRM and survey data for persona creation",
    "uses": "Raw customer behavior dataset",
    "produces": "Customer segmentation model",
    "full_description": "Step 2:\nUses: Raw customer behavior dataset\nAction: Apply clustering algorithm to combine CRM and survey data for persona creation\nProduces: Customer segmentation model\nStores/Sends To: Machine learning model repository - Model: v1_customer_personas"
  },
  {
    "step_number": 3,
    "action": "Map content preferences to personas using correlation analysis",
    "uses": "Customer segmentation model, Sales Targets",
    "produces": "Persona-specific content recommendations",
    "full_description": "Step 3:\nUses: Customer segmentation model, Sales Targets\nAction: Map content preferences to personas using correlation analysis\nProduces: Persona-specific content recommendations\nStores/Sends To: Content strategy document - File: content_recommendations.docx"
  }
]
```

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

## Complete Real Example

```json
{
  "task_id": "14b0cdd23fca",
  "input": "Research customer insights to produce cohesive blogs, videos, and social posts across all channels while tracking engagement and conversion metrics to hit sales targets.",
  "required_inputs": [],
  "outputs": ["result"],
  "subtasks": [],
  "dependency_structure": {
    "type": "dependency_driven",
    "graph": {},
    "total_subtasks": 0
  },
  "execution_plan": {
    "model_used": "AI1",
    "model_endpoint": "qwen/qwen3-235b-a22b",
    "inputs": [
      {
        "name": "Customer Data",
        "source_type": "SYSTEM-RETRIEVABLE",
        "source_origin": "CRM Database (Salesforce API)",
        "input_data": "Customer demographics, purchase history, interaction logs",
        "bound_reference": "None"
      },
      {
        "name": "Sales Targets",
        "source_type": "USER-CONTROLLED",
        "source_origin": "Marketing Leadership Team",
        "input_data": "Numeric revenue goals by category",
        "bound_reference": "None"
      }
    ],
    "outputs": [
      "Customer Insights Report",
      "Content Calendar",
      "Published Content Assets",
      "Engagement Dashboard"
    ],
    "steps": [
      {
        "step_number": 1,
        "action": "Extract customer profiles from CRM",
        "uses": "Customer Data",
        "produces": "Cleaned customer dataset",
        "full_description": "..."
      },
      {
        "step_number": 2,
        "action": "Analyze customer segments and preferences",
        "uses": "Cleaned customer dataset",
        "produces": "Customer personas and preferences",
        "full_description": "..."
      }
    ],
    "step_count": 2,
    "dependency_validated": true
  },
  "aeb_analysis": {
    "steps_count": 2,
    "aeb_analysis_raw": "Step 1: Yes, AEB...",
    "analysis_complete": true
  },
  "io_decomposed": true
}
```

## Key Principles

1. **No Raw Response**: Final JSON contains only parsed, structured data
2. **Explicit Dependencies**: Every step input is traceable to source
3. **Chainable Execution**: Can implement as sequential block execution
4. **Complete Context**: All information needed to implement steps is present
5. **Verifiable Outputs**: Each output is observable and measurable
