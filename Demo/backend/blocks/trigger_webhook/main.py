"""Trigger webhook block — returns webhook metadata (skipped by executor)."""


async def execute(inputs: dict, context: dict) -> dict:
    return {
        "payload": inputs.get("payload", {}),
        "headers": inputs.get("headers", {}),
        "method": inputs.get("method", "POST"),
    }
