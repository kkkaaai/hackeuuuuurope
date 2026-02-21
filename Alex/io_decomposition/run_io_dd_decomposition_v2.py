"""
IO-Driven Decomposition using Dependency-Driven Structure (V2 Engine)
Reads from dd_requests_v2/ and writes execution plans back to dd_requests_v2/
Uses V2 engine with recursive DERIVABLE input decomposition.

Usage: python run_io_dd_decomposition_v2.py [filename] [max_depth]
"""

import os
import sys
import glob
import json
from pathlib import Path

# Add parent directory to path to enable relative imports
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from io_decomposition.io_task_decomposer import decompose_task_io
from task_id_manager import get_depth

# Input and output directory for V2 decomposed tasks
DD_REQUESTS_V2_DIR = os.path.join(SCRIPT_DIR, "dd_requests_v2")


def is_valid_dd_task(task_record: dict) -> bool:
    """Check if task is valid for IO decomposition with DD structure."""
    return (
        task_record.get("task_id") and
        task_record.get("input") and
        "dependency_structure" in task_record
    )


def find_all_dd_tasks(skip_decomposed: bool = True):
    """Find all depth 0 DD tasks in dd_requests_v2, optionally skipping already decomposed ones."""
    dd_path = Path(DD_REQUESTS_V2_DIR)
    if not dd_path.exists():
        print(f"DD requests V2 directory not found: {DD_REQUESTS_V2_DIR}")
        return []
    
    tasks = []
    skipped_depth = 0
    skipped_decomposed = 0
    
    json_files = sorted(dd_path.glob("*.json"))
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                task = json.load(f)
                
                # Check if task is valid
                if not is_valid_dd_task(task):
                    continue
                
                # Check depth - only process depth 0 tasks
                task_id = task.get("task_id", "")
                depth = get_depth(task_id)
                if depth > 0:
                    skipped_depth += 1
                    continue
                
                # Skip if already decomposed (has execution_plan)
                if skip_decomposed and "execution_plan" in task:
                    skipped_decomposed += 1
                    continue
                
                tasks.append((task, json_file))
        except (json.JSONDecodeError, IOError):
            continue
    
    if skipped_depth > 0:
        print(f"[INFO] Skipped {skipped_depth} tasks (depth > 0)")
    if skipped_decomposed > 0:
        print(f"[INFO] Skipped {skipped_decomposed} tasks (already decomposed)")
    
    return tasks


def add_execution_plan_to_task(task: dict, io_result: dict) -> dict:
    """
    Add execution plan from IO decomposition to task.
    
    Args:
        task: Original DD task
        io_result: Result from decompose_task_io
    
    Returns:
        dict: Updated task with execution plan
    """
    if io_result.get("error"):
        return task
    
    task["execution_plan"] = {
        "model_used": io_result.get("model_used"),
        "model_endpoint": io_result.get("model_endpoint"),
        "inputs": io_result.get("inputs", []),
        "outputs": io_result.get("outputs", []),
        "steps": io_result.get("steps", []),
        "raw_response": io_result.get("raw_response")
    }
    
    # Add AEB analysis if available
    if io_result.get("aeb_analysis"):
        task["aeb_analysis"] = io_result["aeb_analysis"]
    
    # Mark as decomposed with V2 engine
    task["io_decomposed"] = True
    task["decomposition_engine"] = "v2"
    
    return task


