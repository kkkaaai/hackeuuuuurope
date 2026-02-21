# Block Schema & Semantic Retrieval

## Overview

Blocks are reusable, composable execution units that can be discovered semantically and chained together to form workflows.

## Block Definition

### Core Structure

```json
{
  "id": "web_search",
  "name": "Web Search",
  "description": "Search the web for information",
  "location": "https://api.example.com/blocks/web_search",
  "inputs": {
    "query": {
      "type": "string",
      "description": "Search query",
      "required": true
    },
    "max_results": {
      "type": "integer",
      "description": "Maximum number of results",
      "required": false,
      "default": 10
    }
  },
  "outputs": {
    "results": {
      "type": "array",
      "description": "Search results"
    },
    "total_count": {
      "type": "integer",
      "description": "Total results found"
    }
  },
  "tags": ["search", "web", "information-retrieval"],
  "category": "data-retrieval",
  "version": "1.0",
  "author": "system",
  "created_at": "2026-01-01T00:00:00Z"
}
```

## Field Definitions

### `id` (string, required)
- Unique identifier for the block
- Lowercase, alphanumeric with underscores
- Format: `domain_action` or `action_target`
- Examples: `web_search`, `extract_price`, `filter_threshold`, `crm_fetch_customers`

### `name` (string, required)
- Human-readable name
- Title case
- Examples: "Web Search", "Extract Price", "Filter by Threshold"

### `description` (string, required)
- Clear explanation of what the block does
- 1-2 sentences
- Examples: "Search the web for information using a query string"

### `location` (string, required)
- Where the block is executed
- Can be HTTP endpoint, file path, or service endpoint
- Examples:
  - `https://api.example.com/blocks/web_search`
  - `/services/analyze/endpoint`
  - `s3://bucket/blocks/extract_price.py`
  - `file:///opt/blocks/filter_threshold.py`
  - `database://postgres/stored_procedures/search`

### `inputs` (object, required)
- Dictionary of input parameters
- Each parameter has:
  - `type`: string, integer, number, boolean, array, object
  - `description`: What this input represents
  - `required`: true/false
  - `default`: Default value (if not required)
  - `enum`: Allowed values (optional, for restricted choices)

### `outputs` (object, required)
- Dictionary of output values
- Each output has:
  - `type`: Expected output type
  - `description`: What this output represents
  - `nullable`: Can be null (optional)

### `tags` (array, optional)
- Keywords for semantic search
- Examples: ["search", "web", "api", "async", "text-processing"]

### `category` (string, optional)
- Functional category
- Examples: "data-retrieval", "transformation", "analysis", "generation", "validation"

### `version` (string, optional)
- Semantic versioning
- Format: "MAJOR.MINOR.PATCH"

### `author` (string, optional)
- Who created/maintains the block

### `created_at` (string, optional)
- ISO 8601 timestamp

## Semantic Block Retrieval

### Process

1. **User Intent Embedding**
   - User provides: "Search the web for recent news"
   - System embeds this using NVIDIA embedding model
   - Results in vector: `[0.42, 0.81, 0.12, ..., 0.65]`

2. **Block Database Search**
   - Compute cosine similarity between user intent vector and each block's description vector
   - Rank blocks by similarity score
   - Return top-K blocks (usually K=5-10)

3. **Filtering & Selection**
   - Filter by category (if specified)
   - Filter by input/output compatibility
   - Return ranked list with confidence scores

### Example Retrieval

**User Intent:** "I need to search for customer information in our CRM system"

**Semantic Scores:**
1. `crm_search_customers` - 0.94 ✓ (best match)
2. `crm_fetch_customer_by_id` - 0.87
3. `web_search` - 0.45 (irrelevant)
4. `database_query` - 0.63
5. `text_search` - 0.58

**Result:** Block `crm_search_customers` selected with 94% confidence

## Block Execution

### Invocation Format

```json
{
  "block_id": "web_search",
  "inputs": {
    "query": "latest AI news",
    "max_results": 5
  }
}
```

### Response Format

