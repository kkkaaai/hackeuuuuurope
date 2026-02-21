"""Tests for the Doer pipeline — end-to-end with Python blocks."""

import pytest

from engine.doer import run_pipeline


class TestDoerPipeline:
    @pytest.mark.asyncio
    async def test_simple_two_node_pipeline(self, sample_pipeline_json):
        """filter_threshold → notify_push, verify results and template resolution."""
        result = await run_pipeline(sample_pipeline_json, "test_user")

        # n1: filter_threshold (42 > 10 → passed=True)
        assert result["results"]["n1"]["passed"] is True
        assert result["results"]["n1"]["value"] == 42.0

        # n2: notify_push — body should have resolved {{n1.passed}}
        assert result["results"]["n2"]["delivered"] is True

    @pytest.mark.asyncio
    async def test_three_node_chain(self, three_node_pipeline):
        """filter → branch → notify, verify data flows through."""
        result = await run_pipeline(three_node_pipeline, "test_user")

        assert result["results"]["n1"]["passed"] is True
        assert result["results"]["n2"]["branch"] == "yes"
        assert result["results"]["n3"]["delivered"] is True

    @pytest.mark.asyncio
    async def test_parallel_nodes(self, parallel_pipeline):
        """Two independent root nodes should both execute before the sink node."""
        result = await run_pipeline(parallel_pipeline, "test_user")

        # Both root nodes ran
        assert result["results"]["n1"]["passed"] is True
        assert result["results"]["n2"]["passed"] is True

        # Sink node ran after both
        assert result["results"]["n3"]["delivered"] is True

    @pytest.mark.asyncio
    async def test_memory_load_save_in_log(self, sample_pipeline_json):
        """Verify _load_memory and _save_memory appear in the log."""
        result = await run_pipeline(sample_pipeline_json, "test_user")
        steps = [entry.get("step") for entry in result["log"]]
        assert "_load_memory" in steps
        assert "_save_memory" in steps

    @pytest.mark.asyncio
    async def test_pipeline_state_structure(self, sample_pipeline_json):
        """Verify returned state has expected top-level keys."""
        result = await run_pipeline(sample_pipeline_json, "test_user")
        assert "results" in result
        assert "log" in result
        assert "pipeline_id" in result
        assert result["pipeline_id"] == "test_pipeline"
