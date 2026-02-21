#!/usr/bin/env python
"""
Standalone script to synthesize a Python block from a natural language prompt.

Usage:
    python synthesize_block.py --prompt "path/to/prompt.txt"
    python synthesize_block.py --prompt-text "Inputs: ..."
    
    # Or pipe directly:
    echo "Inputs: ..." | python synthesize_block.py
    
Examples:
    python synthesize_block.py --prompt block_synthesis/prompts/sample_segmentation.txt
    python synthesize_block.py --prompt-text "Inputs:
    - text (type: string): Text to analyze.
    
    Outputs:
    - sentiment (type: string): positive, negative, or neutral.
    
    Purpose:
    Analyze the sentiment of the input text."
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from block_synthesis.run_synthesis import synthesize_from_prompt


def get_provider_and_model():
    """Detect available API key and return provider/model."""
    if os.environ.get("OPENAI_API_KEY"):
        return "openai", "gpt-4o"
    elif os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic", "claude-sonnet-4-20250514"
    else:
        print("ERROR: No API key found. Set one of:")
        print("  OPENAI_API_KEY=sk-...")
        print("  ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)


async def main():
    parser = argparse.ArgumentParser(
        description="Synthesize a Python block from a natural language prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--prompt", "-p",
        type=str,
        help="Path to a file containing the block prompt",
    )
    parser.add_argument(
        "--prompt-text", "-t",
        type=str,
        help="Block prompt text directly",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path for the generated code",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic"],
        help="LLM provider (auto-detected from API keys if not specified)",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Model name",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=6,
        help="Maximum repair iterations (default: 6)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output the generated code",
    )
    
    args = parser.parse_args()
    
    if args.prompt:
        prompt_text = Path(args.prompt).read_text(encoding="utf-8")
    elif args.prompt_text:
        prompt_text = args.prompt_text
    elif not sys.stdin.isatty():
        prompt_text = sys.stdin.read()
    else:
        parser.print_help()
        sys.exit(1)
    
    if not prompt_text.strip():
        print("Error: Empty prompt", file=sys.stderr)
        sys.exit(1)
    
    if args.provider and args.model:
        provider, model = args.provider, args.model
    elif args.provider:
        provider = args.provider
        model = "gpt-4o" if provider == "openai" else "claude-sonnet-4-20250514"
    else:
        provider, model = get_provider_and_model()
    
    if not args.quiet:
        print(f"Provider: {provider}")
        print(f"Model: {model}")
        print(f"Max iterations: {args.max_iterations}")
        print()
        print("Prompt:")
        print("-" * 40)
        print(prompt_text.strip())
        print("-" * 40)
        print()
        print("Synthesizing...")
        print()
    
    try:
        code = await synthesize_from_prompt(
            prompt_text=prompt_text,
            provider=provider,
            model=model,
            max_iterations=args.max_iterations,
            output_file=args.output,
        )
        
        if args.quiet:
            print(code)
        else:
            print()
            print("=" * 60)
            print("GENERATED CODE:")
            print("=" * 60)
            print(code)
            print("=" * 60)
            
            if args.output:
                print(f"\nSaved to: {args.output}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
