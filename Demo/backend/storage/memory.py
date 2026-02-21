"""In-memory store for users, memory, and pipelines.

Hackathon-grade: everything lives in dicts. Swap for a real DB later.
"""


class MemoryStore:
    def __init__(self):
        self._users: dict[str, dict] = {}
        self._memory: dict[str, dict] = {}
        self._pipelines: dict[str, dict] = {}
        self._executions: dict[str, dict] = {}
        self._notifications: list[dict] = []
        self._pipeline_list: dict[str, dict] = {}

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

    def list_pipelines(self) -> list[dict]:
        return sorted(self._pipeline_list.values(), key=lambda p: p.get("created_at", ""), reverse=True)

    def get_pipeline_summary(self, pipeline_id: str) -> dict | None:
        return self._pipeline_list.get(pipeline_id)

    def save_pipeline_summary(self, pipeline_id: str, data: dict):
        self._pipeline_list[pipeline_id] = data

    def delete_pipeline_summary(self, pipeline_id: str):
        self._pipeline_list.pop(pipeline_id, None)
        self._pipelines.pop(pipeline_id, None)

    def save_execution(self, run_id: str, data: dict):
        self._executions[run_id] = data

    def list_executions(self, limit: int = 50) -> list[dict]:
        execs = sorted(self._executions.values(), key=lambda e: e.get("finished_at", ""), reverse=True)
        return execs[:limit]

    def get_execution(self, run_id: str) -> dict | None:
        return self._executions.get(run_id)

    def add_notification(self, notif: dict):
        notif["id"] = len(self._notifications) + 1
        self._notifications.append(notif)

    def list_notifications(self, limit: int = 50) -> list[dict]:
        return list(reversed(self._notifications[-limit:]))

    def mark_notification_read(self, notif_id: int):
        for n in self._notifications:
            if n.get("id") == notif_id:
                n["read"] = True
                break


memory_store = MemoryStore()
