# Prompt Injection System

## Overview

The prompt injection system provides query-powered, semantic block retrieval and dynamic prompt population. It uses embedding-based search to find relevant blocks and injects them into prompt templates for LLM processing.

---

## Quick Start

### Simple Injection

```python
from prompt_injector import inject_prompt

# Your template prompt with placeholder
template = """You are a decomposer.

## Available Blocks
[BLOCKS_PLACEHOLDER]

## Rules
1. Use existing blocks when they fit
"""

# Inject query-relevant blocks
full_prompt = inject_prompt(
    template_prompt=template,
    query="search and summarize news"
)

# Send full_prompt to LLM
response = llm.chat.completions.create(
    messages=[{"role": "user", "content": full_prompt}]
)
```

### With Metadata Tracking

```python
from prompt_injector import inject_prompt_with_metadata

# Get both the prompt and metadata
full_prompt, metadata = inject_prompt_with_metadata(
    template_prompt=template,
    query="search and summarize news"
)

# Use the prompt
response = llm.call(full_prompt)

# Track what blocks were retrieved
print(f"Retrieved {metadata['num_retrieved']} blocks:")
for block in metadata['retrieved_blocks']:
    print(f"  - {block['id']}")
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    prompt_injector.py                        │
│                                                             │
│  inject_prompt()                                            │
│  inject_prompt_with_metadata()                              │
│  PromptInjector class                                       │
│                                                             │
│  ↓ Uses ↓                                                   │
│  block_retriever.py (retrieval logic)                       │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│                    flow_creator.py                           │
│                                                             │
│  FlowCreator.create_flow()                                  │
│  imports inject_prompt_with_metadata()                      │
└─────────────────────────────────────────────────────────────┘
```

---

## How It Works

### Step-by-Step Process

```
inject_prompt(template, "search and summarize")
    ↓
1. Retrieve blocks
   - Embed query: "search and summarize"
   - Search block database for similar blocks
   - Return top-K (default 5) blocks
    ↓
2. Format blocks
   - Convert Block objects to JSON
   - Create formatted block list
    ↓
3. Replace placeholder
   - Find [BLOCKS_PLACEHOLDER] in template
   - Replace with formatted block JSON
    ↓
4. Add query
   - Append "User Intent: {query}" to prompt
    ↓
5. Return fully populated prompt
```

---

## API Reference

### `inject_prompt()` - Standalone Function

```python
inject_prompt(
    template_prompt: str,
    query: str,
    num_blocks: int = 5,
    block_db: Optional[BlockDatabase] = None,
    placeholder: str = "[BLOCKS_PLACEHOLDER]"
) -> str
```

**Returns:** Fully populated prompt ready for LLM

**Example:**
```python
full_prompt = inject_prompt(template, "search for information")
```

---

### `inject_prompt_with_metadata()` - Standalone Function

```python
inject_prompt_with_metadata(
    template_prompt: str,
    query: str,
    num_blocks: int = 5,
    block_db: Optional[BlockDatabase] = None,
    placeholder: str = "[BLOCKS_PLACEHOLDER]"
) -> Tuple[str, Dict]
```

**Returns:** Tuple of (populated_prompt, metadata_dict)

**Metadata contains:**
- `retrieved_blocks` - List of block dicts
- `num_retrieved` - Count of blocks
- `query` - The original query

**Example:**
```python
full_prompt, metadata = inject_prompt_with_metadata(
    template,
    "search and filter"
)

print(f"Retrieved {metadata['num_retrieved']} blocks")
```

---

### `PromptInjector` Class

For more control, use the `PromptInjector` class directly:

```python
from prompt_injector import PromptInjector
from block_retriever import BlockDatabase

# Initialize with your block database
db = BlockDatabase()
injector = PromptInjector(db)

# Inject prompt
full_prompt = injector.inject_prompt(
    template_prompt=template,
    query="filter and analyze data",
    num_blocks=5
)
```

#### Class Methods

##### `inject_prompt()`
```python
def inject_prompt(
    self,
    template_prompt: str,
    query: str,
    num_blocks: int = 5,
    placeholder: str = "[BLOCKS_PLACEHOLDER]"
) -> str
```

##### `inject_prompt_only_blocks()`
```python
def inject_prompt_only_blocks(
    self,
    template_prompt: str,
    query: str,
    num_blocks: int = 5,
    placeholder: str = "[BLOCKS_PLACEHOLDER]"
) -> str
```
**Use when:** Your prompt template already handles query placement

##### `inject_prompt_and_return_metadata()`
```python
def inject_prompt_and_return_metadata(
    self,
    template_prompt: str,
    query: str,
    num_blocks: int = 5,
    placeholder: str = "[BLOCKS_PLACEHOLDER]"
) -> Tuple[str, Dict]
```

---

## Query-Powered Retrieval

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

---

## What Gets Injected

**Template:**
```
## Available Blocks
[BLOCKS_PLACEHOLDER]
```