```json
{
  "status": "success",
  "block_id": "web_search",
  "execution_time_ms": 234,
  "outputs": {
    "results": [
      {
        "title": "AI Breakthrough...",
        "url": "https://...",
        "snippet": "..."
      }
    ],
    "total_count": 1000
  }
}
```

## Block Chaining

### Concept

Blocks are chained by connecting outputs of one block to inputs of the next:

```
Block A: web_search
  output: results (array of search results)
    ↓
Block B: extract_price
  input: items (array)
  output: prices (array of numbers)
    ↓
Block C: calculate_average
  input: numbers (array)
  output: average (number)
```

### Execution Order

1. Execute Block A (web_search) with user-provided inputs
2. Wait for Block A outputs
3. Pass Block A's `results` output to Block B's `items` input
4. Wait for Block B outputs
5. Continue chain until final block completes

## Best Practices

### Block Design

1. **Single Responsibility**: Each block does one thing well
2. **Clear Interface**: Inputs and outputs must be unambiguous
3. **Error Handling**: Return meaningful error messages
4. **Timeouts**: Set reasonable execution timeouts
5. **Idempotency**: Same inputs should produce same outputs

### Naming Conventions

- **Block IDs**: `action_subject` (e.g., `extract_price`, `validate_email`)
- **Inputs/Outputs**: Descriptive, snake_case (e.g., `customer_email`, `is_valid`)
- **Categories**: kebab-case (e.g., `data-retrieval`, `text-processing`)

### Documentation

- Always provide examples in block descriptions
- Document any side effects or external dependencies
- Include sample inputs/outputs in comments
- Specify timeout and rate limits if applicable

## Example Blocks

### Block: `web_search`
```json
{
  "id": "web_search",
  "name": "Web Search",
  "description": "Search the internet for information using Bing or Google API",
  "location": "https://api.search.example.com/search",
  "inputs": {
    "query": { "type": "string", "required": true },
    "engine": { "type": "string", "required": false, "enum": ["google", "bing"], "default": "google" },
    "max_results": { "type": "integer", "required": false, "default": 10 }
  },
  "outputs": {
    "results": { "type": "array" },
    "total_count": { "type": "integer" }
  },
  "tags": ["search", "web", "external-api"],
  "category": "data-retrieval"
}
```

### Block: `text_summarize`
```json
{
  "id": "text_summarize",
  "name": "Summarize Text",
  "description": "Summarize long-form text into concise bullet points",
  "location": "https://api.llm.example.com/summarize",
  "inputs": {
    "text": { "type": "string", "required": true },
    "max_length": { "type": "integer", "required": false, "default": 200 },
    "format": { "type": "string", "required": false, "enum": ["bullets", "paragraph", "brief"], "default": "bullets" }
  },
  "outputs": {
    "summary": { "type": "string" },
    "original_length": { "type": "integer" },
    "summary_length": { "type": "integer" }
  },
  "tags": ["text-processing", "summarization", "nlp"],
  "category": "transformation"
}
```

### Block: `crm_search_customers`
```json
{
  "id": "crm_search_customers",
  "name": "Search CRM Customers",
  "description": "Query customer records from Salesforce CRM by name, email, or ID",
  "location": "https://crm.example.com/api/customers/search",
  "inputs": {
    "query": { "type": "string", "required": true, "description": "Customer name, email, or ID" },
    "limit": { "type": "integer", "required": false, "default": 50 }
  },
  "outputs": {
    "customers": { 
      "type": "array",
      "description": "Matching customer records with id, name, email, phone, address"
    },
    "total_found": { "type": "integer" }
  },
  "tags": ["crm", "salesforce", "customer-data"],
  "category": "data-retrieval",
  "requires_auth": true
}
```

## Integration with Task Decomposition

Blocks can be used as atomic execution units within a decomposed task:

1. Task is decomposed into steps
2. Each step maps to a block (or chain of blocks)
3. Step inputs become block inputs
4. Step outputs become next step's inputs
5. Block execution provides actual implementation

This bridges the gap between abstract task plans and concrete executable workflows.
