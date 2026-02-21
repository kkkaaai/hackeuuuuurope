"""Tests for the Orchestra Agent."""

import pytest

from app.agents.orchestra import OrchestraAgent
from app.blocks.registry import BlockRegistry
from app.models.pipeline import PipelineStatus, TriggerType


@pytest.fixture()
def registry():
    reg = BlockRegistry()
    reg.load_from_directory()
    return reg


@pytest.fixture()
def orchestra(registry):
    return OrchestraAgent(registry)


class TestOrchestraDecompose:
    @pytest.mark.asyncio
    async def test_manual_task_decomposition(self, orchestra):
        """A one-time task should produce a manual trigger pipeline."""
        result = await orchestra.decompose(
            "Find me cheap flights to London departing next Friday, return Sunday"
        )
        # May return clarification or pipeline — both are valid
        if result.get("type") == "clarification":
            assert "message" in result
            assert "questions" in result
            return
        assert result["trigger"]["type"] == "manual"
        assert len(result["nodes"]) >= 2  # At least trigger + something
        assert len(result["edges"]) >= 1

    @pytest.mark.asyncio
    async def test_daily_task_decomposition(self, orchestra):
        """A daily task should produce a cron trigger."""
        result = await orchestra.decompose("Every morning, summarize top news")
        assert result["trigger"]["type"] == "cron"
        assert result["trigger"]["schedule"] is not None

    @pytest.mark.asyncio
    async def test_weekly_task_decomposition(self, orchestra):
        """A weekly task should produce a cron trigger."""
        result = await orchestra.decompose("Every Tuesday, buy milk")
        assert result["trigger"]["type"] == "cron"

    @pytest.mark.asyncio
    async def test_search_task_includes_web_search(self, orchestra):
        """A search request should include the web_search block."""
        result = await orchestra.decompose("Search for best protein powder")
        block_ids = [n["block_id"] for n in result["nodes"]]
        assert "web_search" in block_ids

    @pytest.mark.asyncio
    async def test_price_monitoring_includes_threshold(self, orchestra):
        """A price monitoring task should include a threshold or condition block."""
        result = await orchestra.decompose("Monitor Amazon for PS5 below 400 euros")
        block_ids = [n["block_id"] for n in result["nodes"]]
        assert "conditional_branch" in block_ids or "filter_threshold" in block_ids

    @pytest.mark.asyncio
    async def test_always_ends_with_notification(self, orchestra):
        """Every pipeline should end with a notification block."""
        result = await orchestra.decompose("Find me cheap flights")
        block_ids = [n["block_id"] for n in result["nodes"]]
        assert "notify_in_app" in block_ids

    @pytest.mark.asyncio
    async def test_missing_blocks_field_present(self, orchestra):
        """Decomposition should always include missing_blocks (even if empty)."""
        result = await orchestra.decompose("Search for news")
        assert "missing_blocks" in result


class TestOrchestraBuildPipeline:
    @pytest.mark.asyncio
    async def test_build_pipeline_from_decomposition(self, orchestra):
        """Converting decomposition to Pipeline model should work."""
        decomposition = await orchestra.decompose("Search for AI news every morning")
        pipeline = orchestra.build_pipeline("Search for AI news every morning", decomposition)

        assert pipeline.id.startswith("pipe_")
        assert pipeline.user_intent == "Search for AI news every morning"
        assert pipeline.status == PipelineStatus.CREATED
        assert len(pipeline.nodes) >= 2
        assert len(pipeline.edges) >= 1

    @pytest.mark.asyncio
    async def test_build_pipeline_cron_trigger(self, orchestra):
        """Cron decomposition should produce a cron trigger config."""
        decomposition = await orchestra.decompose("Every day check the news")
        pipeline = orchestra.build_pipeline("Every day check the news", decomposition)

        assert pipeline.trigger.type == TriggerType.CRON
        assert pipeline.trigger.schedule is not None

    @pytest.mark.asyncio
    async def test_build_pipeline_manual_trigger(self, orchestra):
        """One-time request should produce a manual trigger."""
        decomposition = await orchestra.decompose("Find best laptop under 1000")
        pipeline = orchestra.build_pipeline("Find best laptop under 1000", decomposition)

        assert pipeline.trigger.type == TriggerType.MANUAL
