from __future__ import annotations

import json as _json
import logging
import re
import time
from typing import Any, Callable, Coroutine

from app.models.block import BlockDefinition
from app.models.execution import ExecutionStatus, NodeResult

logger = logging.getLogger("agentflow.executor")

# Registry of block implementation functions: block_id -> async callable
_implementations: dict[str, Callable[..., Coroutine[Any, Any, dict[str, Any]]]] = {}


def register_implementation(block_id: str):
    """Decorator to register a block implementation function."""

    def decorator(fn: Callable[..., Coroutine[Any, Any, dict[str, Any]]]):
        _implementations[block_id] = fn
        return fn

    return decorator


def get_implementation(block_id: str) -> Callable | None:
    return _implementations.get(block_id)


def resolve_templates(
    inputs: dict[str, Any],
    shared_context: dict[str, Any],
    memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve template variables like {{node_id.field}} and {{memory.key}}."""
    memory = memory or {}
    resolved = {}
    for key, value in inputs.items():
        if isinstance(value, str):
            resolved[key] = _resolve_string(value, shared_context, memory)
        else:
            resolved[key] = value
    return resolved


def _resolve_string(
    template: str,
    shared_context: dict[str, Any],
    memory: dict[str, Any],
) -> Any:
    """Resolve template variables. Supports both {{x.y}} and {x.y} formats."""
    # Match both double-brace {{x.y}} and single-brace {x.y} templates
    pattern = r"\{{1,2}(\w+)\.(\w+)\}{1,2}"

    # If the entire string is one template, return the raw value (preserves type)
    full_match = re.fullmatch(pattern, template.strip())
    if full_match:
        source, field = full_match.group(1), full_match.group(2)
        return _lookup(source, field, shared_context, memory)

    # Otherwise do string interpolation
    def replacer(match: re.Match) -> str:
        source, field = match.group(1), match.group(2)
        val = _lookup(source, field, shared_context, memory)
        return str(val) if val is not None else ""

    return re.sub(pattern, replacer, template)


def _lookup(
    source: str,
    field: str,
    shared_context: dict[str, Any],
    memory: dict[str, Any],
) -> Any:
    if source == "memory":
        return memory.get(field)
    # source is a node_id — look up in shared_context
    node_data = shared_context.get(source, {})
    if isinstance(node_data, dict):
        return node_data.get(field)
    return None


def coerce_inputs(
    inputs: dict[str, Any],
    input_schema: dict[str, Any],
) -> dict[str, Any]:
    """Coerce input values to match the block's expected types.

    Handles common LLM output mismatches: "5" → 5, "true" → True, etc.
    """
    props = input_schema.get("properties", {})
    coerced = dict(inputs)
    for field, value in coerced.items():
        if value is None:
            continue
        schema = props.get(field, {})
        expected = schema.get("type")
        if not expected:
            continue
        try:
            coerced[field] = _coerce_value(value, expected)
        except ValueError:
            pass  # Keep original value; let the block handle or raise
        except TypeError as e:
            logger.warning("Type coercion failed for field '%s': %s", field, e)
    return coerced


def _coerce_value(value: Any, expected_type: str) -> Any:
    """Coerce a single value to the expected JSON schema type."""
    if expected_type == "integer":
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, float) and value == int(value):
            return int(value)
        if isinstance(value, str):
            return int(value)
    elif expected_type == "number":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            return float(value)
    elif expected_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
    elif expected_type == "string":
        if isinstance(value, str):
            return value
        if isinstance(value, (list, dict)):
            return _json.dumps(value)
        return str(value)
    elif expected_type == "array":
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = _json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except (ValueError, TypeError):
                pass
        return [value]
    elif expected_type == "object":
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = _json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except (ValueError, TypeError):
                pass
            raise TypeError(
                f"Expected a JSON object but got a plain string: {repr(value)[:120]}"
            )
    return value


class BlockExecutor:
    """Executes a single block given its definition and resolved inputs."""

    async def execute(
        self,
        block: BlockDefinition,
        inputs: dict[str, Any],
        shared_context: dict[str, Any] | None = None,
        memory: dict[str, Any] | None = None,
        node_id: str = "",
    ) -> NodeResult:
        shared_context = shared_context or {}
        memory = memory or {}
        start = time.time()

        # Resolve template variables in inputs
        resolved_inputs = resolve_templates(inputs, shared_context, memory)

        # Coerce types to match the block's input schema
        resolved_inputs = coerce_inputs(resolved_inputs, block.input_schema)

        impl = get_implementation(block.id)
        if impl is None:
            return NodeResult(
                node_id=node_id,
                block_id=block.id,
                status=ExecutionStatus.FAILED,
                error=f"No implementation registered for block '{block.id}'",
                duration_ms=(time.time() - start) * 1000,
            )

        try:
            output = await impl(resolved_inputs)
            duration = (time.time() - start) * 1000
            logger.info("Block %s executed in %.1fms", block.id, duration)
            return NodeResult(
                node_id=node_id,
                block_id=block.id,
                status=ExecutionStatus.COMPLETED,
                output=output,
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error("Block %s failed: %s", block.id, e)
            return NodeResult(
                node_id=node_id,
                block_id=block.id,
                status=ExecutionStatus.FAILED,
                error=str(e),
                duration_ms=duration,
            )
