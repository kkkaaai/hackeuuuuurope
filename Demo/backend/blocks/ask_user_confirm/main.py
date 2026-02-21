"""Ask user confirmation block — auto-confirms for pipeline execution (no interactive UI yet)."""


async def execute(inputs: dict, context: dict) -> dict:
    question = inputs["question"]
    details = inputs.get("details", {})

    print(f"[CONFIRM STUB] {question} | details={details}")
    # Auto-confirm in pipeline mode — real implementation would pause and wait for UI input
    return {"confirmed": True, "user_message": "Auto-confirmed (pipeline mode)"}
