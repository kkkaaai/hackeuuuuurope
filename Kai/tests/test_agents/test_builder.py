"""Tests for the Builder Agent."""

import pytest

from app.agents.builder import BuilderAgent
from app.blocks.executor import get_implementation
from app.blocks.registry import BlockRegistry


@pytest.fixture()
def registry():
    reg = BlockRegistry()
    reg.load_from_directory()
    return reg


@pytest.fixture()
def builder(registry):
    return BuilderAgent(registry)


class TestBuilderCreateBlock:
    @pytest.mark.asyncio
    async def test_create_mock_block(self, builder, registry):
        """Builder should create and register a new block from a spec."""
        initial_count = registry.count

        spec = {
            "suggested_id": "flight_search",
            "name": "Flight Search",
            "description": "Search for flights between two cities on a given date",
            "category": "perceive",
            "input_schema": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string"},
                    "destination": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["origin", "destination", "date"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "flights": {"type": "array"},
                    "cheapest_price": {"type": "number"},
                },
            },
        }

        block = await builder.create_block(spec)

        assert block.id == "flight_search"
        assert block.name == "Flight Search"
        assert block.category == "perceive"
        assert block.api_type == "mock"
        assert registry.count == initial_count + 1
        assert registry.get("flight_search") is not None

    @pytest.mark.asyncio
    async def test_created_block_has_implementation(self, builder):
        """Created block should have a registered implementation."""
        spec = {
            "suggested_id": "test_dynamic_block",
            "name": "Test Dynamic",
            "description": "A test block",
            "category": "think",
        }
        await builder.create_block(spec)

        impl = get_implementation("test_dynamic_block")
        assert impl is not None

    @pytest.mark.asyncio
    async def test_created_block_implementation_runs(self, builder):
        """The mock implementation should execute and return data."""
        spec = {
            "suggested_id": "test_runnable_block",
            "name": "Test Runnable",
            "description": "Should be executable",
            "category": "act",
        }
        await builder.create_block(spec)

        impl = get_implementation("test_runnable_block")
        result = await impl({"some_input": "value"})
        assert "result" in result
        assert result["status"] == "mock"

    @pytest.mark.asyncio
    async def test_create_multiple_missing_blocks(self, builder, registry):
        """create_missing_blocks should create all blocks in the list."""
        specs = [
            {
                "suggested_id": "block_a",
                "name": "Block A",
                "description": "First block",
                "category": "perceive",
            },
            {
                "suggested_id": "block_b",
                "name": "Block B",
                "description": "Second block",
                "category": "act",
            },
        ]

        created = await builder.create_missing_blocks(specs)
        assert len(created) == 2
        assert registry.get("block_a") is not None
        assert registry.get("block_b") is not None
