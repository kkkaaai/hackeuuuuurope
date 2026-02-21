"""End-to-end tests: user request -> Orchestra -> Builder (if needed) -> Pipeline -> execution."""

import pytest

from app.agents.builder import BuilderAgent
from app.agents.orchestra import OrchestraAgent
from app.blocks.loader import load_all_implementations
from app.blocks.registry import BlockRegistry
from app.database import init_db
from app.engine.runner import PipelineRunner
from app.memory.store import MemoryStore
from app.models.execution import ExecutionStatus


@pytest.fixture(scope="module", autouse=True)
def setup():
    init_db()
    load_all_implementations()


@pytest.fixture()
def registry():
    reg = BlockRegistry()
    reg.load_from_directory()
    return reg


@pytest.fixture()
def mem():
    store = MemoryStore()
    store.clear_namespace("e2e_test")
    yield store
    store.clear_namespace("e2e_test")


class TestEndToEnd:
    @pytest.mark.asyncio
    async def test_search_and_summarize(self, registry, mem):
        """User: 'Search for AI news' -> decompose -> execute."""
        orchestra = OrchestraAgent(registry)
        runner = PipelineRunner(registry=registry, memory=mem)

        # Decompose
        decomposition = await orchestra.decompose("Search for AI news")
        pipeline = orchestra.build_pipeline("Search for AI news", decomposition)

        # Execute
        result = await runner.run(pipeline)
        assert result.status == ExecutionStatus.COMPLETED
        assert len(result.shared_context) >= 2  # At least trigger + one more block

    @pytest.mark.asyncio
    async def test_daily_news_briefing(self, registry, mem):
        """User: 'Every morning, summarize top tech news' -> cron pipeline."""
        orchestra = OrchestraAgent(registry)
        runner = PipelineRunner(registry=registry, memory=mem)

        decomposition = await orchestra.decompose("Every morning, summarize top tech news")
        pipeline = orchestra.build_pipeline("Every morning, summarize top tech news", decomposition)

        assert pipeline.trigger.type.value == "cron"

        result = await runner.run(pipeline)
        assert result.status == ExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_with_missing_block_creation(self, registry, mem):
        """Orchestra identifies a missing block -> Builder creates it -> pipeline runs."""
        orchestra = OrchestraAgent(registry)
        builder = BuilderAgent(registry)
        runner = PipelineRunner(registry=registry, memory=mem)

        # Decompose
        decomposition = await orchestra.decompose("Track Bitcoin price")

        # If there are missing blocks, have Builder create them
        missing = decomposition.get("missing_blocks", [])
        if missing:
            await builder.create_missing_blocks(missing)

        pipeline = orchestra.build_pipeline("Track Bitcoin price", decomposition)
        result = await runner.run(pipeline)
        assert result.status == ExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_full_flow_with_notification(self, registry, mem):
        """Verify the pipeline produces a notification at the end."""
        orchestra = OrchestraAgent(registry)
        runner = PipelineRunner(registry=registry, memory=mem)

        decomposition = await orchestra.decompose("Find best laptop deals")
        pipeline = orchestra.build_pipeline("Find best laptop deals", decomposition)

        result = await runner.run(pipeline)
        assert result.status == ExecutionStatus.COMPLETED

        # At least one node should have produced a notification (delivered=True)
        has_notification = any(
            isinstance(v, dict) and v.get("delivered") is True
            for v in result.shared_context.values()
        )
        assert has_notification, (
            f"No notification found in shared_context keys: {list(result.shared_context.keys())}"
        )
