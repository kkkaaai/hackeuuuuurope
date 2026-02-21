"""Memory read block — read a value from user memory."""


async def execute(inputs: dict, context: dict) -> dict:
    key = inputs["key"]
    memory = context.get("memory", {})
    return {"value": memory.get(key)}
