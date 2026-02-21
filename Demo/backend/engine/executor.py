"""Block executor — two execution paths: llm and python (exec from source_code)."""

from __future__ import annotations

import json
import re
import traceback
from io import StringIO
from typing import Any

from engine.resolver import resolve_templates
from llm.service import call_llm, parse_json_output
from registry.registry import registry
from storage.supabase_client import get_supabase

# Compiled function cache: block_id → execute function
_compiled_blocks: dict[str, Any] = {}


async def execute_block(node_def: dict, state: dict) -> dict[str, Any]:
    """Execute a single block node. Returns its output dict.

    Args:
        node_def: {"id": "n1", "block_id": "web_search", "inputs": {...}}
        state: Current pipeline state with results, user, memory.

    Returns:
        The block's output dict.
    """
    block = registry.get(node_def["block_id"])

    # Trigger blocks are scheduling metadata — skip during execution
    if block.get("category") == "trigger":
        return {"status": "triggered", "trigger_type": block["id"]}

    resolved_inputs = resolve_templates(node_def.get("inputs", {}), state)
    context = {
        "user": state.get("user", {}),
        "memory": state.get("memory", {}),
        "user_id": state.get("user_id", "default_user"),
        "supabase": get_supabase(),
    }

    exec_type = block["execution_type"]
    if exec_type == "llm":
        return await run_llm_block(block, resolved_inputs, context)
    elif exec_type == "python":
        return await run_python_block(block, resolved_inputs, context)
    else:
        raise ValueError(f"Unknown execution_type: {exec_type}")


def _safe_format(template: str, values: dict) -> str:
    """Replace {key} placeholders only when key is a known input name."""
    def replacer(m):
        key = m.group(1)
        if key in values:
            return values[key]
        return m.group(0)
    return re.sub(r"\{(\w+)\}", replacer, template)


async def run_llm_block(block: dict, inputs: dict, context: dict) -> dict:
    """Execute an LLM-type block: fill prompt template, call LLM, parse JSON output."""
    schema_props = block.get("input_schema", {}).get("properties", {})
    for key, prop in schema_props.items():
        if key not in inputs and "default" in prop:
            inputs[key] = prop["default"]

    str_inputs = {}
    for k, v in inputs.items():
        str_inputs[k] = json.dumps(v) if not isinstance(v, str) else v

    prompt = _safe_format(block["prompt_template"], str_inputs)

    output_schema = block.get("output_schema", {})
    output_props = output_schema.get("properties", {})
    required_fields = output_schema.get("required", [])
    fields_desc = ", ".join(
        f'"{k}" ({v.get("type", "any")}: {v.get("description", "no description")})'
        for k, v in output_props.items()
    )
    required_note = f"Required fields: {', '.join(required_fields)}" if required_fields else ""

    examples = block.get("examples", [])
    example_note = ""
    if examples and "outputs" in examples[0]:
        example_note = f"\n6. Example output for reference: {json.dumps(examples[0]['outputs'])}"

    system = (
        f"You are executing the block: {block['name']}.\n"
        f"Task: {block['description']}\n\n"
        f"IMPORTANT RULES:\n"
        f"1. Return ONLY a JSON object (no markdown, no explanation).\n"
        f"2. The JSON must contain these fields: {fields_desc}.\n"
        f"3. Populate every field with REAL, substantive data — never return empty arrays or placeholder values.\n"
        f"4. Use your knowledge to produce the best possible answer.\n"
        f"5. If asked to search or look up information, use your training knowledge to provide real, accurate results."
        f"{example_note}"
    )
    if required_note:
        system += f"\n{required_note}"

    response = await call_llm(system=system, user=prompt)
    return parse_json_output(response, block["output_schema"])


async def run_python_block(block: dict, inputs: dict, context: dict) -> dict:
    """Execute a python block by exec()'ing its source_code.

    The source_code must define an `async def execute(inputs, context) -> dict`.
    Compiled functions are cached by block_id for performance.
    """
    block_id = block["id"]

    if block_id not in _compiled_blocks:
        source_code = block.get("source_code")
        if not source_code:
            raise ValueError(f"Python block {block_id} has no source_code")

        namespace = _build_exec_namespace()
        try:
            exec(compile(source_code, f"<block:{block_id}>", "exec"), namespace)
        except Exception:
            raise RuntimeError(
                f"Failed to compile block {block_id}:\n{traceback.format_exc()}"
            )

        if "execute" not in namespace:
            raise AttributeError(f"Block {block_id} source_code missing execute() function")

        _compiled_blocks[block_id] = namespace["execute"]

    execute_fn = _compiled_blocks[block_id]
    return await execute_fn(inputs, context)


def _build_exec_namespace() -> dict:
    """Build a safe namespace for exec() with allowed modules."""
    import builtins
    import collections
    import datetime
    import functools
    import itertools
    import math
    import os
    import re as re_mod
    import statistics

    import httpx
    import json as json_mod

    allowed_builtins = {
        "True": True, "False": False, "None": None,
        "int": int, "float": float, "str": str, "bool": bool,
        "list": list, "dict": dict, "tuple": tuple, "set": set,
        "frozenset": frozenset, "bytes": bytes,
        "abs": abs, "all": all, "any": any, "bin": bin,
        "chr": chr, "divmod": divmod, "enumerate": enumerate,
        "filter": filter, "format": format, "hash": hash, "hex": hex,
        "isinstance": isinstance, "issubclass": issubclass,
        "iter": iter, "len": len, "map": map, "max": max, "min": min,
        "next": next, "oct": oct, "ord": ord, "pow": pow,
        "range": range, "repr": repr, "reversed": reversed,
        "round": round, "slice": slice, "sorted": sorted,
        "sum": sum, "type": type, "zip": zip,
        "hasattr": hasattr, "getattr": getattr, "setattr": setattr,
        "print": print,
        "Exception": Exception, "ValueError": ValueError,
        "TypeError": TypeError, "KeyError": KeyError,
        "RuntimeError": RuntimeError, "AttributeError": AttributeError,
    }

    return {
        "__builtins__": allowed_builtins,
        # Safe modules
        "math": math,
        "statistics": statistics,
        "collections": collections,
        "itertools": itertools,
        "functools": functools,
        "re": re_mod,
        "datetime": datetime,
        "json": json_mod,
        "os": os,  # needed for os.environ (API keys)
        "httpx": httpx,
    }
