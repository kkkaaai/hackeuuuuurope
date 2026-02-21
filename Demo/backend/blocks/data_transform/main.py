"""Data transform block — maps fields from input data using simple expressions."""


async def execute(inputs: dict, context: dict) -> dict:
    data = inputs["data"]
    mapping = inputs.get("mapping", {})

    transformed = {}
    for new_key, expr in mapping.items():
        # Simple field reference: if expr is a key in data, use its value
        if expr in data:
            transformed[new_key] = data[expr]
        else:
            # Treat as a literal value
            transformed[new_key] = expr

    return {"transformed": transformed}
