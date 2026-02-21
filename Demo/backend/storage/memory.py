"""Supabase-backed store for pipelines, executions, notifications, and user memory.

Replaces the old in-memory MemoryStore. Same interface, Supabase under the hood.
"""

from __future__ import annotations

import json
import logging

from storage.supabase_client import get_supabase

logger = logging.getLogger(__name__)


class SupabaseStore:
    """Persistent store backed by Supabase tables."""

    # ── User Memory ──

    def get_memory(self, user_id: str) -> dict | None:
        """Get all memory key-value pairs for a user."""
        sb = get_supabase()
        result = sb.table("user_memory").select("key, value").eq("user_id", user_id).execute()
        if not result.data:
            return {}
        memory = {}
        for row in result.data:
            val = row["value"]
            # value is stored as jsonb, so it may already be parsed
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    pass
            memory[row["key"]] = val
        return memory

    def save_memory(self, user_id: str, data: dict):
        """Save full memory dict for a user (upserts each key)."""
        sb = get_supabase()
        for key, value in data.items():
            sb.table("user_memory").upsert({
                "user_id": user_id,
                "key": key,
                "value": json.dumps(value) if not isinstance(value, (str, int, float, bool)) else json.dumps(value),
            }).execute()

    # ── Pipelines ──

    def get_pipeline(self, pipeline_id: str) -> dict | None:
        sb = get_supabase()
        result = sb.table("pipelines").select("*").eq("id", pipeline_id).execute()
        if not result.data:
            return None
        row = result.data[0]
        return self._row_to_pipeline(row)

    def save_pipeline(self, pipeline_id: str, data: dict):
        sb = get_supabase()
        row = {
            "id": pipeline_id,
            "name": data.get("name", "Untitled"),
            "user_prompt": data.get("user_prompt", ""),
            "user_id": data.get("user_id", "default_user"),
            "nodes": data.get("nodes", []),
            "edges": data.get("edges", []),
            "memory_keys": data.get("memory_keys", []),
            "status": data.get("status", "created"),
            "trigger_type": data.get("trigger_type", "manual"),
            "node_count": len(data.get("nodes", [])),
        }
        sb.table("pipelines").upsert(row).execute()

    def list_pipelines(self) -> list[dict]:
        sb = get_supabase()
        result = sb.table("pipelines").select("id, name, user_prompt, status, trigger_type, node_count, created_at").order("created_at", desc=True).execute()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "user_intent": r.get("user_prompt", ""),
                "user_prompt": r.get("user_prompt", ""),
                "status": r.get("status", "created"),
                "trigger_type": r.get("trigger_type", "manual"),
                "node_count": r.get("node_count", 0),
                "created_at": r.get("created_at", ""),
            }
            for r in result.data
        ]

    def delete_pipeline(self, pipeline_id: str):
        sb = get_supabase()
        sb.table("pipelines").delete().eq("id", pipeline_id).execute()

    # Aliases for backward compatibility with main.py
    def get_pipeline_summary(self, pipeline_id: str) -> dict | None:
        return self.get_pipeline(pipeline_id)

    def save_pipeline_summary(self, pipeline_id: str, data: dict):
        # Pipeline summary is now just the pipeline row itself
        self.save_pipeline(pipeline_id, data)

    def delete_pipeline_summary(self, pipeline_id: str):
        self.delete_pipeline(pipeline_id)

    # ── Executions ──

    def save_execution(self, run_id: str, data: dict):
        sb = get_supabase()
        row = {
            "run_id": run_id,
            "pipeline_id": data.get("pipeline_id"),
            "pipeline_name": data.get("pipeline_name", ""),
            "pipeline_intent": data.get("pipeline_intent", ""),
            "user_id": data.get("user_id", "default_user"),
            "status": data.get("status", "completed"),
            "node_count": data.get("node_count", 0),
            "node_results": data.get("nodes", []),
            "shared_context": data.get("shared_context", {}),
            "errors": data.get("errors", []),
            "finished_at": data.get("finished_at"),
        }
        sb.table("executions").upsert(row).execute()

    def list_executions(self, limit: int = 50) -> list[dict]:
        sb = get_supabase()
        result = sb.table("executions").select("*").order("finished_at", desc=True).limit(limit).execute()
        return result.data or []

    def get_execution(self, run_id: str) -> dict | None:
        sb = get_supabase()
        result = sb.table("executions").select("*").eq("run_id", run_id).execute()
        if not result.data:
            return None
        return result.data[0]

    # ── Notifications ──

    def add_notification(self, notif: dict):
        sb = get_supabase()
        sb.table("notifications").insert({
            "user_id": notif.get("user_id", "default_user"),
            "title": notif.get("title", ""),
            "body": notif.get("body", ""),
            "metadata": notif.get("metadata", {}),
        }).execute()

    def list_notifications(self, limit: int = 50) -> list[dict]:
        sb = get_supabase()
        result = sb.table("notifications").select("*").order("created_at", desc=True).limit(limit).execute()
        return result.data or []

    def mark_notification_read(self, notif_id: int):
        sb = get_supabase()
        sb.table("notifications").update({"read": True}).eq("id", notif_id).execute()

    # ── Helpers ──

    @staticmethod
    def _row_to_pipeline(row: dict) -> dict:
        """Convert a Supabase pipeline row to the dict format used by the engine."""
        return {
            "id": row["id"],
            "name": row.get("name", "Untitled"),
            "user_prompt": row.get("user_prompt", ""),
            "nodes": row.get("nodes", []),
            "edges": row.get("edges", []),
            "memory_keys": row.get("memory_keys", []),
            "status": row.get("status", "created"),
        }


memory_store = SupabaseStore()
