"""Conditional branch block — route based on a boolean condition."""


async def execute(inputs: dict, context: dict) -> dict:
    condition = bool(inputs["condition"])
    return {
        "branch": "yes" if condition else "no",
        "data": inputs.get("data"),
    }