def decompose_dd_task(task: dict, task_path: Path, max_depth: int = None) -> bool:
    """
    Decompose a DD task using IO decomposition V2 and save back to dd_requests_v2.
    
    Args:
        task: DD task record
        task_path: Path to task file in dd_requests_v2
        max_depth: Optional max depth limit
    
    Returns:
        bool: True if successful
    """
    print(f"\n{'='*60}")
    print(f"DECOMPOSING DD TASK (V2 ENGINE)")
    print(f"{'='*60}")
    
    task_input = task.get("input", "")
    task_id = task.get("task_id", "")
    
    print(f"\nTask ID: {task_id}")
    print(f"Input: {task_input[:100]}...")
    
    if max_depth:
        print(f"Max Depth: {max_depth}")
    
    # Extract subtask dependencies for context
    subtasks = task.get("subtasks", [])
    print(f"Subtasks: {len(subtasks)}")
    
    if subtasks:
        print("\nDependency Information:")
        for subtask in subtasks[:3]:  # Show first 3
            deps = subtask.get("dependencies", [])
            print(f"  - {subtask.get('input', 'N/A')[:60]}")
            if deps:
                print(f"    Depends on: {deps}")
    
    # Run IO decomposition with V2 engine
    print(f"\nRunning IO decomposition (V2 - recursive DERIVABLE)...")
    try:
        io_result = decompose_task_io(
            task_input,
            client=None,
            current_depth=0,
            engine_version="v2"  # Force V2 engine
        )
        
        if io_result.get("error"):
            print(f"[ERROR] {io_result['error']}")
            return False
        
        print(f"[OK] Decomposition successful")
        print(f"Model: {io_result.get('model_used')}")
        print(f"Engine: V2 (recursive DERIVABLE)")
        
        # Add execution plan to task
        updated_task = add_execution_plan_to_task(task, io_result)
        
        # Save back to dd_requests_v2 (same location)
        with open(task_path, 'w', encoding='utf-8') as f:
            json.dump(updated_task, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] Saved to {task_path.name}")
        
        # Show results
        if io_result.get("inputs"):
            print(f"\nInputs identified: {len(io_result['inputs'])}")
            for inp in io_result['inputs'][:2]:
                if isinstance(inp, dict):
                    print(f"  - {inp.get('name', 'N/A')} ({inp.get('source_type', 'N/A')})")
                else:
                    print(f"  - {inp}")
        
        if io_result.get("steps"):
            print(f"\nExecution steps: {len(io_result['steps'])}")
            for i, step in enumerate(io_result['steps'][:3], 1):
                if isinstance(step, dict):
                    print(f"  {i}. {step.get('action', str(step))[:60]}")
                else:
                    print(f"  {i}. {str(step)[:60]}")
        
        return True
    
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main(filename: str = None, max_depth: int = None):
    """Main entry point for IO DD decomposition V2."""
    
    print("="*60)
    print("IO-DRIVEN DECOMPOSITION (DD STRUCTURE - V2 ENGINE)")
    print("="*60)
    print(f"Directory: {DD_REQUESTS_V2_DIR}")
    print(f"Engine: V2 (recursive DERIVABLE decomposition)")
    
    # Create directory if it doesn't exist
    dd_path = Path(DD_REQUESTS_V2_DIR)
    dd_path.mkdir(exist_ok=True)
    print(f"\n[OK] Directory ready: {DD_REQUESTS_V2_DIR}\n")
    
    # Find or load task(s)
    if filename:
        # Process single file
        task_path = dd_path / filename
        if not task_path.exists():
            print(f"\n[ERROR] File not found: {task_path}")
            return
        
        with open(task_path, 'r', encoding='utf-8') as f:
            task = json.load(f)
        
        tasks_to_process = [(task, task_path)]
    else:
        # Process all tasks, skipping already decomposed ones
        tasks_to_process = find_all_dd_tasks(skip_decomposed=True)
        if not tasks_to_process:
            print(f"\n[INFO] No tasks to process - all depth 0 tasks already decomposed")
            print(f"To reprocess, remove the 'execution_plan' key from tasks in dd_requests_v2/")
            return
    
    print(f"Found {len(tasks_to_process)} task(s) to decompose\n")
    
    # Process all tasks
    completed = 0
    failed = 0
    
    for task, task_path in tasks_to_process:
        print(f"Processing [{completed + failed + 1}/{len(tasks_to_process)}]: {task_path.name}")
        
        # Decompose task
        success = decompose_dd_task(task, task_path, max_depth)
        
        if success:
            completed += 1
        else:
            failed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print("BATCH DECOMPOSITION COMPLETE (V2)")
    print(f"{'='*60}")
    print(f"Completed: {completed}/{len(tasks_to_process)}")
    if failed > 0:
        print(f"Failed: {failed}/{len(tasks_to_process)}")
    print(f"\nResults saved to: {DD_REQUESTS_V2_DIR}")


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
