LLM-Enhanced Query Embedding

Overview

Add an LLM call in embeddings.py to convert raw search queries into a structured format that better matches the stored block embeddings, improving semantic similarity search.

Current Flow

flowchart LR
    A[Search Query] --> B[generate_embedding]
    B --> C[OpenAI Embedding]
    C --> D[Supabase Vector Search]

The current registry.search() passes raw query text (e.g., "fetch bitcoin price") directly to generate_embedding().

Proposed Flow

flowchart LR
    A[Search Query + Schema] --> B[format_query_for_embedding]
    B -->|LLM Call| C[Structured Query Text]
    C --> D[generate_embedding]
    D --> E[OpenAI Embedding]
    E --> F[Supabase Vector Search]

Implementation

1. Add LLM query formatter in [Demo/backend/storage/embeddings.py](Demo/backend/storage/embeddings.py)

Add new function format_query_for_embedding() that:





Takes the raw query string plus optional input/output schemas from the required_block spec



Calls the LLM with your prompt template



Returns structured plain text in the format:

Inputs:
- name (type: descriptive type): brief description

Outputs:
- name (type: descriptive type): brief description

Purpose:
- 1-2 concise sentences...

Uses the existing call_llm from llm.service.

2. Update generate_embedding() in [Demo/backend/storage/embeddings.py](Demo/backend/storage/embeddings.py)

Add optional parameter to trigger LLM formatting:





generate_embedding(text, format_as_query=False, input_schema=None, output_schema=None)



When format_as_query=True, call format_query_for_embedding() first

3. Update search call in [Demo/backend/registry/registry.py](Demo/backend/registry/registry.py)

Modify BlockRegistry.search() to accept and pass schema context:





search(query, limit=10, input_schema=None, output_schema=None)



Pass schemas to generate_embedding() with format_as_query=True

4. Update callers in thinker files

Update search calls in:





[Demo/backend/engine/thinker_stream.py](Demo/backend/engine/thinker_stream.py) (line 121)



[Demo/backend/engine/thinker_synthesis.py](Demo/backend/engine/thinker_synthesis.py) (line 174)

Pass input_schema and output_schema from the req dict to registry.search().

Key Code Additions

New prompt constant in embeddings.py:

QUERY_FORMAT_PROMPT = """Convert the user's requested block characteristics into an embedding-ready query.

Output plain text only in this exact format:

Inputs:
- name (type: descriptive natural language type): brief description

Outputs:
- name (type: descriptive natural language type): brief description

Purpose:
- 1-2 concise sentences describing the intended transformation and when the block should be used.

Rules:
- Use natural language types (e.g., "RGB image file", "floating point number", "list of text strings").
- Do not include JSON or code.
- Keep descriptions short but semantically clear.
- Match the structure used for stored block embeddings.
- No extra commentary."""

Files to Modify





Demo/backend/storage/embeddings.py - Add format_query_for_embedding(), update generate_embedding()



Demo/backend/registry/registry.py - Update search() signature



Demo/backend/engine/thinker_stream.py - Pass schemas to search



Demo/backend/engine/thinker_synthesis.py - Pass schemas to search

