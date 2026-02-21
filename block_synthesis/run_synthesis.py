#!/usr/bin/env python
"""
Block Synthesis Runner

Takes a block specification prompt and synthesizes working code using
Docker-sandboxed execution with iterative LLM repair.

Usage:
    python -m block_synthesis.run_synthesis --prompt "path/to/prompt.txt"
    python -m block_synthesis.run_synthesis --prompt-text "Inputs: ..."
    
Or import and use programmatically:
    from block_synthesis.run_synthesis import synthesize_from_prompt
    code = await synthesize_from_prompt(prompt_text)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .synthesizer import (
    BlockRequest,
    BlockSynthesizer,
    BlockValidator,
    ExecutionResult,
    MaxIterationsError,
    Orchestrator,
    OutputFormat,
    SandboxManager,
    SynthesisResult,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class ParsedPrompt:
    """Parsed block specification from prompt text."""
    inputs: list[dict[str, str]]
    outputs: list[dict[str, str]]
    purpose: str
    test_input: Any | None = None
    expected_output: Any | None = None


def parse_block_prompt(prompt_text: str) -> ParsedPrompt:
    """Parse a block specification prompt into structured data.
    
    Expected format:
        Inputs:
        - name (type: description): explanation
        
        Outputs:
        - name (type: description): explanation
        
        Purpose:
        Description of what the block should do.
        
        Test Input (optional):
        JSON or description
        
        Expected Output (optional):
        JSON or description
    """
    lines = prompt_text.strip().split("\n")
    
    inputs = []
    outputs = []
    purpose = ""
    test_input = None
    expected_output = None
    
    current_section = None
    section_content = []
    
    def parse_io_line(line: str) -> dict[str, str] | None:
        match = re.match(r"^-\s*(\w+)\s*(?:\(([^)]+)\))?:?\s*(.*)$", line.strip())
        if match:
            name = match.group(1)
            type_info = match.group(2) or ""
            description = match.group(3) or ""
            
            type_match = re.match(r"type:\s*(.+)", type_info)
            actual_type = type_match.group(1) if type_match else type_info
            
            return {
                "name": name,
                "type": actual_type.strip(),
                "description": description.strip(),
            }
        return None
    
    for line in lines:
        line_lower = line.lower().strip()
        
        if line_lower.startswith("inputs:"):
            current_section = "inputs"
            section_content = []
        elif line_lower.startswith("outputs:"):
            current_section = "outputs"
            section_content = []
        elif line_lower.startswith("purpose:"):
            current_section = "purpose"
            section_content = []
            remainder = line.split(":", 1)
            if len(remainder) > 1 and remainder[1].strip():
                section_content.append(remainder[1].strip())
        elif line_lower.startswith("test input:") or line_lower.startswith("test_input:"):
            current_section = "test_input"
            section_content = []
        elif line_lower.startswith("expected output:") or line_lower.startswith("expected_output:"):
            current_section = "expected_output"
            section_content = []
        elif current_section:
            if current_section == "inputs":
                parsed = parse_io_line(line)
                if parsed:
                    inputs.append(parsed)
            elif current_section == "outputs":
                parsed = parse_io_line(line)
                if parsed:
                    outputs.append(parsed)
            elif current_section in ("purpose", "test_input", "expected_output"):
                if line.strip():
                    section_content.append(line.strip())
    
        if current_section == "purpose" and section_content:
            purpose = " ".join(section_content)
    
    purpose = " ".join(section_content) if current_section == "purpose" else purpose
    
    for line in lines:
        if line.lower().strip().startswith("purpose:"):
            idx = lines.index(line)
            purpose_lines = []
            for l in lines[idx:]:
                if l.lower().strip().startswith(("test input:", "test_input:", "expected output:", "expected_output:")):
                    break
                if l.lower().strip().startswith("purpose:"):
                    remainder = l.split(":", 1)
                    if len(remainder) > 1 and remainder[1].strip():
                        purpose_lines.append(remainder[1].strip())
                elif l.strip() and not l.strip().startswith("-"):
                    purpose_lines.append(l.strip())
            purpose = " ".join(purpose_lines)
            break
    
    return ParsedPrompt(
        inputs=inputs,
        outputs=outputs,
        purpose=purpose,
        test_input=test_input,
        expected_output=expected_output,
    )


def generate_test_case(parsed: ParsedPrompt) -> tuple[Any, Any]:
    """Generate a synthetic test case based on input/output types.
    
    For image processing, we create minimal test data.
    """
    test_input = {}
    expected_output = {}
    
    for inp in parsed.inputs:
        inp_type = inp.get("type", "").lower()
        inp_name = inp["name"]
        
        if "image" in inp_type or "png" in inp_type or "jpg" in inp_type:
            test_input[inp_name] = "base64_encoded_image_placeholder"
        elif "json" in inp_type:
            test_input[inp_name] = {}
        elif "list" in inp_type or "array" in inp_type:
            test_input[inp_name] = []
        elif "number" in inp_type or "int" in inp_type or "float" in inp_type:
            test_input[inp_name] = 0
        elif "string" in inp_type or "text" in inp_type:
            test_input[inp_name] = "test_string"
        else:
            test_input[inp_name] = "test_value"
    
    for out in parsed.outputs:
        out_type = out.get("type", "").lower()
        out_name = out["name"]
        
        if "image" in out_type or "binary" in out_type or "mask" in out_type:
            expected_output[out_name] = "base64_encoded_output_placeholder"
        elif "json" in out_type:
            expected_output[out_name] = {}
        elif "list" in out_type or "array" in out_type:
            expected_output[out_name] = []
        elif "number" in out_type or "int" in out_type or "float" in out_type:
            expected_output[out_name] = 0
        elif "string" in out_type or "text" in out_type:
            expected_output[out_name] = "output_string"
        elif "bool" in out_type:
            expected_output[out_name] = True
        else:
            expected_output[out_name] = "output_value"
    
    return test_input, expected_output


async def synthesize_from_prompt(
    prompt_text: str,
    prompt_file: str | Path | None = None,
    provider: str = "openai",
    model: str = "gpt-4o",
    max_iterations: int = 6,
    output_file: str | Path | None = None,
) -> str:
    """Synthesize a block from a natural language prompt.
    
    Args:
        prompt_text: The block specification prompt
        prompt_file: Path to master prompt file (optional, uses default)
        provider: LLM provider (openai or anthropic)
        model: Model name
        max_iterations: Maximum repair attempts
        output_file: Path to save the generated code (optional)
        
    Returns:
        The synthesized Python code
    """
    parsed = parse_block_prompt(prompt_text)
    
    logger.info("Parsed prompt:")
    logger.info("  Inputs: %s", [i["name"] for i in parsed.inputs])
    logger.info("  Outputs: %s", [o["name"] for o in parsed.outputs])
    logger.info("  Purpose: %s", parsed.purpose[:100])
    
    test_input, expected_output = generate_test_case(parsed)
    logger.info("Generated test case:")
    logger.info("  Input: %s", json.dumps(test_input, indent=2)[:200])
    logger.info("  Expected: %s", json.dumps(expected_output, indent=2)[:200])
    
    input_names = [i["name"] for i in parsed.inputs]
    output_names = [o["name"] for o in parsed.outputs]
    
    full_purpose = parsed.purpose
    if parsed.inputs:
        full_purpose += "\n\nInput specifications:"
        for inp in parsed.inputs:
            full_purpose += f"\n- {inp['name']} ({inp.get('type', 'any')}): {inp.get('description', '')}"
    if parsed.outputs:
        full_purpose += "\n\nOutput specifications:"
        for out in parsed.outputs:
            full_purpose += f"\n- {out['name']} ({out.get('type', 'any')}): {out.get('description', '')}"
    
    request = BlockRequest(
        inputs=input_names,
        outputs=output_names,
        purpose=full_purpose,
        test_input=test_input,
        expected_output=expected_output,
    )
    
    master_prompt = prompt_file or Path(__file__).parent / "prompts" / "master_prompt.txt"
    
    synthesizer = BlockSynthesizer(
        prompt_file=master_prompt,
        provider=provider,
        model=model,
    )
    
    sandbox = SandboxManager(
        backend="docker",
        image="block-sandbox",
        allow_pip_install=True,
    )
    
    validator = BlockValidator()
    
    orchestrator = Orchestrator(
        synthesizer=synthesizer,
        sandbox=sandbox,
        validator=validator,
        max_iterations=max_iterations,
    )
    
    logger.info("Starting synthesis with Docker sandbox...")
    logger.info("Max iterations: %d", max_iterations)
    
    try:
        code = await orchestrator.run(request)
        logger.info("Synthesis successful!")
        
        if output_file:
            output_path = Path(output_file)
            output_path.write_text(code, encoding="utf-8")
            logger.info("Saved to: %s", output_path)
        
        return code
        
    except MaxIterationsError as e:
        logger.error("Synthesis failed after %d iterations: %s", max_iterations, e)
        raise
    except Exception as e:
        logger.error("Synthesis failed: %s", e)
        raise


async def main():
    parser = argparse.ArgumentParser(
        description="Synthesize a Python block from a natural language prompt"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Path to a file containing the block prompt",
    )
    parser.add_argument(
        "--prompt-text",
        type=str,
        help="Block prompt text directly",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path for the generated code",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="openai",
        choices=["openai", "anthropic"],
        help="LLM provider (default: openai)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o",
        help="Model name (default: gpt-4o)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=6,
        help="Maximum repair iterations (default: 6)",
    )
    parser.add_argument(
        "--master-prompt",
        type=str,
        help="Path to custom master prompt file",
    )
    
    args = parser.parse_args()
    
    if args.prompt:
        prompt_text = Path(args.prompt).read_text(encoding="utf-8")
    elif args.prompt_text:
        prompt_text = args.prompt_text
    else:
        print("Reading prompt from stdin...")
        prompt_text = sys.stdin.read()
    
    if not prompt_text.strip():
        print("Error: No prompt provided", file=sys.stderr)
        sys.exit(1)
    
    try:
        code = await synthesize_from_prompt(
            prompt_text=prompt_text,
            prompt_file=args.master_prompt,
            provider=args.provider,
            model=args.model,
            max_iterations=args.max_iterations,
            output_file=args.output,
        )
        
        print("\n" + "=" * 60)
        print("GENERATED BLOCK CODE:")
        print("=" * 60)
        print(code)
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
