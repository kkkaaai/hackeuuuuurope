"""In-memory store for users, memory, and pipelines.

Hackathon-grade: everything lives in dicts. Swap for a real DB later.
"""


class MemoryStore:
    def __init__(self):
        self._users: dict[str, dict] = {}
        self._memory: dict[str, dict] = {}
        self._pipelines: dict[str, dict] = {}

    def get_user(self, user_id: str) -> dict | None:
        return self._users.get(user_id)

    def save_user(self, user_id: str, data: dict):
        self._users[user_id] = data

    def get_memory(self, user_id: str) -> dict | None:
        return self._memory.get(user_id)

    def save_memory(self, user_id: str, data: dict):
        self._memory[user_id] = data

    def get_pipeline(self, pipeline_id: str) -> dict | None:
        return self._pipelines.get(pipeline_id)

    def save_pipeline(self, pipeline_id: str, data: dict):
        self._pipelines[pipeline_id] = data


memory_store = MemoryStore()
