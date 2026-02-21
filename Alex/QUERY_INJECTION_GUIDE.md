# Query-Powered Prompt Injection Guide

## Overview

The `FlowCreator.create_flow()` method automatically performs query-powered prompt injection:

1. **Query-powered retrieval**: Uses semantic search to find relevant blocks based on user intent
2. **Dynamic injection**: Injects retrieved blocks into the "Available Blocks" section of the prompt
3. **LLM processing**: Sends the prompt with injected blocks to the LLM for flow generation

## How It Works

### Step 1: Query-Powered Block Retrieval

```python
# User provides their intent
user_intent = "Search the web and summarize findings"

# Retriever embeds the intent and queries the database
retrieved_blocks, blocks_json = self.retriever.get_blocks_for_intent(
    user_intent,
    k=5  # Top 5 relevant blocks
)

# Result: Only blocks semantically similar to the intent are retrieved
# Example: [web_search, claude_summarize, memory_write, ...]
```

**Behind the scenes:**
1. Intent is embedded using NVIDIA embedding model
2. Compared against all block descriptors (via cosine similarity)
3. Returns top-K blocks above similarity threshold
4. Formatted as JSON for injection

### Step 2: Dynamic Prompt Injection

**Base prompt template (from flow_creation_prompt.json):**
```
You are a task decomposer for AgentFlow...

## Available Blocks
[BLOCKS_PLACEHOLDER]

## Rules
1. Use existing blocks by referencing their "block_id"...
```

**After injection:**
```
You are a task decomposer for AgentFlow...

## Available Blocks
[
  {
    "id": "web_search",
    "location": "https://api.example.com/blocks/web_search",
    "inputs": {"query": "string", "num_results": "integer (optional)"},
    "outputs": {"results": "array of {title, url, snippet}"},
    "descriptor": "Search the web for information on any topic..."
  },
  {
    "id": "claude_summarize",
    "location": "https://api.example.com/blocks/claude_summarize",
    "inputs": {"content": "string", "length": "string (optional)"},
    "outputs": {"summary": "string"},
    "descriptor": "Summarize text content into concise summaries..."
  },
  ...
]

## Rules
1. Use existing blocks by referencing their "block_id"...
```

### Step 3: LLM Flow Generation

The LLM receives the complete prompt with injected blocks and generates a flow plan:

```json
{
  "required_blocks": [
    {
      "block_id": "web_search",
      "reason": "Search for information from the web"
    },
    {
      "block_id": "claude_summarize",
      "reason": "Summarize the search results"
    }
  ]
}
```

## Implementation Details

### In FlowCreator.create_flow()

```python
def create_flow(self, user_intent: str, num_blocks: int = 5):
    """
    Step 1: Retrieve relevant blocks based on query
    """
    retrieved_blocks, blocks_json = self.retriever.get_blocks_for_intent(
        user_intent,  # <-- QUERY INPUT
        k=num_blocks
    )
    # blocks_json is a formatted JSON string of retrieved blocks
    
    """
    Step 2: Inject into prompt
    """
    prompt = self.base_prompt.replace(
        "[BLOCKS_PLACEHOLDER]",  # <-- PLACEHOLDER
        blocks_json              # <-- INJECTED BLOCKS
    )
    
    """
    Step 3: Add user intent and call LLM
    """
    full_prompt = f"{prompt}\n\nUser Intent:\n{user_intent}"
    
    # LLM receives full_prompt with injected blocks
    response = client.chat.completions.create(
        model=self.model,
        messages=[{"role": "user", "content": full_prompt}],
        ...
    )
```

## Retrieval Process

### Query Embedding
```
User Intent: "Search the web and summarize findings"
         ↓
[Embedded using nvidia/llama-3.2-nv-embedqa-1b-v1]
         ↓
Vector: [0.234, -0.156, ..., 0.892] (1024-dimensional)
```

### Similarity Search
```
Compare against all block descriptors:

web_search:
  "Search the web for information on any topic..."
  Similarity: 0.94 ✓ (HIGH - INCLUDE)

claude_summarize:
  "Summarize text content into concise summaries..."
  Similarity: 0.91 ✓ (HIGH - INCLUDE)

filter_threshold:
  "Filter items based on numerical thresholds..."
  Similarity: 0.38 ✗ (LOW - EXCLUDE)

memory_write:
  "Store data in memory for retrieval..."
  Similarity: 0.45 ✓ (MEDIUM - INCLUDE)
```

### Block Filtering
Only blocks above `SIMILARITY_THRESHOLD` (default: 0.4) are included:
- web_search (0.94)
- claude_summarize (0.91)
- memory_write (0.45)

### JSON Formatting
```json
[
  {
    "id": "web_search",
    "location": "...",
    "inputs": {...},
    "outputs": {...},
    "descriptor": "..."
  },
  {
    "id": "claude_summarize",
    "location": "...",
    "inputs": {...},
    "outputs": {...},
    "descriptor": "..."
  },
  {
    "id": "memory_write",
    "location": "...",
    "inputs": {...},
    "outputs": {...},
    "descriptor": "..."
  }
]
```

## Example Execution

