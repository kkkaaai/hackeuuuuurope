"""
Parallel Recursive Task Decomposer
Uses concurrent.futures to parallelize tree traversal and evaluation.
Processes multiple branches concurrently while maintaining single root file processing.
"""

import os
import json
import glob
import time
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from queue import Queue

from complexity_evaluator import evaluate_complexity, _get_client, CLEANED_DIR, LOGS_DIR, EVAL_GEN
from task_decomposer import decompose_task, _parse_decomposition_response
from task_id_manager import create_subtask_id, get_depth, parse_task_id


API_RATE_LIMIT_SECONDS = 5
_last_api_call_time = 0
_api_lock = Lock()  # Protect API rate limiting across threads


def rate_limit_api_call():
    """Thread-safe API rate limiting."""
    global _last_api_call_time
    with _api_lock:
        elapsed = time.time() - _last_api_call_time
        if elapsed < API_RATE_LIMIT_SECONDS:
            wait_time = API_RATE_LIMIT_SECONDS - elapsed
            time.sleep(wait_time)
        _last_api_call_time = time.time()


def evaluate_task_complexity(task_data, client=None):
    """
    Evaluate complexity for a single task if missing.
    Thread-safe function for concurrent execution.
    
    Returns:
        tuple: (task_id, success, updated_task_data)
    """
    if client is None:
        client = _get_client()
    
    task_id = task_data.get("task_id", "")
    complexity = task_data.get("complexity_score")
    
    # Skip if already has complexity
    if complexity is not None:
        print(f"[EVAL] {task_id}: Already has complexity {complexity}", flush=True)
        return (task_id, True, task_data)
    
    # Skip if no input
    if not task_data.get("input"):
        print(f"[EVAL] {task_id}: No input text, skipping", flush=True)
        return (task_id, True, task_data)
    
    print(f"[EVAL] {task_id}: Evaluating...", flush=True)
    rate_limit_api_call()
    
    try:
        complexity_result = evaluate_complexity(task_data.get("input"), client)
        task_data["complexity_score"] = complexity_result.get("score")
        score = complexity_result.get("score")
        print(f"[EVAL] {task_id}: Result = {score}", flush=True)
        return (task_id, True, task_data)
    except Exception as e:
        print(f"[EVAL] {task_id}: ERROR - {e}", flush=True)
        return (task_id, False, task_data)


def decompose_task_wrapper(task_data, complexity_threshold, client=None):
    """
    Decompose a single high-complexity leaf task.
    Thread-safe function for concurrent execution.
    
    Returns:
        tuple: (task_id, success, updated_task_data)
    """
    if client is None:
        client = _get_client()
    
    task_id = task_data.get("task_id", "")
    complexity = task_data.get("complexity_score")
    subtasks = task_data.get("subtasks", [])
    
    # Skip if not a leaf task
    if len(subtasks) > 0:
        print(f"[DECOMP] {task_id}: Not a leaf (has {len(subtasks)} subtasks)", flush=True)
        return (task_id, True, task_data)
    
    # Skip if no complexity or below threshold
    if not complexity or complexity <= complexity_threshold:
        print(f"[DECOMP] {task_id}: Complexity {complexity} <= {complexity_threshold}, skipping", flush=True)
        return (task_id, True, task_data)
    
    print(f"[DECOMP] {task_id}: Decomposing (complexity {complexity})...", flush=True)
    rate_limit_api_call()
    
    try:
        task_input = task_data.get("input", "")
        decomposition_result = decompose_task(task_input, client)
    except Exception as e:
        print(f"[DECOMP] {task_id}: ERROR - {e}", flush=True)
        return (task_id, False, task_data)
    
    if decomposition_result.get("error"):
        print(f"[DECOMP] {task_id}: ERROR - {decomposition_result['error']}", flush=True)
        return (task_id, False, task_data)
    
    subtasks_raw = decomposition_result.get("subtasks", [])
    if not subtasks_raw:
        print(f"[DECOMP] {task_id}: No subtasks generated", flush=True)
        return (task_id, False, task_data)
    
    print(f"[DECOMP] {task_id}: Created {len(subtasks_raw)} subtasks", flush=True)
    
    # Create subtask records with hierarchical IDs
    processed_subtasks = []
    for index, subtask_raw in enumerate(subtasks_raw):
        subtask_id = create_subtask_id(task_id, index)
        
        subtask_record = {
            "task_id": subtask_id,
            "input": subtask_raw.get("description", ""),
            "complexity_score": subtask_raw.get("estimated_complexity"),
            "eval_gen": EVAL_GEN,
            "subtasks": []
        }
        processed_subtasks.append(subtask_record)
    
    task_data["subtasks"] = processed_subtasks
    print(f"[DECOMP] {task_id}: Successfully decomposed", flush=True)
    return (task_id, True, task_data)


