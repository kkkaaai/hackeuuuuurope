# Prompt Injector Usage Guide

## Overview

The `prompt_injector.py` module provides clean, dedicated functions for prompt injection. It handles:

1. **Query-powered block retrieval** - Finds relevant blocks based on user query
2. **Prompt population** - Injects blocks into template
3. **Metadata tracking** - Returns information about retrieved blocks

## Basic Usage

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

### With Metadata

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

## Using PromptInjector Class

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
full_prompt = inject_prompt(
    template,
    "search for information"
)
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

### `PromptInjector.inject_prompt()` - Class Method

```python
class PromptInjector:
    def inject_prompt(
        self,
        template_prompt: str,
        query: str,
        num_blocks: int = 5,
        placeholder: str = "[BLOCKS_PLACEHOLDER]"
    ) -> str
```

**Returns:** Fully populated prompt

**Example:**
```python
injector = PromptInjector(db)
full_prompt = injector.inject_prompt(template, "search query")
```

---

### `PromptInjector.inject_prompt_only_blocks()` - Class Method

```python
class PromptInjector:
    def inject_prompt_only_blocks(
        self,
        template_prompt: str,
        query: str,
        num_blocks: int = 5,
        placeholder: str = "[BLOCKS_PLACEHOLDER]"
    ) -> str
```

**Returns:** Prompt with injected blocks only (no query appended)

**Use when:** Your prompt template already handles query placement

**Example:**
```python
prompt_with_blocks = injector.inject_prompt_only_blocks(template, query)
# Template handles adding the query itself
```

---

### `PromptInjector.inject_prompt_and_return_metadata()` - Class Method

```python
class PromptInjector:
    def inject_prompt_and_return_metadata(
        self,
        template_prompt: str,
        query: str,
        num_blocks: int = 5,
        placeholder: str = "[BLOCKS_PLACEHOLDER]"
    ) -> Tuple[str, Dict]
```

**Returns:** Tuple of (populated_prompt, metadata_dict)

**Example:**
```python
prompt, meta = injector.inject_prompt_and_return_metadata(template, query)
```

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

### What Gets Injected

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

## Custom Placeholder

Use a different placeholder if needed:

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
