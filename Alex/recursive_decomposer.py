import os
import json
import glob
import time
from pathlib import Path
from datetime import datetime, timezone

from complexity_evaluator import evaluate_complexity, _get_client, CLEANED_DIR, LOGS_DIR, EVAL_GEN
from task_decomposer import decompose_task, _parse_decomposition_response
from task_id_manager import create_subtask_id, get_depth, parse_task_id


API_RATE_LIMIT_SECONDS = 5
_last_api_call_time = 0


def rate_limit_api_call():
    """Enforce API rate limiting."""
    global _last_api_call_time
    elapsed = time.time() - _last_api_call_time
    if elapsed < API_RATE_LIMIT_SECONDS:
        wait_time = API_RATE_LIMIT_SECONDS - elapsed
        print(f"    [RATE_LIMIT] Waiting {wait_time:.1f}s...", flush=True)
        time.sleep(wait_time)
    _last_api_call_time = time.time()
    print(f"    [API_CALL] Rate limit check passed", flush=True)


def find_tasks_to_decompose(request_data, complexity_threshold, current_path=""):
    """
    Recursively find all tasks with complexity > threshold.
    Returns them sorted by depth (greatest depth first).
    
    Args:
        request_data: The task/subtask dict
        complexity_threshold: The threshold
        current_path: Path to this task in the hierarchy
    
    Returns:
        list of dicts: [{'task_id': ..., 'data': ..., 'depth': ..., 'parent_data': ...}, ...]
    """
    tasks_to_decompose = []
    
    complexity = request_data.get("complexity_score")
    
    # If this task exceeds threshold and is a leaf, mark for decomposition
    subtasks = request_data.get("subtasks", [])
    if complexity and complexity > complexity_threshold and len(subtasks) == 0:
        tasks_to_decompose.append({
            'task_id': request_data.get("task_id"),
            'data': request_data,
            'depth': get_depth(request_data.get("task_id", "")),
            'parent_data': None
        })
    
    # Recursively check subtasks
    for subtask in subtasks:
        tasks_to_decompose.extend(find_tasks_to_decompose(subtask, complexity_threshold, current_path))
    
    return tasks_to_decompose


def update_subtask_with_id(subtask, task_id, index):
    """
    Assign a hierarchical task ID to a subtask.
    """
    subtask_id = create_subtask_id(task_id, index)
    subtask["task_id"] = subtask_id
    return subtask


def evaluate_missing_complexities(task_data, client=None, depth=0):
    """
    Recursively evaluate complexity for all subtasks that have None complexity_score.
    
    Args:
        task_data: The task/subtask data dict
        client: OpenAI client
        depth: Current recursion depth
    
    Returns:
        tuple: (success, updated_task_data)
    """
    if client is None:
        client = _get_client()
    
    indent = "  " * depth
    task_id = task_data.get("task_id", "")
    complexity = task_data.get("complexity_score")
    
    print(f"{indent}[EVAL_MISSING] Processing task: {task_id}", flush=True)
    
    # Evaluate this task if missing complexity
    if complexity is None and task_data.get("input"):
        print(f"{indent}  [EVAL_MISSING] Task has no complexity, evaluating...", flush=True)
        rate_limit_api_call()
        
        try:
            print(f"{indent}    [EVAL_MISSING] Calling evaluate_complexity()...", flush=True)
            complexity_result = evaluate_complexity(task_data.get("input"), client)
            task_data["complexity_score"] = complexity_result.get("score")
            complexity = complexity_result.get("score")
            print(f"{indent}    [EVAL_MISSING] Result: Complexity = {complexity}", flush=True)
        except Exception as e:
            print(f"{indent}    [ERROR] Failed to evaluate: {e}", flush=True)
    else:
        print(f"{indent}  [EVAL_MISSING] Task already has complexity: {complexity}", flush=True)
    
    # Recursively evaluate subtasks
    subtasks = task_data.get("subtasks", [])
    print(f"{indent}  [EVAL_MISSING] Found {len(subtasks)} subtasks", flush=True)
    
    for i, subtask in enumerate(subtasks):
        print(f"{indent}  [EVAL_MISSING] Processing subtask {i+1}/{len(subtasks)}...", flush=True)
        success, updated_subtask = evaluate_missing_complexities(subtask, client, depth + 1)
        if success:
            # Update the subtask in-place by copying its properties
            for key in updated_subtask:
                subtask[key] = updated_subtask[key]
    
    print(f"{indent}[EVAL_MISSING] Completed task: {task_id}", flush=True)
    return True, task_data


