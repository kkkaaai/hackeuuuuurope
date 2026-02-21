"""In-app notification block — stores notification in the memory store."""

import uuid

from storage.memory import memory_store


async def execute(inputs: dict, context: dict) -> dict:
    title = inputs["title"]
    message = inputs["message"]
    level = inputs.get("level", "info")

    notif_id = f"notif_{uuid.uuid4().hex[:8]}"
    memory_store.add_notification({
        "notification_id": notif_id,
        "title": title,
        "message": message,
        "level": level,
        "read": False,
    })

    print(f"[NOTIFICATION] [{level.upper()}] {title}: {message}")
    return {"notification_id": notif_id, "delivered": True}
