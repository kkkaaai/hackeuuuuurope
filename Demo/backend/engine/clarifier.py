"""Clarifier — evaluates if a user request is specific enough for pipeline creation."""

from llm.service import call_llm_messages, parse_json_output

SYSTEM_PROMPT = """\
You are a pipeline-creation assistant. Your job is to evaluate whether the user's \
request is specific enough to create an automation pipeline.

A request is "ready" if it includes:
- A clear action or sequence of actions to perform
- Enough detail to determine what data sources, APIs, or tools are needed

A request is NOT ready if it's:
- Too vague (e.g., "automate something", "help me with work")
- Missing critical details needed to build a pipeline

If the request is NOT ready, ask ONE short clarifying question to get the missing detail.
You may ask at most 3 rounds of questions total. After 3 rounds, consider the request \
ready and work with what you have.

Respond in JSON only:
- If ready: {"ready": true, "refined_intent": "<the user's intent, clarified and expanded>"}
- If not ready: {"ready": false, "question": "<your clarifying question>"}"""


async def clarify(message: str, history: list[dict]) -> dict:
    """Evaluate if the user's request is specific enough.

    Returns {"ready": True, "refined_intent": "..."} or {"ready": False, "question": "..."}
    """
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add conversation history
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current message
    messages.append({"role": "user", "content": message})

    # If we've already had 3+ user messages, force ready
    user_count = sum(1 for m in messages if m["role"] == "user")
    if user_count > 3:
        return {"ready": True, "refined_intent": message}

    response = await call_llm_messages(messages)

    try:
        parsed = parse_json_output(response)
        if "ready" in parsed:
            return parsed
    except Exception:
        pass

    # Fallback: assume ready
    return {"ready": True, "refined_intent": message}
