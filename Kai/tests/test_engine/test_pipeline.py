"""Tests for the pipeline execution engine."""

import pytest

from app.blocks.loader import load_all_implementations
from app.blocks.registry import BlockRegistry
from app.database import init_db
from app.engine.runner import PipelineRunner
from app.memory.store import MemoryStore
from app.models.execution import ExecutionStatus
from app.models.pipeline import (
    Pipeline,
    PipelineEdge,
    PipelineNode,
    TriggerConfig,
    TriggerType,
)


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
    store.clear_namespace("test_pipeline")
    yield store
    store.clear_namespace("test_pipeline")


@pytest.fixture()
def runner(registry, mem):
    return PipelineRunner(registry=registry, memory=mem)


class TestLinearPipeline:
    """A -> B -> C linear pipeline."""

    @pytest.mark.asyncio
    async def test_trigger_to_notify(self, runner):
        """trigger_manual -> notify_in_app: simplest possible pipeline."""
        pipeline = Pipeline(
            id="test_linear_1",
            user_intent="Test linear pipeline",
            trigger=TriggerConfig(type=TriggerType.MANUAL),
            nodes=[
                PipelineNode(id="t1", block_id="trigger_manual"),
                PipelineNode(
                    id="n1",
                    block_id="notify_in_app",
                    inputs={"title": "Test", "message": "Pipeline ran!"},
                ),
            ],
            edges=[PipelineEdge(from_node="t1", to_node="n1")],
        )
        result = await runner.run(pipeline, trigger_data={"user_input": "go"})

        assert result.status == ExecutionStatus.COMPLETED
        assert "t1" in result.shared_context
        assert "n1" in result.shared_context
        assert result.shared_context["n1"]["delivered"] is True

    @pytest.mark.asyncio
    async def test_three_step_pipeline(self, runner):
        """trigger_manual -> web_search(mock) -> claude_summarize(mock)."""
        pipeline = Pipeline(
            id="test_linear_3",
            user_intent="Search and summarize",
            trigger=TriggerConfig(type=TriggerType.MANUAL),
            nodes=[
                PipelineNode(id="trigger", block_id="trigger_manual"),
                PipelineNode(
                    id="search",
                    block_id="web_search",
                    inputs={"query": "AI news", "num_results": 2},
                ),
                PipelineNode(
                    id="summarize",
                    block_id="claude_summarize",
                    inputs={"content": "{{search.results}}"},
                ),
            ],
            edges=[
                PipelineEdge(from_node="trigger", to_node="search"),
                PipelineEdge(from_node="search", to_node="summarize"),
            ],
        )
        result = await runner.run(pipeline)

        assert result.status == ExecutionStatus.COMPLETED
        assert "search" in result.shared_context
        assert "summarize" in result.shared_context
        assert "summary" in result.shared_context["summarize"]


class TestBranchingPipeline:
    """A -> condition -> B or C."""

    @pytest.mark.asyncio
    async def test_branch_true(self, runner):
        """Condition passes -> takes true branch."""
        pipeline = Pipeline(
            id="test_branch_true",
            user_intent="Test branching (true path)",
            trigger=TriggerConfig(type=TriggerType.MANUAL),
            nodes=[
                PipelineNode(id="trigger", block_id="trigger_manual"),
                PipelineNode(
                    id="check",
                    block_id="conditional_branch",
                    inputs={"condition": "price < 400", "value": 350},
                ),
                PipelineNode(
                    id="yes_branch",
                    block_id="notify_in_app",
                    inputs={"title": "Buy!", "message": "Price is low"},
                ),
                PipelineNode(
                    id="no_branch",
                    block_id="notify_in_app",
                    inputs={"title": "Wait", "message": "Price is still high"},
                ),
            ],
            edges=[
                PipelineEdge(from_node="trigger", to_node="check"),
                PipelineEdge(from_node="check", to_node="yes_branch", condition="true"),
                PipelineEdge(from_node="check", to_node="no_branch", condition="false"),
            ],
        )
        result = await runner.run(pipeline)

        assert result.status == ExecutionStatus.COMPLETED
        assert "yes_branch" in result.shared_context
        # no_branch should NOT have executed
        assert "no_branch" not in result.shared_context

    @pytest.mark.asyncio
    async def test_branch_false(self, runner):
        """Condition fails -> takes false branch."""
        pipeline = Pipeline(
            id="test_branch_false",
            user_intent="Test branching (false path)",
            trigger=TriggerConfig(type=TriggerType.MANUAL),
            nodes=[
                PipelineNode(id="trigger", block_id="trigger_manual"),
                PipelineNode(
                    id="check",
                    block_id="conditional_branch",
                    inputs={"condition": "price < 400", "value": 450},
                ),
                PipelineNode(
                    id="yes_branch",
                    block_id="notify_in_app",
                    inputs={"title": "Buy!", "message": "Price is low"},
                ),
                PipelineNode(
                    id="no_branch",
                    block_id="notify_in_app",
                    inputs={"title": "Wait", "message": "Price is still high"},
                ),
            ],
            edges=[
                PipelineEdge(from_node="trigger", to_node="check"),
                PipelineEdge(from_node="check", to_node="yes_branch", condition="true"),
                PipelineEdge(from_node="check", to_node="no_branch", condition="false"),
            ],
        )
        result = await runner.run(pipeline)

        assert result.status == ExecutionStatus.COMPLETED
        assert "no_branch" in result.shared_context
        assert "yes_branch" not in result.shared_context


class TestMemoryPipeline:
    """Pipeline that reads and writes memory."""

    @pytest.mark.asyncio
    async def test_write_then_read(self, runner, mem):
        """Write to memory in one pipeline, read in another."""
        # Pipeline 1: Write
        write_pipeline = Pipeline(
            id="test_mem_write",
            user_intent="Write to memory",
            trigger=TriggerConfig(type=TriggerType.MANUAL),
            nodes=[
                PipelineNode(id="trigger", block_id="trigger_manual"),
                PipelineNode(
                    id="write",
                    block_id="memory_write",
                    inputs={"key": "test_value", "value": 42, "namespace": "test_pipeline"},
                ),
            ],
            edges=[PipelineEdge(from_node="trigger", to_node="write")],
        )
        r1 = await runner.run(write_pipeline)
        assert r1.status == ExecutionStatus.COMPLETED

        # Pipeline 2: Read
        read_pipeline = Pipeline(
            id="test_mem_read",
            user_intent="Read from memory",
            trigger=TriggerConfig(type=TriggerType.MANUAL),
            nodes=[
                PipelineNode(id="trigger", block_id="trigger_manual"),
                PipelineNode(
                    id="read",
                    block_id="memory_read",
                    inputs={"key": "test_value", "namespace": "test_pipeline"},
                ),
            ],
            edges=[PipelineEdge(from_node="trigger", to_node="read")],
        )
        r2 = await runner.run(read_pipeline)
        assert r2.status == ExecutionStatus.COMPLETED
        assert r2.shared_context["read"]["value"] == 42
        assert r2.shared_context["read"]["found"] is True


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_missing_block(self, runner):
        """Pipeline with a non-existent block should fail at build time."""
        pipeline = Pipeline(
            id="test_error",
            user_intent="Should fail",
            trigger=TriggerConfig(type=TriggerType.MANUAL),
            nodes=[
                PipelineNode(id="t1", block_id="nonexistent_block_xyz"),
            ],
            edges=[],
        )
        result = await runner.run(pipeline)
        assert result.status == ExecutionStatus.FAILED
        assert any("not found" in e for e in result.errors)
