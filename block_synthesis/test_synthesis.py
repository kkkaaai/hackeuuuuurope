#!/usr/bin/env python
"""
Quick test script for block synthesis.

Usage:
    python block_synthesis/test_synthesis.py
    
    # With custom provider/model:
    OPENAI_API_KEY=sk-xxx python block_synthesis/test_synthesis.py
    ANTHROPIC_API_KEY=sk-ant-xxx python block_synthesis/test_synthesis.py --provider anthropic
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from block_synthesis.run_synthesis import synthesize_from_prompt


SAMPLE_PROMPT = """
Inputs:
- numbers (type: list of integers): A list of numbers to process.

Outputs:
- result (type: JSON object): Contains sum, mean, and count.

Purpose:
Calculate basic statistics (sum, mean, count) for a list of numbers.

Test Input:
{"numbers": [1, 2, 3, 4, 5]}

Expected Output:
{"result": {"sum": 15, "mean": 3.0, "count": 5}}
"""


def check_api_keys():
    """Check which API keys are available."""
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    
    if openai_key:
        return "openai", "gpt-4o"
    elif anthropic_key:
        return "anthropic", "claude-sonnet-4-20250514"
    else:
        print("ERROR: No API keys found!")
        print()
        print("Please set one of the following environment variables:")
        print("  OPENAI_API_KEY=sk-...")
        print("  ANTHROPIC_API_KEY=sk-ant-...")
        print()
        print("Or add them to your .env file")
        sys.exit(1)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["openai", "anthropic"])
    parser.add_argument("--model", type=str)
    args = parser.parse_args()
    
    if args.provider and args.model:
        provider, model = args.provider, args.model
    elif args.provider:
        provider = args.provider
        model = "gpt-4o" if provider == "openai" else "claude-sonnet-4-20250514"
    else:
        provider, model = check_api_keys()
    
    print("=" * 60)
    print("BLOCK SYNTHESIS TEST")
    print("=" * 60)
    print(f"Provider: {provider}")
    print(f"Model: {model}")
    print()
    print("Prompt:")
    print(SAMPLE_PROMPT)
    print()
    
    try:
        code = await synthesize_from_prompt(
            prompt_text=SAMPLE_PROMPT,
            provider=provider,
            model=model,
            max_iterations=6,
            output_file="block_synthesis/output/stats_block.py",
        )
        
        print()
        print("=" * 60)
        print("SUCCESS! Generated code:")
        print("=" * 60)
        print(code)
        
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    Path("block_synthesis/output").mkdir(exist_ok=True)
    asyncio.run(main())
