"""Tests for the Thinker pipeline."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from engine.thinker import (
    build_decompose_prompts,
    build_create_block_prompt,
    build_wire_prompts,
    create_block,
    decompose_intent,
    match_blocks,
    run_thinker,
    wire_pipeline,
)
from engine.state import ThinkerState


def _base_state(**overrides) -> ThinkerState:
    state: ThinkerState = {
        "user_intent": "Summarize top HN posts daily",
        "user_id": "test_user",
        "required_blocks": [],
        "matched_blocks": [],
        "missing_blocks": [],
        "pipeline_json": None,
        "status": "decomposing",
        "error": None,
        "log": [],
    }
    state.update(overrides)
    return state


class TestMatchBlocks:
    @pytest.mark.asyncio
    async def test_all_blocks_found(self):
        state = _base_state(
            required_blocks=[
                {"block_id": "web_search", "reason": "search"},
                {"block_id": "claude_summarize", "reason": "summarize"},
                {"block_id": "notify_push", "reason": "notify"},
            ]
        )
        result = await match_blocks(state)
        assert len(result["matched_blocks"]) == 3
        assert len(result["missing_blocks"]) == 0
        assert result["status"] == "wiring"
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_missing_block_routes_to_creating(self):
        """Missing blocks should set status to 'creating', not 'error'."""
        state = _base_state(
            required_blocks=[
                {"block_id": "web_search", "reason": "search"},
                {"block_id": "nonexistent_block", "reason": "missing"},
            ]
        )
        result = await match_blocks(state)
        assert len(result["matched_blocks"]) == 1
        assert len(result["missing_blocks"]) == 1
        assert result["status"] == "creating"

    @pytest.mark.asyncio
    async def test_new_block_spec_treated_as_missing(self):
        """Block described without block_id → treated as missing → routes to creating."""
        state = _base_state(
            required_blocks=[
                {"block_id": "web_search", "reason": "search"},
                {
                    "suggested_id": "scrape_hn",
                    "description": "custom scraper",
                    "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}},
                    "output_schema": {"type": "object", "properties": {"posts": {"type": "array"}}},
                },
            ]
        )
        result = await match_blocks(state)
        assert len(result["matched_blocks"]) == 1
        assert len(result["missing_blocks"]) == 1
        assert result["status"] == "creating"

    @pytest.mark.asyncio
    async def test_log_entry_added(self):
        state = _base_state(
            required_blocks=[{"block_id": "web_search", "reason": "search"}]
        )
        result = await match_blocks(state)
        assert len(result["log"]) == 1
        assert result["log"][0]["step"] == "match"
        assert "web_search" in result["log"][0]["matched"]


class TestDecomposeIntent:
    @pytest.mark.asyncio
    @patch("engine.thinker.call_llm")
    async def test_decompose_returns_required_blocks(self, mock_llm):
        mock_llm.return_value = json.dumps({
            "required_blocks": [
                {"block_id": "web_search", "reason": "search"},
                {"block_id": "claude_summarize", "reason": "summarize"},
            ]
        })
        state = _base_state()
        result = await decompose_intent(state)
        assert len(result["required_blocks"]) == 2
        assert result["status"] == "matching"
        assert result["log"][-1]["step"] == "decompose"

    @pytest.mark.asyncio
    @patch("engine.thinker.call_llm")
    async def test_decompose_handles_new_block_spec(self, mock_llm):
        mock_llm.return_value = json.dumps({
            "required_blocks": [
                {"suggested_id": "scrape_hn", "description": "scraper",
                 "input_schema": {"type": "object", "properties": {}},
                 "output_schema": {"type": "object", "properties": {}}}
            ]
        })
        state = _base_state()
        result = await decompose_intent(state)
        assert len(result["required_blocks"]) == 1
        assert "suggested_id" in result["required_blocks"][0]


class TestCreateBlock:
    @pytest.mark.asyncio
    @patch("engine.thinker.call_llm")
    async def test_create_registers_block(self, mock_llm):
        mock_llm.return_value = json.dumps({
            "id": "test_new_block",
            "name": "Test New Block",
            "description": "A test block",
            "category": "process",
            "execution_type": "llm",
            "input_schema": {"type": "object", "properties": {"x": {"type": "string"}}},
            "output_schema": {"type": "object", "properties": {"y": {"type": "string"}}},
            "prompt_template": "Process {x}",
        })
        state = _base_state(
            missing_blocks=[{
                "suggested_id": "test_new_block",
                "description": "A test block",
                "input_schema": {"type": "object", "properties": {"x": {"type": "string"}}},
                "output_schema": {"type": "object", "properties": {"y": {"type": "string"}}},
            }]
        )
        result = await create_block(state)
        assert len(result["missing_blocks"]) == 0
        assert any(b["id"] == "test_new_block" for b in result["matched_blocks"])
        assert result["status"] == "wiring"


class TestWirePipeline:
    @pytest.mark.asyncio
    @patch("engine.thinker.call_llm")
    async def test_wire_produces_pipeline_json(self, mock_llm):
        mock_llm.return_value = json.dumps({
            "id": "pipeline_test",
            "name": "Test Pipeline",
            "user_prompt": "test",
            "nodes": [
                {"id": "n1", "block_id": "web_search", "inputs": {"query": "test"}}
            ],
            "edges": [],
            "memory_keys": [],
        })
        state = _base_state(
            matched_blocks=[{
                "id": "web_search",
                "name": "Web Search",
                "description": "Search the web",
                "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
                "output_schema": {"type": "object", "properties": {"results": {"type": "string"}}},
            }]
        )
        result = await wire_pipeline(state)
        assert result["pipeline_json"] is not None
        assert result["pipeline_json"]["id"] == "pipeline_test"
        assert result["status"] == "done"


class TestPromptBuilders:
    def test_build_decompose_prompts(self):
        blocks = [{
            "id": "web_search", "name": "Web Search",
            "description": "Search the web",
            "input_schema": {"properties": {"query": {"type": "string"}}},
            "output_schema": {"properties": {"results": {"type": "string"}}},
        }]
        system, user = build_decompose_prompts("Find news", blocks)
        assert "web_search" in system
        assert "Find news" in user

    def test_build_create_block_prompt(self):
        spec = {
            "suggested_id": "my_block",
            "description": "Does something",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
        }
        system, user = build_create_block_prompt(spec)
        assert "my_block" in user
        assert "prompt_template" in system

    def test_build_wire_prompts(self):
        blocks = [{
            "id": "web_search", "name": "Web Search",
            "description": "Search",
            "input_schema": {}, "output_schema": {},
        }]
        system, user = build_wire_prompts("test intent", blocks)
        assert "web_search" in system
        assert "test intent" in user


class TestRunThinker:
    @pytest.mark.asyncio
    @patch("engine.thinker.call_llm")
    async def test_full_pipeline_with_existing_blocks(self, mock_llm):
        """Full thinker run where all blocks exist in registry."""
        # decompose returns existing blocks
        mock_llm.side_effect = [
            json.dumps({
                "required_blocks": [
                    {"block_id": "web_search", "reason": "search"},
                    {"block_id": "claude_summarize", "reason": "summarize"},
                ]
            }),
            # wire returns pipeline
            json.dumps({
                "id": "pipeline_search_summarize",
                "name": "Search and Summarize",
                "user_prompt": "Search and summarize news",
                "nodes": [
                    {"id": "n1", "block_id": "web_search", "inputs": {"query": "news"}},
                    {"id": "n2", "block_id": "claude_summarize", "inputs": {"text": "{{n1.results}}"}},
                ],
                "edges": [{"from": "n1", "to": "n2"}],
                "memory_keys": [],
            }),
        ]
        result = await run_thinker("Search and summarize news", "test_user")
        assert result["status"] == "done"
        assert result["pipeline_json"] is not None
        assert len(result["pipeline_json"]["nodes"]) == 2


class TestSchemaValidation:
    def test_decompose_output_valid(self):
        from engine.schemas import validate_stage_output

        data = {
            "required_blocks": [
                {"block_id": "web_search", "reason": "search HN"},
                {"block_id": "notify_push", "reason": "notify user"},
            ]
        }
        result = validate_stage_output("decompose", data)
        assert len(result.required_blocks) == 2

    def test_decompose_output_with_new_block(self):
        from engine.schemas import validate_stage_output

        data = {
            "required_blocks": [
                {"block_id": "web_search", "reason": "search"},
                {
                    "suggested_id": "scrape_hn",
                    "description": "Scrape HN front page",
                    "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}},
                    "output_schema": {"type": "object", "properties": {"posts": {"type": "array"}}},
                },
            ]
        }
        result = validate_stage_output("decompose", data)
        assert len(result.required_blocks) == 2

    def test_decompose_output_empty_rejects(self):
        from pydantic import ValidationError
        from engine.schemas import validate_stage_output

        with pytest.raises(ValidationError):
            validate_stage_output("decompose", {"required_blocks": []})

    def test_pipeline_json_valid(self):
        from engine.schemas import validate_stage_output

        data = {
            "pipeline_json": {
                "id": "pipeline_test",
                "name": "Test Pipeline",
                "user_prompt": "test",
                "nodes": [
                    {"id": "n1", "block_id": "web_search", "inputs": {"query": "test"}},
                ],
                "edges": [],
                "memory_keys": [],
            }
        }
        result = validate_stage_output("wire", data)
        assert result.pipeline_json.id == "pipeline_test"

    def test_pipeline_json_missing_nodes_rejects(self):
        from pydantic import ValidationError
        from engine.schemas import validate_stage_output

        with pytest.raises(ValidationError):
            validate_stage_output("wire", {
                "pipeline_json": {
                    "id": "p1",
                    "name": "Bad",
                    "user_prompt": "test",
                    "nodes": [],
                }
            })

    def test_block_definition_valid(self):
        from engine.schemas import BlockDefinition

        block = BlockDefinition(
            id="test_block",
            name="Test Block",
            description="A test",
            category="process",
            execution_type="llm",
            input_schema={"type": "object", "properties": {"x": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"y": {"type": "string"}}},
            prompt_template="Process {x}",
        )
        assert block.id == "test_block"
        assert block.metadata["created_by"] == "thinker"

    def test_create_block_output_valid(self):
        from engine.schemas import validate_stage_output

        data = {
            "created_blocks": [
                {
                    "id": "scrape_hn",
                    "name": "Scrape HN",
                    "description": "Scrape Hacker News front page",
                    "category": "input",
                    "execution_type": "llm",
                    "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}},
                    "output_schema": {"type": "object", "properties": {"posts": {"type": "array"}}},
                    "prompt_template": "Visit {url} and extract posts.",
                }
            ]
        }
        result = validate_stage_output("create_block", data)
        assert len(result.created_blocks) == 1
        assert result.created_blocks[0].id == "scrape_hn"
