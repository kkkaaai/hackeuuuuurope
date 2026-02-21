APPEND TO BLOCK GENERATION FLOW













After defining the block, also generate an embedding representation.

The embedding representation must:

1. Be plain text (no JSON).
2. Follow this exact structure:

Embedding Representation:

Inputs:
- For each input: name (type: descriptive natural language type): short semantic description

Outputs:
- For each output: name (type: descriptive natural language type): short semantic description

Purpose:
- 1–3 sentences clearly describing:
  • what transformation occurs
  • when this block should be used
  • what kind of problem it solves

3. Use descriptive natural language types (e.g., "floating point number", "RGB image file", "list of text strings").
4. Do not include implementation details.
5. Do not include code.
6. Do not include raw schema or JSON.

This text will be embedded directly for semantic retrieval.







RETRIEVAL PROMPT



Convert the user’s requested block characteristics into an embedding-ready query.

Output plain text only in this exact format:

Query Representation:

Inputs:
- name (type: descriptive natural language type): brief description

Outputs:
- name (type: descriptive natural language type): brief description

Purpose:
- 1–2 concise sentences describing the intended transformation and when the block should be used.

Rules:
- Use natural language types (e.g., "RGB image file", "floating point number", "list of text strings").
- Do not include JSON or code.
- Keep descriptions short but semantically clear.
- Match the structure used for stored block embeddings.
- No extra commentary.


Inputs:
...

Outputs:
...

Purpose:
...











RETRIEVAL PROMPT





You are converting user search requirements into a structured semantic retrieval query.

Your task is to transform the provided information (which may be structured parameters, free-form text, or both) into a concise, embedding-optimized representation.

Output plain text only in the exact format below:

Query Representation:

Inputs:
- name (type: descriptive natural language type): brief description
- ...

Outputs:
- name (type: descriptive natural language type): brief description
- ...

Purpose:
- 1–2 concise sentences describing:
  • the intended transformation
  • the goal or problem being solved
  • when this block should be selected

Rules:
1. Use clear section headers exactly as written.
2. Use bullet points under Inputs and Outputs.
3. Express types in descriptive natural language (e.g., "RGB image file", "floating point number", "list of text strings").
4. If specific names are not provided, infer sensible generic names (e.g., "image", "text input", "numeric threshold").
5. Do not include JSON.
6. Do not include code.
7. Do not include commentary or explanation.
8. Keep it concise but semantically clear.