**After Injection:**
```
## Available Blocks
[
  {
    "id": "web_search",
    "location": "https://api.example.com/blocks/web_search",
    "inputs": {"query": "string"},
    "outputs": {"results": "array"},
    "descriptor": "Search the web..."
  },
  {
    "id": "claude_summarize",
    "location": "https://api.example.com/blocks/claude_summarize",
    "inputs": {"content": "string"},
    "outputs": {"summary": "string"},
    "descriptor": "Summarize text..."
  }
]
```

---

## Integration with FlowCreator

`FlowCreator` uses `prompt_injector` internally:

```python
from flow_creator import FlowCreator

creator = FlowCreator()

# Internally uses:
# full_prompt, metadata = inject_prompt_with_metadata(
#     self.base_prompt,
#     user_intent,
#     num_blocks,
#     self.block_db
# )

result = creator.create_flow("search and summarize")
```

No explicit call needed - it's handled internally!

---

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

### Custom Placeholder

```python
template = """
Available models:
[[MODELS_HERE]]

Available blocks:
[[BLOCKS_HERE]]
"""

full_prompt = inject_prompt(
    template,
    "search",
    placeholder="[[BLOCKS_HERE]]"
)
```

---

## Common Patterns

### Pattern 1: Simple Flow Creation

```python
from prompt_injector import inject_prompt
from openai import OpenAI

client = OpenAI()
template = load_template()

full_prompt = inject_prompt(template, user_intent)

response = client.chat.completions.create(
    messages=[{"role": "user", "content": full_prompt}]
)
```

### Pattern 2: Track Retrieved Blocks

```python
from prompt_injector import inject_prompt_with_metadata

full_prompt, meta = inject_prompt_with_metadata(template, intent)

# Log what was retrieved
log_blocks_retrieved(meta['retrieved_blocks'])

# Send prompt
response = llm.call(full_prompt)
```

### Pattern 3: Reuse Injector Instance

```python
from prompt_injector import PromptInjector

injector = PromptInjector()

for intent in intents:
    prompt = injector.inject_prompt(template, intent)
    # Process prompt
```

### Pattern 4: Custom Block Count

```python
# For simple queries
prompt1 = inject_prompt(template, "search", num_blocks=3)

# For complex queries
prompt2 = inject_prompt(template, "search, filter, analyze, store", num_blocks=10)
```

---

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

---

## Performance

| Operation | Time |
|-----------|------|
| Load BlockDatabase | <100ms |
| Embed query | ~200ms |
| Retrieve blocks (top-5) | <50ms |
| Format blocks as JSON | <10ms |
| Replace placeholder | <5ms |
| **Total injection time** | **~250ms** |

Subsequent calls are faster due to caching.

**Speed:**
- Block embedding: ~500ms per block (cached after first run)
- Query embedding: ~200ms
- Retrieval (similarity search): <50ms
- Total retrieval: ~250ms
- LLM call: ~2-3s

**Total time for flow creation: ~3-4 seconds**

---

## Error Handling

The injector handles these gracefully:

**No blocks found:**
```python
# If no blocks match the query
full_prompt = inject_prompt(template, "very specific niche query")
# Result: Prompt with empty blocks array
```

**Missing placeholder:**
```python
template = "No placeholder here"
full_prompt = inject_prompt(template, "query")
# Result: Returns template unchanged
```

**Missing database:**
```python
# Auto-loads from blocks.json
full_prompt = inject_prompt(template, "query")
```

---

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
result = creator.create_flow("search and analyze")
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

---

## Testing

Run the included test:

```bash
python prompt_injector.py
```

Output:
```
Testing Prompt Injector
================================================================================

1. Creating sample block database...
   ✓ Created 6 sample blocks

2. Testing basic injection...
   Query: 'search and summarize news'
   Full prompt length: 1847 characters
   
   First 500 chars of populated prompt:
   ────────────────────────────────────────────────────────────
   You are a task decomposer...
   ────────────────────────────────────────────────────────────

3. Testing injection with metadata...
   Query: 'filter data and analyze'
   Retrieved blocks: 3
   Block IDs:
      - filter_threshold
      - claude_analyze
      - memory_write

✓ Prompt injection working correctly!
```

---

## Files Involved

| File | Role |
|------|------|
| `prompt_injector.py` | Injection logic |
| `block_retriever.py` | Block retrieval |
| `flow_creator.py` | Uses injector |
| `flow_creation_prompt.json` | Template with placeholder |
| `blocks.json` | Block database |

---

## Summary

The `prompt_injector` module provides:

✅ **Clean API** - Simple functions for prompt injection
✅ **Query-powered** - Automatic block retrieval based on query
✅ **Metadata tracking** - Know what blocks were retrieved
✅ **Flexible** - Use standalone functions or class
✅ **Error handling** - Graceful degradation
✅ **Performance** - Fast injection with caching
✅ **Integration** - Used seamlessly by FlowCreator

Use it whenever you need to:
- Populate prompt templates with dynamic content
- Retrieve query-relevant blocks
- Track what was injected
- Create flexible LLM workflows

---

## TL;DR

```python
from prompt_injector import inject_prompt

full_prompt = inject_prompt(template, query)
# → Injected prompt ready for LLM ✓
```
