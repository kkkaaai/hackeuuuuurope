"""Tests for the block executor."""

import pytest
from unittest.mock import AsyncMock, patch

from engine.executor import execute_block, run_llm_block, _import_block


class TestImportBlock:
    def test_import_real_block(self):
        module = _import_block("blocks/filter_threshold/main.py")
        assert hasattr(module, "execute")
        assert callable(module.execute)

    def test_import_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            _import_block("blocks/nonexistent/main.py")


class TestExecuteBlock:
    @pytest.mark.asyncio
    async def test_python_block_dispatch(self):
        """Python block (filter_threshold) runs and returns correct output."""
        node_def = {
            "id": "n1",
            "block_id": "filter_threshold",
            "inputs": {"value": 42, "operator": ">", "threshold": 10},
        }
        state = {"results": {}, "user": {}, "memory": {}}
        result = await execute_block(node_def, state)
        assert result["passed"] is True
        assert result["value"] == 42.0

    @pytest.mark.asyncio
    async def test_python_block_false_result(self):
        node_def = {
            "id": "n1",
            "block_id": "filter_threshold",
            "inputs": {"value": 5, "operator": ">", "threshold": 10},
        }
        state = {"results": {}, "user": {}, "memory": {}}
        result = await execute_block(node_def, state)
        assert result["passed"] is False

    @pytest.mark.asyncio
    async def test_notify_push_block(self):
        node_def = {
            "id": "n1",
            "block_id": "notify_push",
            "inputs": {"title": "Test", "body": "Hello"},
        }
        state = {"results": {}, "user": {}, "memory": {}}
        result = await execute_block(node_def, state)
        assert result["delivered"] is True

    @pytest.mark.asyncio
    async def test_conditional_branch_block(self):
        node_def = {
            "id": "n1",
            "block_id": "conditional_branch",
            "inputs": {"condition": True, "data": "payload"},
        }
        state = {"results": {}, "user": {}, "memory": {}}
        result = await execute_block(node_def, state)
        assert result["branch"] == "yes"
        assert result["data"] == "payload"

    @pytest.mark.asyncio
    async def test_unknown_execution_type_raises(self):
        with patch("engine.executor.registry") as mock_reg:
            mock_reg.get.return_value = {
                "id": "fake",
                "execution_type": "quantum",
            }
            node_def = {"id": "n1", "block_id": "fake", "inputs": {}}
            state = {"results": {}, "user": {}, "memory": {}}
            with pytest.raises(ValueError, match="Unknown execution_type"):
                await execute_block(node_def, state)


class TestRunLlmBlock:
    @pytest.mark.asyncio
    async def test_llm_block_calls_llm(self):
        block = {
            "name": "Test Block",
            "description": "A test",
            "prompt_template": "Do {thing}",
            "input_schema": {
                "properties": {"thing": {"type": "string"}},
            },
            "output_schema": {"type": "object", "properties": {"result": {"type": "string"}}},
        }
        with patch("engine.executor.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = '{"result": "done"}'
            with patch("engine.executor.parse_json_output") as mock_parse:
                mock_parse.return_value = {"result": "done"}
                result = await run_llm_block(block, {"thing": "test"}, {})

        mock_llm.assert_called_once()
        assert result == {"result": "done"}
