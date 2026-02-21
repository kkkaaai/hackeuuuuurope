"""Activity endpoints — execution history and notifications."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from app.database import get_db

router = APIRouter(prefix="/api", tags=["activity"])


@router.get("/executions")
async def list_executions(limit: int = 50) -> list[dict]:
    """List recent execution runs, grouped by run_id."""
    limit = min(limit, 500)

    with get_db() as conn:
        rows = conn.execute(
            """SELECT run_id, pipeline_id,
                      COUNT(*) as node_count,
                      MAX(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as has_failure,
                      MAX(finished_at) as finished_at
               FROM execution_logs
               GROUP BY run_id
               ORDER BY finished_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()

    # Also get pipeline intents for display
    pipeline_intents: dict[str, str] = {}
    if rows:
        pipeline_ids = list({r["pipeline_id"] for r in rows})
        placeholders = ",".join("?" for _ in pipeline_ids)
        with get_db() as conn:
            intent_rows = conn.execute(
                f"SELECT id, user_intent FROM pipelines WHERE id IN ({placeholders})",
                pipeline_ids,
            ).fetchall()
            for row in intent_rows:
                pipeline_intents[row["id"]] = row["user_intent"]

    return [
        {
            "run_id": r["run_id"],
            "pipeline_id": r["pipeline_id"],
            "pipeline_intent": pipeline_intents.get(r["pipeline_id"], "Unknown pipeline"),
            "node_count": r["node_count"],
            "status": "failed" if r["has_failure"] else "completed",
            "finished_at": r["finished_at"],
        }
        for r in rows
    ]


@router.get("/executions/{run_id}")
async def get_execution(run_id: str) -> dict:
    """Get all node-level results for a specific run."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, pipeline_id, run_id, node_id, status,
                      output_data, error, finished_at
               FROM execution_logs
               WHERE run_id = ?
               ORDER BY id""",
            (run_id,),
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="Execution run not found")

    nodes = []
    for r in rows:
        output = None
        if r["output_data"]:
            try:
                output = json.loads(r["output_data"])
            except json.JSONDecodeError:
                output = r["output_data"]
        nodes.append({
            "id": r["id"],
            "node_id": r["node_id"],
            "status": r["status"],
            "output_data": output,
            "error": r["error"],
            "finished_at": r["finished_at"],
        })

    has_failure = any(n["status"] == "failed" for n in nodes)
    return {
        "run_id": run_id,
        "pipeline_id": rows[0]["pipeline_id"],
        "status": "failed" if has_failure else "completed",
        "nodes": nodes,
    }


@router.get("/notifications")
async def list_notifications(limit: int = 50, unread_only: bool = False) -> list[dict]:
    """List notifications, newest first."""
    limit = min(limit, 500)

    query = "SELECT * FROM notifications"
    params: list = []

    if unread_only:
        query += " WHERE read = 0"

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        {
            "id": r["id"],
            "pipeline_id": r["pipeline_id"],
            "run_id": r["run_id"],
            "node_id": r["node_id"],
            "title": r["title"],
            "message": r["message"],
            "level": r["level"],
            "category": r["category"],
            "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
            "read": bool(r["read"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int) -> dict:
    """Mark a notification as read."""
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE notifications SET read = 1 WHERE id = ?",
            (notification_id,),
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Notification not found")

    return {"status": "ok"}
