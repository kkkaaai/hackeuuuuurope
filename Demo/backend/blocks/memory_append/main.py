"""Memory append block — appends a value to a list stored in user memory."""

from storage.memory import memory_store


async def execute(inputs: dict, context: dict) -> dict:
    key = inputs["key"]
    value = inputs["value"]
    namespace = inputs.get("namespace", "default")
    user_id = context.get("user", {}).get("id", "default_user")

    mem = memory_store.get_memory(user_id) or {}
    ns = mem.setdefault(namespace, {})
    lst = ns.setdefault(key, [])
    lst.append(value)
    memory_store.save_memory(user_id, mem)

    return {"success": True, "list_length": len(lst)}
