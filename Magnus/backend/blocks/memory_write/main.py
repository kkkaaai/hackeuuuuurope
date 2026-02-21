"""Memory write block — write a value to user memory."""


async def execute(inputs: dict, context: dict) -> dict:
    key = inputs["key"]
    value = inputs["value"]
    memory = context.get("memory", {})
    memory[key] = value
    return {"success": True}
