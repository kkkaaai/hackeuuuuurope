"""Block executor — dispatches blocks by execution_type."""

import importlib.util
import json
import re
import traceback
from io import StringIO
from pathlib import Path
from typing import Any

from engine.resolver import resolve_templates
from llm.service import call_llm, parse_json_output
from registry.registry import registry


def _import_block(entrypoint: str):
    """Dynamically import a Python block module from its entrypoint path.

    Args:
        entrypoint: Relative path like "blocks/filter_threshold/main.py"

    Returns:
        Module with an async execute(inputs, context) function.
    """
    base_dir = Path(__file__).resolve().parent.parent
    full_path = base_dir / entrypoint

    if not full_path.exists():
        raise FileNotFoundError(f"Block entrypoint not found: {full_path}")

    # Use the full relative path as module name to avoid cache collisions
    # e.g. "blocks.filter_threshold.main" instead of just "blocks.main"
    rel_parts = full_path.relative_to(base_dir / "blocks").with_suffix("").parts
    module_name = "blocks." + ".".join(rel_parts)

    spec = importlib.util.spec_from_file_location(
        module_name,
        str(full_path),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "execute"):
        raise AttributeError(f"Block module {entrypoint} missing execute() function")

    return module


async def execute_block(node_def: dict, state: dict) -> dict[str, Any]:
    """Execute a single block node. Returns its output dict.

    Args:
        node_def: {"id": "n1", "block_id": "web_search", "inputs": {...}}
        state: Current pipeline state with results, user, memory.

    Returns:
        The block's output dict (e.g. {"results": [...]} or {"summary": "..."}).
    """
    block = registry.get(node_def["block_id"])

    # Trigger blocks are scheduling metadata — skip during execution
    if block.get("category") == "trigger":
        return {"status": "triggered", "trigger_type": block["id"]}

    resolved_inputs = resolve_templates(node_def.get("inputs", {}), state)
    context = {"user": state.get("user", {}), "memory": state.get("memory", {})}

    match block["execution_type"]:
        case "llm":
            return await run_llm_block(block, resolved_inputs, context)
        case "code":
            return await run_code_block(block, resolved_inputs, context)
        case "python":
            module = _import_block(block["execution"]["entrypoint"])
            return await module.execute(resolved_inputs, context)
        case "mcp":
            raise NotImplementedError("MCP blocks — implement when needed")
        case "browser":
            raise NotImplementedError("Browser blocks — implement when needed")
        case _:
            raise ValueError(f"Unknown execution_type: {block['execution_type']}")


def _safe_format(template: str, values: dict) -> str:
    """Replace {key} placeholders only when key is a known input name.

    Unlike str.format(), this won't choke on nested braces or
    ICU MessageFormat syntax that LLMs sometimes generate.
    """
    def replacer(m):
        key = m.group(1)
        if key in values:
            return values[key]
        return m.group(0)  # leave unrecognised placeholders as-is

    return re.sub(r"\{(\w+)\}", replacer, template)


async def run_llm_block(block: dict, inputs: dict, context: dict) -> dict:
    """Execute an LLM-type block: fill prompt template, call LLM, parse JSON output."""
    # Fill defaults from input_schema
    schema_props = block.get("input_schema", {}).get("properties", {})
    for key, prop in schema_props.items():
        if key not in inputs and "default" in prop:
            inputs[key] = prop["default"]

    # Serialize non-string inputs so they can be interpolated into the prompt
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

    # Include one example output if available
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


async def run_code_block(block: dict, inputs: dict, context: dict) -> dict:
    """Execute a code-type block: run LLM-generated Python code with inputs injected.

    The block must have a 'code_template' field containing Python source code.
    The code receives all inputs as local variables and must set a 'result' dict.

    If no code_template exists, we ask the LLM to generate code on the fly,
    then execute it.
    """
    code = block.get("code_template")

    if not code:
        # Ask LLM to generate code for this block
        code = await _generate_code(block, inputs)

    # Build the execution namespace with inputs + safe builtins
    namespace = {
        "inputs": inputs,
        "json": json,
        "result": {},
        **inputs,  # spread inputs as top-level variables
    }

    # Capture stdout
    stdout_capture = StringIO()
    namespace["print"] = lambda *args, **kwargs: print(*args, file=stdout_capture, **kwargs)

    try:
        exec(code, {"__builtins__": _safe_builtins()}, namespace)
    except Exception:
        return {
            "error": traceback.format_exc(),
            "stdout": stdout_capture.getvalue(),
            "code": code,
        }

    output = namespace.get("result", {})
    if stdout_capture.getvalue():
        output["_stdout"] = stdout_capture.getvalue()
    output["_code"] = code

    return output


async def _generate_code(block: dict, inputs: dict) -> str:
    """Ask the LLM to write Python code for a code block."""
    input_desc = json.dumps(inputs, indent=2, default=str)
    output_props = block.get("output_schema", {}).get("properties", {})
    output_desc = json.dumps(output_props, indent=2)

    system = (
        "You are a Python code generator. Write Python code that processes inputs and produces outputs.\n\n"
        "RULES:\n"
        "1. Return ONLY Python code — no markdown, no explanation, no ```python fences.\n"
        "2. All input values are available as local variables (and also in an 'inputs' dict).\n"
        "3. Store your output in a dict called 'result'.\n"
        "4. You can use: json, math, statistics, collections, itertools, functools, re, datetime.\n"
        "5. You CANNOT use: os, sys, subprocess, importlib, open, eval, exec, __import__.\n"
        "6. Keep the code simple, correct, and focused on the task."
    )

    user = (
        f"Block: {block['name']}\n"
        f"Description: {block['description']}\n\n"
        f"Input values:\n{input_desc}\n\n"
        f"Required output fields:\n{output_desc}\n\n"
        f"Write Python code that reads from the input variables and sets result = {{...}} "
        f"with the required output fields populated."
    )

    response = await call_llm(system=system, user=user)

    # Strip markdown fences if the LLM added them
    code = response.strip()
    if code.startswith("```python"):
        code = code[len("```python"):].strip()
    if code.startswith("```"):
        code = code[3:].strip()
    if code.endswith("```"):
        code = code[:-3].strip()

    return code


def _safe_builtins() -> dict:
    """Return a restricted set of builtins safe for code execution."""
    import builtins
    import collections
    import datetime
    import functools
    import itertools
    import math
    import re
    import statistics

    allowed = {
        # Types and constructors
        "True": True, "False": False, "None": None,
        "int": int, "float": float, "str": str, "bool": bool,
        "list": list, "dict": dict, "tuple": tuple, "set": set,
        "frozenset": frozenset, "bytes": bytes,
        # Built-in functions
        "abs": abs, "all": all, "any": any, "bin": bin,
        "chr": chr, "divmod": divmod, "enumerate": enumerate,
        "filter": filter, "format": format, "hash": hash, "hex": hex,
        "isinstance": isinstance, "issubclass": issubclass,
        "iter": iter, "len": len, "map": map, "max": max, "min": min,
        "next": next, "oct": oct, "ord": ord, "pow": pow,
        "range": range, "repr": repr, "reversed": reversed,
        "round": round, "slice": slice, "sorted": sorted,
        "sum": sum, "type": type, "zip": zip,
        # String methods via str
        "hasattr": hasattr, "getattr": getattr,
        # Safe modules
        "math": math,
        "statistics": statistics,
        "collections": collections,
        "itertools": itertools,
        "functools": functools,
        "re": re,
        "datetime": datetime,
        "json": json,
    }
    return allowed
