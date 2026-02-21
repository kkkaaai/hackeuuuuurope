"""Tests for the Thinker shared utilities."""

import json

import pytest

from engine.thinker import (
    _is_good_match,
    build_decompose_prompts,
    build_create_block_prompt,
    build_wire_prompts,
)


class TestIsGoodMatch:
    def test_matching_block_passes(self):
        candidate = {"id": "web_search", "description": "Search the web for results", "execution_type": "python",
                      "input_schema": {"properties": {"query": {"type": "string"}}},
                      "output_schema": {"properties": {"results": {"type": "array"}}}}
        req = {"suggested_id": "web_search", "description": "Search the web", "execution_type": "python",
               "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
               "output_schema": {"type": "object", "properties": {"results": {"type": "array"}}}}
        assert _is_good_match(candidate, req) is True

    def test_legacy_llm_block_still_matches(self):
        """Legacy llm blocks should match since executor auto-converts them."""
        candidate = {"id": "summarize", "description": "Summarize text", "execution_type": "llm",
                      "input_schema": {"properties": {}}, "output_schema": {"properties": {}}}
        req = {"suggested_id": "summarize", "description": "Summarize text", "execution_type": "python",
               "input_schema": {"type": "object", "properties": {}},
               "output_schema": {"type": "object", "properties": {}}}
        assert _is_good_match(candidate, req) is True

    def test_different_blocks_still_pass(self):
        """_is_good_match trusts embedding search — always returns True."""
        candidate = {"id": "send_email", "description": "Send an email notification",
                      "execution_type": "python",
                      "input_schema": {"properties": {"to": {"type": "string"}}},
                      "output_schema": {"properties": {"sent": {"type": "boolean"}}}}
        req = {"suggested_id": "web_search", "description": "Search the web",
               "execution_type": "python",
               "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
               "output_schema": {"type": "object", "properties": {"results": {"type": "array"}}}}
        assert _is_good_match(candidate, req) is True


class TestPromptBuilders:
    def test_build_decompose_prompts_python_only(self):
        system, user = build_decompose_prompts("Find news")
        assert "block" in system.lower()
        assert "Find news" in user
        # Should NOT mention llm as an execution type option
        assert '"llm"' not in system or "legacy" in system.lower()
        # Should mention call_llm as a function available to python blocks
        assert "call_llm" in system

    def test_build_create_block_prompt_always_python(self):
        spec = {
            "suggested_id": "my_block",
            "description": "Does something",
            "execution_type": "python",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
        }
        system, user = build_create_block_prompt(spec)
        assert "my_block" in user
        assert "source_code" in system
        assert "call_llm" in system

    def test_build_create_block_prompt_no_llm_branch(self):
        """Even if spec says llm, the create prompt should produce python."""
        spec = {
            "suggested_id": "analyzer",
            "description": "Analyze data",
            "execution_type": "llm",  # legacy — should still produce python prompt
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
        }
        system, user = build_create_block_prompt(spec)
        assert "source_code" in system
        assert "python" in system.lower()

    def test_build_wire_prompts(self):
        blocks = [{
            "id": "web_search", "name": "Web Search",
            "description": "Search",
            "input_schema": {}, "output_schema": {},
        }]
        system, user = build_wire_prompts("test intent", blocks)
        assert "web_search" in system
        assert "test intent" in user


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
            execution_type="python",
            input_schema={"type": "object", "properties": {"x": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"y": {"type": "string"}}},
            source_code="async def execute(inputs, context):\n    return {'y': inputs['x']}\n",
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
                    "execution_type": "python",
                    "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}},
                    "output_schema": {"type": "object", "properties": {"posts": {"type": "array"}}},
                    "source_code": "async def execute(inputs, context):\n    return {'posts': []}\n",
                }
            ]
        }
        result = validate_stage_output("create_block", data)
        assert len(result.created_blocks) == 1
        assert result.created_blocks[0].id == "scrape_hn"
