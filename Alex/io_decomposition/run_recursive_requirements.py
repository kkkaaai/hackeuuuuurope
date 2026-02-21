"""
Entry point for running recursive requirement decomposition.
Extracts requirements from a task and recursively decomposes them into concrete steps.
"""

import os
import sys
import re
import json
from pathlib import Path

# Add parent directory to path
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from complexity_evaluator import CLEANED_DIR, evaluate_complexity
from recursive_io_decomposer import decompose_requirements_to_steps, restructure_task_with_requirement_steps
from model_tiers import get_model_for_complexity, get_tier_info


def is_valid_starting_task(task_record: dict) -> bool:
    """Check if task is valid for requirement decomposition.
    
    Accepts tasks with:
    - depth == 0 AND complexity_score set (explicit depth), OR
    - no depth field AND complexity_score set (implicit root task)
    """
    has_input = task_record.get("task_input") or task_record.get("input")
    has_complexity = task_record.get("complexity_score") is not None
    
    if not has_input or not has_complexity:
        return False
    
    depth = task_record.get("depth")
    
    # Accept if explicitly depth 0, or if no depth field (root task)
    return depth == 0 or depth is None


def find_first_valid_task():
    """Find the first task in CLEANED_DIR with depth==0 and complexity_score set."""
    cleaned_path = Path(CLEANED_DIR)
    if not cleaned_path.exists():
        return None, None
    
    json_files = sorted(cleaned_path.glob("*.json"))
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                task = json.load(f)
                if is_valid_starting_task(task):
                    return task, json_file
        except (json.JSONDecodeError, IOError):
            continue
    
    return None, None


def extract_requirements_from_task(task_input: str) -> list:
    """
    Extract requirements from task input.
    Looks for numbered items, bullet points, or natural language requirements.
    """
    requirements = []
    lines = task_input.split('\n')
    
    for line in lines:
        stripped = line.strip()
        # Match numbered items (1. 2. etc) or bullet points
        if stripped and (
            (len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in '.):') or
            stripped.startswith(('-', '*', '•'))
        ):
            # Remove numbering/bullet
            req = re.sub(r'^[\d.)\-*•]\s*', '', stripped)
            if req:
                requirements.append(req)
    
    return requirements if requirements else [task_input]


def main(filename: str = None, max_depth: int = None):
    """Main entry point for recursive requirement decomposition.
    
    Args:
        filename: Optional specific task file to process
        max_depth: Optional maximum recursion depth (None = infinite)
    """
    
    print("=" * 60)
    print("RECURSIVE REQUIREMENT DECOMPOSER")
    print("=" * 60)
    
    if max_depth:
        print(f"Max Depth: {max_depth}")
    else:
        print(f"Max Depth: Infinite")
    
    # Find task to process
    if filename:
        task_path = Path(CLEANED_DIR) / filename
        if not task_path.exists():
            print(f"ERROR: File {filename} not found in {CLEANED_DIR}")
            return
        
        with open(task_path, 'r', encoding='utf-8') as f:
            task = json.load(f)
    else:
        task, task_path = find_first_valid_task()
        if not task:
            print(f"ERROR: No valid tasks found in {CLEANED_DIR}")
            print("Need: depth == 0 and complexity_score != None")
            return
    
    print(f"\nProcessing task: {task_path.name}")
    print(f"Task ID: {task.get('task_id', 'N/A')}")
    print(f"Complexity Score: {task.get('complexity_score', 'N/A')}")
    
    # Handle both 'task_input' and 'input' field names
    task_input = task.get("task_input") or task.get("input", "")
    complexity_score = task.get("complexity_score", 50)
    task_id = task.get("task_id", task_path.stem)
    
    print(f"\nTask Input:\n{task_input[:200]}...")
    
    # Extract requirements
    print("\n" + "=" * 60)
    print("EXTRACTING REQUIREMENTS...")
    print("=" * 60)
    
    requirements = extract_requirements_from_task(task_input)
    print(f"\nFound {len(requirements)} requirement(s):")
    for i, req in enumerate(requirements, 1):
        print(f"  {i}. {req[:80]}...")
    
    # Decompose requirements to steps
    print("\n" + "=" * 60)
    print("DECOMPOSING REQUIREMENTS TO STEPS...")
    print("=" * 60)
    
    result = decompose_requirements_to_steps(requirements, complexity_score=complexity_score, max_depth=max_depth)
    
    if result.get("error"):
        print(f"\nERROR: {result['error']}")
        return
    
    print(f"\nModel Used: {result.get('model_used')} ({result.get('model_endpoint')})")
    if result.get('tier_info'):
        print(f"Tier: {result['tier_info'].get('description')}")
    
    # Display decompositions
    print("\n" + "=" * 60)
    print("REQUIREMENT DECOMPOSITIONS")
    print("=" * 60)
    
    decompositions = result.get("decompositions", {})
    for i, (req, decomp) in enumerate(decompositions.items(), 1):
        print(f"\n{'─' * 60}")
        print(f"REQUIREMENT {i}:")
        print(f"{req}")
        print(f"\n{decomp.get('content', 'N/A')}")
    
    # Restructure task with new format
    restructured = restructure_task_with_requirement_steps(
        task_id,
        task_input,
        complexity_score,
        requirements,
        decompositions
    )
    
    # Save restructured task
    output_path = task_path.parent / f"{task_path.stem}_requirements_decomposed.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(restructured, f, indent=2)
    
    print(f"\n" + "=" * 60)
    print("RESULTS SAVED")
    print("=" * 60)
    print(f"Output file: {output_path}")
    print(f"Total requirements: {len(requirements)}")
    print(f"Total decompositions: {len(decompositions)}")


if __name__ == "__main__":
    filename = None
    max_depth = None
    
    # Parse arguments: [filename] [max_depth]
    if len(sys.argv) > 1:
        try:
            max_depth = int(sys.argv[1])
        except ValueError:
            # Not a number, treat as filename
            filename = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            max_depth = int(sys.argv[2])
        except ValueError:
            pass
    
    main(filename, max_depth)