def collect_all_tasks(task_data):
    """
    Flatten tree structure into a list of all tasks.
    Used for batch processing in parallel.
    
    Returns:
        list of task_data dicts at all levels
    """
    tasks = [task_data]
    for subtask in task_data.get("subtasks", []):
        tasks.extend(collect_all_tasks(subtask))
    return tasks


def rebuild_tree_from_map(root_data, task_map):
    """
    Rebuild nested tree structure from flat map of updated tasks.
    
    Args:
        root_data: Original root task
        task_map: Dict mapping task_id -> updated task_data
    
    Returns:
        Updated root_data with all changes applied
    """
    root_id = root_data.get("task_id")
    
    # Update this task if in map
    if root_id in task_map:
        for key in task_map[root_id]:
            root_data[key] = task_map[root_id][key]
    
    # Recursively update subtasks
    for subtask in root_data.get("subtasks", []):
        rebuild_tree_from_map(subtask, task_map)
    
    return root_data


def process_request_file_parallel(request_file, complexity_threshold, max_workers=4):
    """
    Process a single request file with parallel task processing.
    
    Strategy:
    1. Flatten tree into task list
    2. Evaluate all missing complexities in parallel
    3. Decompose all high-complexity leaves in parallel
    4. Rebuild tree structure
    5. Repeat steps 2-4 until no more decompositions
    
    Args:
        request_file: Path to cleaned request JSON
        complexity_threshold: Complexity threshold
        max_workers: Max concurrent threads
    
    Returns:
        dict: Results summary
    """
    print(f"\n[PROCESS] Loading file: {os.path.basename(request_file)}", flush=True)
    
    try:
        with open(request_file, "r", encoding="utf-8") as f:
            request_data = json.load(f)
        print(f"[PROCESS] File loaded successfully", flush=True)
    except Exception as e:
        print(f"[ERROR] Failed to load file: {e}", flush=True)
        return None
    
    task_id = request_data.get("task_id")
    root_complexity = request_data.get("complexity_score")
    filename = os.path.basename(request_file)
    
    print(f"\n{'='*80}", flush=True)
    print(f"[PROCESS] Processing: {filename}", flush=True)
    print(f"[PROCESS] Task ID: {task_id}", flush=True)
    print(f"[PROCESS] Root complexity: {root_complexity}", flush=True)
    print(f"[PROCESS] Threshold: {complexity_threshold}", flush=True)
    print(f"[PROCESS] Max workers: {max_workers}", flush=True)
    print(f"{'='*80}", flush=True)
    
    if root_complexity is None or root_complexity <= complexity_threshold:
        print(f"[PROCESS] Skipping: Root complexity {root_complexity} not above threshold", flush=True)
        return None
    
    client = _get_client()
    iteration = 0
    
    while True:
        iteration += 1
        print(f"\n{'='*80}", flush=True)
        print(f"[ITERATION {iteration}] Processing tree...", flush=True)
        print(f"{'='*80}", flush=True)
        
        # Flatten tree into task list
        all_tasks = collect_all_tasks(request_data)
        print(f"[ITERATION {iteration}] Flattened tree into {len(all_tasks)} tasks", flush=True)
        
        # Find tasks needing evaluation
        tasks_needing_eval = [t for t in all_tasks if t.get("complexity_score") is None and t.get("input")]
        print(f"[ITERATION {iteration}] Tasks needing evaluation: {len(tasks_needing_eval)}", flush=True)
        
        # Evaluate in parallel
        if tasks_needing_eval:
            print(f"[ITERATION {iteration}] Starting parallel evaluation with {max_workers} workers...", flush=True)
            task_map = {}
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(evaluate_task_complexity, task, client): task.get("task_id")
                    for task in tasks_needing_eval
                }
                
                completed = 0
                for future in as_completed(futures):
                    completed += 1
                    task_id_result, success, updated_task = future.result()
                    if success:
                        task_map[task_id_result] = updated_task
                    print(f"[ITERATION {iteration}] Evaluation {completed}/{len(tasks_needing_eval)} complete", flush=True)
            
            # Apply updates to tree
            print(f"[ITERATION {iteration}] Rebuilding tree with evaluation results...", flush=True)
            request_data = rebuild_tree_from_map(request_data, task_map)
        
        # Find high-complexity leaves to decompose
        all_tasks = collect_all_tasks(request_data)
        leaves_to_decompose = [
            t for t in all_tasks 
            if len(t.get("subtasks", [])) == 0 
            and t.get("complexity_score") 
            and t["complexity_score"] > complexity_threshold
        ]
        print(f"[ITERATION {iteration}] High-complexity leaves to decompose: {len(leaves_to_decompose)}", flush=True)
        
        if not leaves_to_decompose:
            print(f"[ITERATION {iteration}] No more decompositions needed, complete!", flush=True)
            break
        
        # Decompose in parallel
        print(f"[ITERATION {iteration}] Starting parallel decomposition with {max_workers} workers...", flush=True)
        task_map = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(decompose_task_wrapper, task, complexity_threshold, client): task.get("task_id")
                for task in leaves_to_decompose
            }
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                task_id_result, success, updated_task = future.result()
                if success:
                    task_map[task_id_result] = updated_task
                print(f"[ITERATION {iteration}] Decomposition {completed}/{len(leaves_to_decompose)} complete", flush=True)
        
        # Apply updates to tree
        print(f"[ITERATION {iteration}] Rebuilding tree with decomposition results...", flush=True)
        request_data = rebuild_tree_from_map(request_data, task_map)
    
    # Save updated request
    print(f"\n[PROCESS] Saving updated request file...", flush=True)
    try:
        with open(request_file, "w", encoding="utf-8") as f:
            json.dump(request_data, f, ensure_ascii=False, indent=2)
        print(f"[PROCESS] File saved successfully", flush=True)
    except Exception as e:
        print(f"[ERROR] Failed to save file: {e}", flush=True)
        return None
    
    # Calculate statistics
    def count_tasks(task_data):
        return 1 + sum(count_tasks(st) for st in task_data.get("subtasks", []))
    
    def max_depth(task_data, current=0):
        if not task_data.get("subtasks"):
            return current
        return max(max_depth(st, current + 1) for st in task_data.get("subtasks", []))
    
    total_tasks = count_tasks(request_data)
    max_tree_depth = max_depth(request_data)
    
    print(f"\n{'='*80}", flush=True)
    print(f"[SUCCESS] Decomposition Complete!", flush=True)
    print(f"[STATS] Total tasks in tree: {total_tasks}", flush=True)
    print(f"[STATS] Maximum tree depth: {max_tree_depth}", flush=True)
    print(f"[STATS] Iterations required: {iteration}", flush=True)
    print(f"{'='*80}\n", flush=True)
    
    return {
        'filename': filename,
        'task_id': task_id,
        'root_complexity': root_complexity,
        'total_tasks': total_tasks,
        'max_depth': max_tree_depth,
        'iterations': iteration,
        'success': True
    }


if __name__ == "__main__":
    import sys
    
    threshold = 50
    workers = 4
    
    if len(sys.argv) > 1:
        try:
            threshold = int(sys.argv[1])
        except ValueError:
            print(f"Invalid threshold: {sys.argv[1]}")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        try:
            workers = int(sys.argv[2])
        except ValueError:
            print(f"Invalid worker count: {sys.argv[2]}")
            sys.exit(1)
    
    print(f"Starting parallel recursive decomposition")
    print(f"  Threshold: {threshold}")
    print(f"  Workers: {workers}\n")
    
    result = process_request_file_parallel(
        next(glob.iglob(os.path.join(CLEANED_DIR, "*.json"))),
        complexity_threshold=threshold,
        max_workers=workers
    )
    
    if result:
        print(f"Result: {result}")
    else:
        print(f"No result")
