"""Memory load/save helpers for the Doer pipeline."""

from storage.memory import memory_store


async def load_memory(user_id: str) -> tuple[dict, dict]:
    """Load user profile and memory. Returns (user_dict, memory_dict)."""
    return (
        memory_store.get_user(user_id) or {},
        memory_store.get_memory(user_id) or {},
    )


async def save_memory(user_id: str, memory: dict, pipeline_id: str = "", results: dict | None = None):
    """Persist memory and optionally save last-run results (without overwriting pipeline definition)."""
    memory_store.save_memory(user_id, memory)
    if pipeline_id and results:
        existing = memory_store.get_pipeline(pipeline_id) or {}
        existing["last_results"] = results
        memory_store.save_pipeline(pipeline_id, existing)