def decompose_high_complexity_leaves(task_data, complexity_threshold, client=None, depth=0):
    """
    Recursively find and decompose all leaf tasks with complexity > threshold.
    
    Args:
        task_data: The task/subtask data dict
        complexity_threshold: Complexity threshold
        client: OpenAI client
        depth: Current recursion depth
    
    Returns:
        tuple: (success, updated_task_data)
    """
    if client is None:
        client = _get_client()
    
    indent = "  " * depth
    task_id = task_data.get("task_id", "")
    complexity = task_data.get("complexity_score")
    subtasks = task_data.get("subtasks", [])
    
    print(f"{indent}[DECOMP_LEAVES] Checking task: {task_id} (complexity: {complexity}, is_leaf: {len(subtasks)==0})", flush=True)
    
    # Check if this is a leaf task (no subtasks) with high complexity
    if len(subtasks) == 0 and complexity and complexity > complexity_threshold:
        print(f"{indent}[DECOMP_LEAVES] HIGH-COMPLEXITY LEAF FOUND! (complexity: {complexity} > {complexity_threshold})", flush=True)
        print(f"{indent}  [DECOMP_LEAVES] Decomposing task...", flush=True)
        
        task_input = task_data.get("input", "")
        
        # Rate limit API call
        rate_limit_api_call()
        
        # Decompose the task
        try:
            print(f"{indent}    [DECOMP_LEAVES] Calling decompose_task()...", flush=True)
            decomposition_result = decompose_task(task_input, client)
            print(f"{indent}    [DECOMP_LEAVES] decompose_task() returned", flush=True)
        except Exception as e:
            print(f"{indent}    [ERROR] Failed to decompose: {e}", flush=True)
            return False, task_data
        
        if decomposition_result.get("error"):
            print(f"{indent}    [ERROR] {decomposition_result['error']}", flush=True)
            return False, task_data
        
        subtasks_raw = decomposition_result.get("subtasks", [])
        if not subtasks_raw:
            print(f"{indent}    [WARN] No subtasks generated", flush=True)
            return False, task_data
        
        print(f"{indent}    [DECOMP_LEAVES] Created {len(subtasks_raw)} subtasks", flush=True)
        
        # Create subtask records with IDs and evaluate complexity
        processed_subtasks = []
        for index, subtask_raw in enumerate(subtasks_raw):
            subtask_id = create_subtask_id(task_id, index)
            estimated_complexity = subtask_raw.get("estimated_complexity")
            
            print(f"{indent}      [DECOMP_LEAVES] Subtask {index+1}/{len(subtasks_raw)}: {subtask_id} (est. complexity: {estimated_complexity})", flush=True)
            
            subtask_record = {
                "task_id": subtask_id,
                "input": subtask_raw.get("description", ""),
                "complexity_score": estimated_complexity,  # Use estimated from decomposition
                "eval_gen": EVAL_GEN,
                "subtasks": []
            }
            
            processed_subtasks.append(subtask_record)
        
        # Update task data with decomposed subtasks
        task_data["subtasks"] = processed_subtasks
        print(f"{indent}  [DECOMP_LEAVES] Successfully decomposed into {len(processed_subtasks)} subtasks", flush=True)
    else:
        if len(subtasks) > 0:
            print(f"{indent}  [DECOMP_LEAVES] Task is not a leaf (has {len(subtasks)} subtasks), skipping decomposition", flush=True)
        elif complexity is None:
            print(f"{indent}  [DECOMP_LEAVES] Task has no complexity score, skipping", flush=True)
        else:
            print(f"{indent}  [DECOMP_LEAVES] Complexity {complexity} <= threshold {complexity_threshold}, skipping", flush=True)
    
    # Recursively process subtasks
    subtasks_to_process = task_data.get("subtasks", [])
    print(f"{indent}  [DECOMP_LEAVES] Processing {len(subtasks_to_process)} subtasks...", flush=True)
    
    for i, subtask in enumerate(subtasks_to_process):
        print(f"{indent}  [DECOMP_LEAVES] Processing subtask {i+1}/{len(subtasks_to_process)}...", flush=True)
        success, updated_subtask = decompose_high_complexity_leaves(subtask, complexity_threshold, client, depth + 1)
        if success:
            # Update the subtask in-place
            for key in updated_subtask:
                subtask[key] = updated_subtask[key]
    
    print(f"{indent}[DECOMP_LEAVES] Completed task: {task_id}", flush=True)
    return True, task_data


