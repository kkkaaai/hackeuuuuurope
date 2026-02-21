"""Tests for the block executor."""

import pytest
from unittest.mock import AsyncMock, patch

from engine.executor import execute_block, run_python_block, _convert_legacy_llm_block


class TestExecuteBlock:
    @pytest.mark.asyncio
    async def test_python_block_dispatch(self):
        """Python block runs via registry and returns correct output."""
        block = {
            "id": "test_add",
            "execution_type": "python",
            "input_schema": {"properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
            "output_schema": {"properties": {"sum": {"type": "number"}}},
            "source_code": "async def execute(inputs, context):\n    return {'sum': inputs['a'] + inputs['b']}\n",
        }
        with patch("engine.executor.registry") as mock_reg:
            mock_reg.get.return_value = block
            node_def = {"id": "n1", "block_id": "test_add", "inputs": {"a": 3, "b": 4}}
            state = {"results": {}, "user": {}, "memory": {}}
            result = await execute_block(node_def, state)
        assert result["sum"] == 7

    @pytest.mark.asyncio
    async def test_legacy_llm_block_auto_converted(self):
        """Legacy llm blocks are auto-converted to python and still execute."""
        block = {
            "id": "legacy_summarize",
            "execution_type": "llm",
            "name": "Summarize",
            "description": "Summarize text",
            "prompt_template": "Summarize: {content}",
            "input_schema": {"properties": {"content": {"type": "string"}}},
            "output_schema": {"properties": {"summary": {"type": "string"}}, "required": ["summary"]},
            "examples": [],
        }
        with patch("engine.executor.registry") as mock_reg:
            mock_reg.get.return_value = block
            with patch("engine.executor.call_llm", new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = '{"summary": "Short version"}'
                node_def = {"id": "n1", "block_id": "legacy_summarize", "inputs": {"content": "Long text"}}
                state = {"results": {}, "user": {}, "memory": {}}
                result = await execute_block(node_def, state)

        mock_llm.assert_called_once()
        assert result["summary"] == "Short version"

    @pytest.mark.asyncio
    async def test_trigger_block_skipped(self):
        block = {"id": "daily_trigger", "category": "trigger", "execution_type": "python"}
        with patch("engine.executor.registry") as mock_reg:
            mock_reg.get.return_value = block
            node_def = {"id": "n1", "block_id": "daily_trigger", "inputs": {}}
            state = {"results": {}, "user": {}, "memory": {}}
            result = await execute_block(node_def, state)
        assert result["status"] == "triggered"


class TestRunPythonBlock:
    @pytest.mark.asyncio
    async def test_python_block_with_llm_access(self):
        """Python blocks can call call_llm() from their source code."""
        block = {
            "id": "test_llm_python",
            "execution_type": "python",
            "input_schema": {"properties": {"text": {"type": "string"}}},
            "output_schema": {"properties": {"result": {"type": "string"}}},
            "source_code": (
                "async def execute(inputs, context):\n"
                "    resp = await call_llm(system='Echo', user=inputs['text'])\n"
                "    return {'result': resp}\n"
            ),
        }
        with patch("engine.executor.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "echoed"
            result = await run_python_block(block, {"text": "hello"}, {})
        assert result["result"] == "echoed"
        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_source_code_raises(self):
        block = {"id": "empty", "execution_type": "python"}
        with pytest.raises(ValueError, match="has no source_code"):
            await run_python_block(block, {}, {})

    @pytest.mark.asyncio
    async def test_missing_execute_function_raises(self):
        block = {
            "id": "no_execute",
            "execution_type": "python",
            "source_code": "x = 1\n",
        }
        with pytest.raises(AttributeError, match="missing execute"):
            await run_python_block(block, {}, {})


class TestConvertLegacyLlmBlock:
    def test_converts_execution_type(self):
        block = {
            "id": "old_block",
            "execution_type": "llm",
            "name": "Old",
            "description": "Old block",
            "prompt_template": "Do {x}",
            "input_schema": {"properties": {"x": {"type": "string"}}},
            "output_schema": {"properties": {"y": {"type": "string"}}, "required": ["y"]},
            "examples": [],
        }
        converted = _convert_legacy_llm_block(block)
        assert converted["execution_type"] == "python"
        assert "source_code" in converted
        assert "async def execute" in converted["source_code"]

    def test_original_block_unchanged(self):
        block = {
            "id": "old",
            "execution_type": "llm",
            "name": "Old",
            "description": "",
            "prompt_template": "Do {x}",
            "input_schema": {"properties": {}},
            "output_schema": {"properties": {}},
            "examples": [],
        }
        _convert_legacy_llm_block(block)
        assert block["execution_type"] == "llm"  # original not mutated
