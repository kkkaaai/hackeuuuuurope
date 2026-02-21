"""Tests for all API endpoints."""

import json

import pytest
from fastapi.testclient import TestClient

from app.database import init_db, get_db
from app.main import app


@pytest.fixture(scope="module", autouse=True)
def setup():
    init_db()


@pytest.fixture()
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestChatEndpoint:
    def test_chat_decompose(self, client):
        """POST /api/chat should decompose a request into a pipeline."""
        resp = client.post(
            "/api/chat",
            json={"message": "Search for AI news every morning"},
        )
        assert resp.status_code == 200
        data = resp.json()
        if data.get("response_type") == "clarification":
            assert data["clarification_message"]
            return
        assert data["pipeline_id"].startswith("pipe_")
        assert data["user_intent"] == "Search for AI news every morning"
        assert len(data["nodes"]) >= 2
        assert len(data["edges"]) >= 1

    def test_chat_with_auto_execute(self, client):
        """POST /api/chat with auto_execute should run the pipeline or ask for clarification."""
        resp = client.post(
            "/api/chat",
            json={"message": "Summarize the top 3 Hacker News stories right now", "auto_execute": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        if data.get("response_type") == "clarification":
            # Clarification is a valid response
            assert data["clarification_message"]
            assert len(data["questions"]) > 0
        else:
            assert data["execution_result"] is not None
            assert data["execution_result"]["status"] in ("completed", "failed")

    def test_chat_empty_message(self, client):
        resp = client.post("/api/chat", json={"message": ""})
        assert resp.status_code == 422  # Validation error


class TestBlocksEndpoint:
    def test_list_all_blocks(self, client):
        resp = client.get("/api/blocks")
        assert resp.status_code == 200
        blocks = resp.json()
        assert len(blocks) == 35

    def test_list_blocks_by_category(self, client):
        resp = client.get("/api/blocks?category=trigger")
        assert resp.status_code == 200
        blocks = resp.json()
        assert len(blocks) == 4
        assert all(b["category"] == "trigger" for b in blocks)

    def test_get_single_block(self, client):
        resp = client.get("/api/blocks/web_search")
        assert resp.status_code == 200
        block = resp.json()
        assert block["id"] == "web_search"
        assert block["category"] == "perceive"

    def test_get_nonexistent_block(self, client):
        resp = client.get("/api/blocks/nonexistent")
        assert resp.status_code == 404

    def test_search_blocks(self, client):
        resp = client.post("/api/blocks/search", json={"query": "payment stripe"})
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) > 0
        assert results[0]["id"] == "stripe_pay"


class TestPipelinesEndpoint:
    def _create_pipeline(self, client) -> str:
        """Helper: create a pipeline via chat and return its ID."""
        resp = client.post(
            "/api/chat",
            json={"message": "Search for tech news"},
        )
        return resp.json()["pipeline_id"]

    def test_pipeline_crud_flow(self, client):
        """Create -> List -> Get -> Delete flow."""
        # Create via chat (use specific request unlikely to trigger clarification)
        chat_resp = client.post(
            "/api/chat",
            json={"message": "Summarize the top 5 Hacker News stories right now"},
        )
        pipeline_data = chat_resp.json()

        # If clarification, skip CRUD test
        if pipeline_data.get("response_type") == "clarification":
            pytest.skip("Got clarification response instead of pipeline")

        # Store it
        store_resp = client.post(
            "/api/pipelines",
            json={"pipeline": {
                "id": pipeline_data["pipeline_id"],
                "user_intent": pipeline_data["user_intent"],
                "trigger": {"type": pipeline_data["trigger_type"]},
                "nodes": pipeline_data["nodes"],
                "edges": pipeline_data["edges"],
            }},
        )
        assert store_resp.status_code == 200
        pid = store_resp.json()["id"]

        # List
        list_resp = client.get("/api/pipelines")
        assert list_resp.status_code == 200
        assert any(p["id"] == pid for p in list_resp.json())

        # Get
        get_resp = client.get(f"/api/pipelines/{pid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == pid

        # Delete
        del_resp = client.delete(f"/api/pipelines/{pid}")
        assert del_resp.status_code == 200

        # Verify deleted
        get_resp2 = client.get(f"/api/pipelines/{pid}")
        assert get_resp2.status_code == 404


class TestWebhookEndpoint:
    def test_receive_webhook(self, client):
        resp = client.post(
            "/api/webhooks/my-trigger",
            json={"event": "push", "repo": "test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["received"] is True
        assert data["webhook_path"] == "my-trigger"


class TestUploadEndpoint:
    def test_file_upload(self, client):
        resp = client.post(
            "/api/upload",
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["file_size_bytes"] == 11
        assert data["file_type"] == "text/plain"
        assert "file_id" in data
        assert "file_path" not in data  # No server path leak


class TestActivityEndpoints:
    def test_list_executions_empty(self, client):
        resp = client.get("/api/executions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_execution_not_found(self, client):
        resp = client.get("/api/executions/nonexistent_run")
        assert resp.status_code == 404

    def test_list_notifications_empty(self, client):
        resp = client.get("/api/notifications")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_notification_crud(self, client):
        """Insert a notification directly and verify API returns it."""
        with get_db() as conn:
            conn.execute(
                """INSERT INTO notifications (title, message, level, category)
                   VALUES (?, ?, ?, ?)""",
                ("Test Alert", "Something happened", "info", "notification"),
            )
            conn.commit()

        resp = client.get("/api/notifications")
        assert resp.status_code == 200
        notifs = resp.json()
        test_notif = next((n for n in notifs if n["title"] == "Test Alert"), None)
        assert test_notif is not None
        assert test_notif["message"] == "Something happened"
        assert test_notif["read"] is False

        # Mark as read
        mark_resp = client.post(f"/api/notifications/{test_notif['id']}/read")
        assert mark_resp.status_code == 200

        # Verify it's read
        resp2 = client.get("/api/notifications")
        test_notif2 = next((n for n in resp2.json() if n["id"] == test_notif["id"]), None)
        assert test_notif2["read"] is True

    def test_mark_nonexistent_notification(self, client):
        resp = client.post("/api/notifications/999999/read")
        assert resp.status_code == 404

    def test_execution_log_persistence(self, client):
        """Insert execution logs and verify API returns them grouped."""
        import uuid
        pipe_id = f"pipe_activity_test_{uuid.uuid4().hex[:8]}"
        run_id = f"run_activity_test_{uuid.uuid4().hex[:8]}"

        with get_db() as conn:
            conn.execute(
                """INSERT INTO pipelines (id, user_intent, definition, status)
                   VALUES (?, ?, ?, ?)""",
                (pipe_id, "Test pipeline", "{}", "completed"),
            )
            conn.execute(
                """INSERT INTO execution_logs
                   (pipeline_id, run_id, node_id, status, output_data, finished_at)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                (pipe_id, run_id, "node_1", "completed", json.dumps({"result": 42})),
            )
            conn.execute(
                """INSERT INTO execution_logs
                   (pipeline_id, run_id, node_id, status, output_data, finished_at)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                (pipe_id, run_id, "node_2", "completed", json.dumps({"output": "done"})),
            )
            conn.commit()

        # List executions
        resp = client.get("/api/executions")
        assert resp.status_code == 200
        runs = resp.json()
        test_run = next((r for r in runs if r["run_id"] == run_id), None)
        assert test_run is not None
        assert test_run["node_count"] == 2
        assert test_run["status"] == "completed"
        assert test_run["pipeline_intent"] == "Test pipeline"

        # Get execution detail
        detail_resp = client.get(f"/api/executions/{run_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["run_id"] == run_id
        assert len(detail["nodes"]) == 2
        assert detail["nodes"][0]["output_data"]["result"] == 42