def save_recursive_decomposition_log(task_id, task_data, logs_dir=LOGS_DIR):
    """
    Save the recursive decomposition structure to a log file.
    """
    try:
        os.makedirs(logs_dir, exist_ok=True)
        log_filename = f"recursive_decomp_{task_id}.json"
        log_path = os.path.join(logs_dir, log_filename)
        
        log_data = {
            "root_task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "task_structure": task_data,
            "depth": get_depth(task_id)
        }
        
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving recursive decomposition log: {e}")
        return False


def count_tasks_in_tree(task_data):
    """
    Count total tasks (including root) in the decomposition tree.
    """
    count = 1
    for subtask in task_data.get("subtasks", []):
        count += count_tasks_in_tree(subtask)
    return count


def get_tree_depth(task_data):
    """
    Get the maximum depth of the decomposition tree.
    """
    if not task_data.get("subtasks"):
        return 0
    return 1 + max(get_tree_depth(st) for st in task_data.get("subtasks", []))


def process_request_file(request_file, complexity_threshold):
    """
    Process a single request file through recursive decomposition:
    1. Evaluate all subtasks with missing complexity
    2. Decompose all leaf tasks with complexity > threshold
    3. Repeat until complete
    
    Args:
        request_file: Path to cleaned request JSON
        complexity_threshold: Complexity threshold
    
    Returns:
        dict: Results summary
    """
    print(f"\n[PROCESS] Loading request file: {os.path.basename(request_file)}", flush=True)
    
    try:
        with open(request_file, "r", encoding="utf-8") as f:
            request_data = json.load(f)
        print(f"[PROCESS] File loaded successfully", flush=True)
    except Exception as e:
        print(f"[ERROR] Error loading {os.path.basename(request_file)}: {e}", flush=True)
        return None
    
    task_id = request_data.get("task_id")
    root_complexity = request_data.get("complexity_score")
    filename = os.path.basename(request_file)
    
    print(f"\n{'='*80}", flush=True)
    print(f"[PROCESS] Processing: {filename}", flush=True)
    print(f"[PROCESS] Task ID: {task_id}", flush=True)
    print(f"[PROCESS] Root complexity: {root_complexity}", flush=True)
    print(f"[PROCESS] Decomposition threshold: {complexity_threshold}", flush=True)
    print(f"{'='*80}", flush=True)
    
    if root_complexity is None:
        print("[PROCESS] Skipping: No root complexity score", flush=True)
        return None
    
    if root_complexity <= complexity_threshold:
        print(f"[PROCESS] Skipping: Root complexity {root_complexity} <= {complexity_threshold}", flush=True)
        return None
    
    print(f"[PROCESS] Root complexity {root_complexity} > {complexity_threshold}, proceeding...", flush=True)
    
    try:
        print(f"[PROCESS] Creating OpenAI client...", flush=True)
        client = _get_client()
        print(f"[PROCESS] Client created successfully", flush=True)
    except Exception as e:
        print(f"[ERROR] Failed to create client: {e}", flush=True)
        return None
    
    # Step 1: Evaluate all missing complexities
    print(f"\n{'='*80}", flush=True)
    print(f"[STEP 1] Evaluating missing complexity scores...", flush=True)
    print(f"{'='*80}", flush=True)
    success, updated_data = evaluate_missing_complexities(request_data, client, depth=0)
    if not success:
        print("[ERROR] Failed during complexity evaluation", flush=True)
        return None
    print(f"[STEP 1] Completed", flush=True)
    
    # Step 2: Decompose high-complexity leaf tasks
    print(f"\n{'='*80}", flush=True)
    print(f"[STEP 2] Decomposing high-complexity leaf tasks (threshold: {complexity_threshold})...", flush=True)
    print(f"{'='*80}", flush=True)
    success, updated_data = decompose_high_complexity_leaves(updated_data, complexity_threshold, client, depth=0)
    if not success:
        print("[ERROR] Failed during decomposition", flush=True)
        return None
    print(f"[STEP 2] Completed", flush=True)
    
    # Save updated request
    print(f"\n[PROCESS] Saving updated request file...", flush=True)
    try:
        with open(request_file, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, ensure_ascii=False, indent=2)
        print(f"[PROCESS] File saved successfully", flush=True)
    except Exception as e:
        print(f"[ERROR] Error saving updated request: {e}", flush=True)
        return None
    
    # Save recursive decomposition log
    print(f"[PROCESS] Saving decomposition log...", flush=True)
    save_recursive_decomposition_log(task_id, updated_data)
    print(f"[PROCESS] Log saved successfully", flush=True)
    
    # Calculate statistics
    print(f"[PROCESS] Calculating statistics...", flush=True)
    total_tasks = count_tasks_in_tree(updated_data)
    max_depth = get_tree_depth(updated_data)
    
    print(f"\n{'='*80}", flush=True)
    print(f"[SUCCESS] Decomposition Complete!", flush=True)
    print(f"[STATS] Total tasks in tree: {total_tasks}", flush=True)
    print(f"[STATS] Maximum tree depth: {max_depth}", flush=True)
    print(f"{'='*80}\n", flush=True)
    
    return {
        'filename': filename,
        'task_id': task_id,
        'root_complexity': root_complexity,
        'total_tasks': total_tasks,
        'max_depth': max_depth,
        'success': True
    }


