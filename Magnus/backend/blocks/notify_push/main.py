"""Notify push block — send a notification (logs to stdout for now)."""


async def execute(inputs: dict, context: dict) -> dict:
    title = inputs["title"]
    body = inputs["body"]
    print(f"[NOTIFICATION] {title}: {body}")
    return {"delivered": True}
