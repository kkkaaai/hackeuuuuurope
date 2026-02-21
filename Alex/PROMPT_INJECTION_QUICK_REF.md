# Prompt Injection - Quick Reference

## The Simplest Way

```python
from prompt_injector import inject_prompt

full_prompt = inject_prompt(template, "search and summarize")
# That's it!
```

## With Tracking

```python
from prompt_injector import inject_prompt_with_metadata

full_prompt, metadata = inject_prompt_with_metadata(template, "search and summarize")
print(f"Retrieved {metadata['num_retrieved']} blocks")
```

## What It Does

```
Template: "## Available Blocks\n[BLOCKS_PLACEHOLDER]\n\nRules..."
Query: "search and summarize"

         ↓ inject_prompt() ↓

1. Embed query
2. Find similar blocks
3. Format as JSON
4. Replace [BLOCKS_PLACEHOLDER]
5. Add query to prompt
6. Return ready-to-use prompt
```

## Complete Flow Example

```python
from flow_creator import FlowCreator

# Create flow - internally uses inject_prompt automatically
creator = FlowCreator()
result = creator.create_flow("search and summarize news")

# Or use prompt injector directly
from prompt_injector import inject_prompt

template = load_template()
full_prompt = inject_prompt(template, "search and summarize")
response = llm.call(full_prompt)
```

## API Cheat Sheet

| Function | Returns | Use When |
|----------|---------|----------|
| `inject_prompt()` | str | Just need the prompt |
| `inject_prompt_with_metadata()` | (str, dict) | Need to track blocks |
| `PromptInjector.inject_prompt()` | str | Want class instance |
| `PromptInjector.inject_prompt_only_blocks()` | str | Custom query handling |

## Parameters

```python
inject_prompt(
    template_prompt,        # Required: template with [BLOCKS_PLACEHOLDER]
    query,                  # Required: user intent for block retrieval
    num_blocks=5,           # Optional: how many blocks to retrieve
    block_db=None,          # Optional: custom BlockDatabase
    placeholder="[BLOCKS_PLACEHOLDER]"  # Optional: custom placeholder
)
```

## Return Values

### `inject_prompt()` returns
- `str` - Full prompt ready for LLM

### `inject_prompt_with_metadata()` returns
- `str` - Full prompt
- `dict` with:
  - `retrieved_blocks` - List of block dicts
  - `num_retrieved` - Count
  - `query` - Original query

## Real Examples

### Example 1: Simple
```python
from prompt_injector import inject_prompt
prompt = inject_prompt(template, "search")
llm.call(prompt)
```

### Example 2: Track Blocks
```python
from prompt_injector import inject_prompt_with_metadata
prompt, meta = inject_prompt_with_metadata(template, "search")
log_blocks(meta['retrieved_blocks'])
llm.call(prompt)
```

### Example 3: Custom Count
```python
# Few blocks for simple query
p1 = inject_prompt(template, "search", num_blocks=3)

# Many blocks for complex query
p2 = inject_prompt(template, "search, filter, analyze, store", num_blocks=10)
```

### Example 4: Class-based
```python
from prompt_injector import PromptInjector
injector = PromptInjector()

for query in queries:
    prompt = injector.inject_prompt(template, query)
    process(prompt)
```

## What Gets Injected

```
BEFORE:
## Available Blocks
[BLOCKS_PLACEHOLDER]

AFTER:
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
    ...
  }
]
```

## Process

```
Query: "search and summarize"
  ↓
Embed query (using NVIDIA model)
  ↓
Search blocks (cosine similarity)
  ↓
Get top-K (default 5)
  ↓
Format as JSON
  ↓
Replace placeholder
  ↓
Add query to end
  ↓
Return full prompt
```

## Performance

- **First call:** ~250ms (includes embedding)
- **Cached calls:** ~50ms

## Integration Points

### With FlowCreator (Automatic)
```python
creator = FlowCreator()
# Internally uses inject_prompt_with_metadata
result = creator.create_flow(intent)
```

### With Custom LLM (Manual)
```python
from prompt_injector import inject_prompt

full_prompt = inject_prompt(template, intent)
response = my_llm.generate(full_prompt)
```

### With Monitoring (Manual)
```python
from prompt_injector import inject_prompt_with_metadata

full_prompt, meta = inject_prompt_with_metadata(template, intent)
monitor.log_blocks(meta['retrieved_blocks'])
response = llm.generate(full_prompt)
```

## Common Patterns

### Pattern: Search & Summarize
```python
prompt = inject_prompt(template, "search for X and summarize")
# Retrieved: [web_search, claude_summarize]
```

### Pattern: Filter & Analyze
```python
prompt = inject_prompt(template, "filter data and analyze")
# Retrieved: [filter_threshold, claude_analyze]
```

### Pattern: Complex Workflow
```python
prompt = inject_prompt(template, "search, extract, filter, analyze, store")
# Retrieved: [web_search, extract_*, filter_*, analyze, memory_write]
```

## Error Handling

| Issue | Behavior |
|-------|----------|
| No blocks found | Returns empty array in blocks |
| Missing placeholder | Returns template unchanged |
| Invalid template | Exception raised |
| Bad query | Still works, may get fewer blocks |

## Configuration

In `block_retriever.py`:
```python
SIMILARITY_THRESHOLD = 0.4  # Min relevance score

# Lower for loose matching
SIMILARITY_THRESHOLD = 0.3

# Higher for strict matching
SIMILARITY_THRESHOLD = 0.6
```

## Testing

```bash
python prompt_injector.py
```

Verifies:
- Block database loads
- Injection works
- Metadata accurate
- Prompt is populated

## Files Involved

| File | Role |
|------|------|
| `prompt_injector.py` | Injection logic |
| `block_retriever.py` | Block retrieval |
| `flow_creator.py` | Uses injector |
| `flow_creation_prompt.json` | Template with placeholder |
| `blocks.json` | Block database |

## Docs

- **PROMPT_INJECTOR_USAGE.md** - Full API reference
- **QUERY_INJECTION_GUIDE.md** - How retrieval works
- **IMPLEMENTATION_SUMMARY.md** - Architecture overview

---

**TL;DR:** `inject_prompt(template, query)` → Injected prompt ready for LLM ✓