def find_first_root_file(sample_dir=CLEANED_DIR):
    """
    Find the first cleaned_request file with depth 0 (root task).
    
    Args:
        sample_dir: Directory with cleaned requests
    
    Returns:
        str: Path to the first root file, or None if not found
    """
    json_files = glob.glob(os.path.join(sample_dir, "*.json"))
    
    for request_file in sorted(json_files):
        try:
            with open(request_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            task_id = data.get("task_id", "")
            depth = get_depth(task_id)
            
            if depth == 0:
                return request_file
        except Exception:
            continue
    
    return None


def recursive_decompose_single_file(complexity_threshold=50, sample_dir=CLEANED_DIR):
    """
    Recursively decompose a single file (the first root file found).
    Continues until all leaf tasks have complexity <= threshold.
    
    Args:
        complexity_threshold: Complexity threshold
        sample_dir: Directory with cleaned requests
    
    Returns:
        dict: Summary of the processed file
    """
    if not os.path.exists(sample_dir):
        print(f"Directory not found: {sample_dir}")
        return None
    
    # Find the first root file
    request_file = find_first_root_file(sample_dir)
    if not request_file:
        print(f"No root files (depth 0) found in {sample_dir}")
        return None
    
    print(f"\nRecursive Task Decomposition Pipeline")
    print(f"Threshold: {complexity_threshold}")
    print(f"Processing single file (first root found)\n")
    
    result = process_request_file(request_file, complexity_threshold)
    
    if result is None:
        print("Skipped: No valid root complexity score or below threshold")
        return None
    
    if not result.get('success'):
        print("Failed to decompose")
        return None
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"DECOMPOSITION COMPLETE")
    print(f"{'='*80}")
    print(f"File: {result['filename']}")
    print(f"Task ID: {result['task_id']}")
    print(f"Root complexity: {result['root_complexity']}")
    print(f"Total tasks in tree: {result['total_tasks']}")
    print(f"Maximum tree depth: {result['max_depth']}")
    print(f"{'='*80}\n")
    
    # Save results summary
    summary_file = os.path.join(BASE_DIR, "recursive_decomposition_result.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Result saved to: {summary_file}\n")
    
    return result


def recursive_decompose_all(complexity_threshold=50, sample_dir=CLEANED_DIR):
    """
    Legacy function - now calls single file decomposition.
    
    Args:
        complexity_threshold: Complexity threshold
        sample_dir: Directory with cleaned requests
    
    Returns:
        dict: Summary of the processed file
    """
    return recursive_decompose_single_file(complexity_threshold, sample_dir)


if __name__ == "__main__":
    import sys
    
    BASE_DIR = os.path.dirname(__file__)
    
    threshold = 50
    if len(sys.argv) > 1:
        try:
            threshold = int(sys.argv[1])
        except ValueError:
            print(f"Invalid threshold: {sys.argv[1]}")
            print("Usage: python recursive_decomposer.py [complexity_threshold]")
            sys.exit(1)
    
    print(f"Starting recursive decomposition with threshold: {threshold}")
    sys.stdout.flush()
    
    result = recursive_decompose_all(complexity_threshold=threshold)
    
    if result:
        print(f"Success!")
    else:
        print(f"No result")
