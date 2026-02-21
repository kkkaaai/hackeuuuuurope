"""Builder Agent — creates new block definitions and implementations on-the-fly."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic

from app.blocks.executor import register_implementation
from app.blocks.registry import BlockRegistry
from app.config import settings
from app.models.block import BlockDefinition

logger = logging.getLogger("agentflow.builder")

SYSTEM_PROMPT = """You are the Builder Agent for AgentFlow — an automation platform.

Your job: given a block specification, generate a new block definition with working Python code.

## Block Specification Format (input you receive)
{{
  "suggested_id": "unique_snake_case_id",
  "name": "Human Readable Name",
  "description": "What this block does",
  "category": "perceive|think|act|communicate|remember|control",
  "input_schema": {{ JSON Schema for inputs }},
  "output_schema": {{ JSON Schema for outputs }}
}}

## Output Format

Respond with ONLY valid JSON (no markdown, no code fences, just raw JSON):

{{
  "block_definition": {{
    "id": "the_block_id",
    "name": "Human Name",
    "description": "What it does",
    "category": "category",
    "organ": "system|web|claude|gemini|stripe|elevenlabs|miro|email",
    "input_schema": {{ ... }},
    "output_schema": {{ ... }},
    "api_type": "real|mock",
    "tier": 2,
    "examples": [{{ "input": {{}}, "output": {{}} }}]
  }},
  "implementation_code": "async def block_fn(inputs: dict) -> dict:\\n    # Python code here\\n    return {{}}"
}}

## Rules

1. The implementation_code must be an async function that takes a dict and returns a dict.
2. You can use these imports: httpx, json, re, datetime, bs4.BeautifulSoup
3. The function must handle errors gracefully — return error info instead of raising.
4. Keep implementations simple and focused.
5. If you can't make a real implementation, set api_type to "mock" and return realistic fake data.
6. The function name should match the block_id.
"""


class BuilderAgent:
    def __init__(self, registry: BlockRegistry):
        self.registry = registry

    async def create_block(self, spec: dict[str, Any]) -> BlockDefinition:
        """Create a new block from a specification.

        Returns the registered BlockDefinition.
        """
        if not settings.anthropic_api_key:
            logger.warning("No ANTHROPIC_API_KEY — creating mock block")
            return self._mock_create(spec)

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(spec, indent=2)}],
        )

        response_text = message.content[0].text.strip()

        # Strip markdown code fences if present
        md_match = re.search(r"```(?:json)?\s*\n?(.*?)```", response_text, re.DOTALL)
        if md_match:
            response_text = md_match.group(1).strip()

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            logger.error("Builder returned invalid JSON: %s", response_text[:200])
            logger.warning("Falling back to mock block creation")
            return self._mock_create(spec)

        block_data = result["block_definition"]
        block = BlockDefinition(**block_data)

        # Register the mock implementation
        impl_code = result.get("implementation_code", "")
        self._register_dynamic_implementation(block.id, impl_code)

        # Add to registry
        self.registry.register(block)
        logger.info("Builder created block: %s", block.id)
        return block

    async def create_missing_blocks(self, missing_specs: list[dict[str, Any]]) -> list[BlockDefinition]:
        """Create all missing blocks from a list of specs."""
        created = []
        for spec in missing_specs:
            block = await self.create_block(spec)
            created.append(block)
        return created

    def _register_dynamic_implementation(self, block_id: str, code: str) -> None:
        """Register a dynamically generated block implementation.

        For safety, we create a mock implementation that returns
        the example output from the block definition rather than
        executing arbitrary generated code.
        """
        # Safe approach: create a mock that returns realistic data
        async def mock_impl(inputs: dict[str, Any]) -> dict[str, Any]:
            logger.info("Executing dynamic block %s (mock mode)", block_id)
            return {
                "result": f"Mock output from dynamic block '{block_id}'",
                "inputs_received": inputs,
                "status": "mock",
            }

        register_implementation(block_id)(mock_impl)

    def _mock_create(self, spec: dict[str, Any]) -> BlockDefinition:
        """Create a block without calling the API."""
        block_id = spec.get("suggested_id", f"custom_{spec.get('name', 'block').lower().replace(' ', '_')}")
        block = BlockDefinition(
            id=block_id,
            name=spec.get("name", "Custom Block"),
            description=spec.get("description", "A dynamically created block"),
            category=spec.get("category", "perceive"),
            organ="system",
            input_schema=spec.get("input_schema", {}),
            output_schema=spec.get("output_schema", {}),
            api_type="mock",
            tier=2,
            examples=[{"input": {}, "output": {"result": "mock"}}],
        )

        self._register_dynamic_implementation(block.id, "")
        self.registry.register(block)
        logger.info("Builder created mock block: %s", block.id)
        return block