```python
from flow_creator import FlowCreator

creator = FlowCreator()

# Query 1: Search-focused
result1 = creator.create_flow(
    "Search for AI news and summarize"
)
# Retrieved: [web_search, claude_summarize, memory_write]

# Query 2: Data processing-focused
result2 = creator.create_flow(
    "Filter data by price and analyze trends"
)
# Retrieved: [filter_threshold, claude_analyze, sort_by_field]

# Query 3: Complex workflow
result3 = creator.create_flow(
    "Search competitor prices, filter by threshold, analyze, and store results"
)
# Retrieved: [web_search, filter_threshold, claude_analyze, memory_write]
```

## Configuration

### Control Block Retrieval Count

```python
# Get fewer blocks (faster, more focused)
result = creator.create_flow(intent, num_blocks=3)

# Get more blocks (slower, more options)
result = creator.create_flow(intent, num_blocks=10)
```

### Adjust Similarity Threshold

Edit `block_retriever.py`:
```python
SIMILARITY_THRESHOLD = 0.4  # Default

# Lower for looser matching
SIMILARITY_THRESHOLD = 0.3

# Higher for stricter matching
SIMILARITY_THRESHOLD = 0.6
```

## Performance Notes

### Speed
- Block embedding: ~500ms per block (cached after first run)
- Query embedding: ~200ms
- Retrieval (similarity search): <50ms
- Total retrieval: ~250ms
- LLM call: ~2-3s

**Total time for flow creation: ~3-4 seconds**

### Quality
- Better query → Better block matches
- More descriptive block descriptors → Better semantic matching
- Larger block database → More options for LLM

## Example Flows

### Search & Summarize

**Query:**
```
"Search for machine learning tutorials and provide a summary"
```

**Retrieved Blocks:**
- `web_search` (similarity: 0.95)
- `claude_summarize` (similarity: 0.93)

**Generated Flow:**
```json
{
  "required_blocks": [
    {"block_id": "web_search", "reason": "Search for ML tutorials"},
    {"block_id": "claude_summarize", "reason": "Summarize results"}
  ]
}
```

### Data Analysis Pipeline

**Query:**
```
"Filter products by price threshold and analyze market trends"
```

**Retrieved Blocks:**
- `filter_threshold` (similarity: 0.92)
- `claude_analyze` (similarity: 0.88)
- `sort_by_field` (similarity: 0.81)

**Generated Flow:**
```json
{
  "required_blocks": [
    {"block_id": "filter_threshold", "reason": "Filter by price"},
    {"block_id": "sort_by_field", "reason": "Rank by relevance"},
    {"block_id": "claude_analyze", "reason": "Analyze trends"}
  ]
}
```

### Complex Multi-Step Workflow

**Query:**
```
"Search competitor sites, extract prices, filter by our threshold, analyze pricing strategy, and save results"
```

**Retrieved Blocks:**
- `web_search` (similarity: 0.94)
- `filter_threshold` (similarity: 0.89)
- `claude_analyze` (similarity: 0.87)
- `memory_write` (similarity: 0.79)
- `extract_price` (similarity: 0.92)

**Generated Flow:**
```json
{
  "required_blocks": [
    {"block_id": "web_search", "reason": "Search competitor sites"},
    {"block_id": "extract_price", "reason": "Extract prices from listings"},
    {"block_id": "filter_threshold", "reason": "Filter by threshold"},
    {"block_id": "claude_analyze", "reason": "Analyze pricing strategy"},
    {"block_id": "memory_write", "reason": "Save results for later"}
  ]
}
```

## Troubleshooting

### No Blocks Retrieved

**Problem:** `get_blocks_for_intent()` returns empty list

**Causes:**
1. No blocks in database
2. Similarity threshold too high
3. Query too specific

**Solution:**
```python
# Check if blocks exist
db = BlockDatabase()
print(len(db.blocks))  # Should be > 0

# Lower threshold
# In block_retriever.py:
SIMILARITY_THRESHOLD = 0.3  # Was 0.4

# Try more generic query
result = creator.create_flow(
    "search and analyze"  # Instead of "extract NER entities from reddit comments"
)
```

### Wrong Blocks Retrieved

**Problem:** Retrieved blocks don't match intent

**Cause:** Block descriptors are not descriptive enough

**Solution:** Improve block descriptors
```json
{
  "id": "my_block",
  "descriptor": "Does something"  // BAD
}

{
  "id": "my_block",
  "descriptor": "Extract product prices from HTML listings using regex patterns and return structured data"  // GOOD
}
```

### Slow Retrieval

**Problem:** First call takes 3-5+ seconds

**Cause:** Blocks are being embedded on first run

**Solution:** Pre-generate embeddings
```python
db = BlockDatabase()
db.embed_blocks()  # This caches embeddings
```

## Summary

Query-powered prompt injection:

✅ **Automatic** - Happens transparently in `create_flow()`
✅ **Semantic** - Uses vector embeddings for matching
✅ **Dynamic** - Different queries get different blocks
✅ **Fast** - Cached embeddings make subsequent calls fast
✅ **Flexible** - Easy to control with `num_blocks` parameter
✅ **Smart** - LLM sees only relevant blocks, not entire database

**Result:** Flow generation is query-aware and produces contextually appropriate execution plans.
