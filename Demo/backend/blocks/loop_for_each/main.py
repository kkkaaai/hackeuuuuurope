"""Loop for-each block — iterates over items and executes a block for each."""

from engine.executor import execute_block


async def execute(inputs: dict, context: dict) -> dict:
    items = inputs["items"]
    block_id = inputs["block_id"]

    results = []
    for item in items:
        node_def = {
            "id": f"loop_iter_{len(results)}",
            "block_id": block_id,
            "inputs": item if isinstance(item, dict) else {"input": item},
        }
        state = {"results": {}, "user": context.get("user", {}), "memory": context.get("memory", {})}
        result = await execute_block(node_def, state)
        results.append(result)

    return {"results": results, "count": len(results)}
