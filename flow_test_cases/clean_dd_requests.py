"""
Dependency-Driven Request Cleaner
Processes cleaned requests and creates dependency-driven subtask structures.
Saves output to dd_requests/ directory.
"""

import os
import sys
import json
import glob
from pathlib import Path

# Add parent directory to path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from task_id_manager import generate_base_id, create_subtask_id

SAMPLE_DIR = os.path.join(BASE_DIR, "sample_requests")
DD_REQUESTS_DIR = os.path.join(BASE_DIR, "dd_requests")
DD_REQUESTS_V2_DIR = os.path.join(BASE_DIR, "dd_requests_v2")


def extract_dependencies_from_task(task_input: str) -> list:
    """
    Extract task dependencies and ordering from task description.
    
    Looks for patterns like:
    - "1. Task A (requires X)"
    - "Task B depends on Task A"
    - "After X is done, do Y"
    
    Args:
        task_input: Task description text
    
    Returns:
        list: List of (task_name, dependencies, order) tuples
    """
    dependencies = []
    
    # Simple dependency extraction from numbered items
    lines = task_input.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        
        # Match numbered items
        if len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in '.):':
            # Extract task description
            task_desc = stripped.split('. ', 1)[-1] if '. ' in stripped else stripped
            
            # Check for dependency keywords
            deps = []
            if 'require' in task_desc.lower() or 'depends' in task_desc.lower():
                # Simple heuristic: tasks mentioned in parentheses are dependencies
                if '(' in task_desc and ')' in task_desc:
                    dep_text = task_desc[task_desc.find('(')+1:task_desc.find(')')]
                    deps = [d.strip() for d in dep_text.split(',')]
            
            dependencies.append({
                "order": i,
                "name": task_desc,
                "dependencies": deps
            })
    
    return dependencies


def build_dependency_graph(dependencies: list) -> dict:
    """
    Build a dependency graph from extracted dependencies.
    
    Returns:
        dict: Mapping of task to its dependencies and dependents
    """
    graph = {dep["name"]: {
        "dependencies": dep.get("dependencies", []),
        "dependents": [],
        "order": dep.get("order", 0)
    } for dep in dependencies}
    
    # Add reverse dependencies (dependents)
    for task_name, info in graph.items():
        for dep in info["dependencies"]:
            if dep in graph:
                graph[dep]["dependents"].append(task_name)
    
    return graph


def create_subtask_with_dependencies(parent_id: str, task_name: str, dependencies: list, order: int) -> dict:
    """
    Create a subtask record with dependency tracking, inputs, and outputs.
    
    Args:
        parent_id: Parent task ID
        task_name: Name/description of subtask
        dependencies: List of task names this depends on
        order: Execution order
    
    Returns:
        dict: Subtask record with required_inputs and outputs
    """
    return {
        "subtask_id": create_subtask_id(parent_id),
        "input": task_name,
        "dependencies": dependencies,
        "execution_order": order,
        "required_inputs": dependencies if dependencies else [],
        "outputs": [f"output_{order}"],
        "subtasks": []
    }


def extract_response_content(response_obj):
    """
    Extract the actual content/output from an LLM response object.
    Handles OpenAI-like response format.
    
    Args:
        response_obj: Response dict from LLM
    
    Returns:
        str: The extracted content, or empty string if not found
    """
    if not response_obj or not isinstance(response_obj, dict):
        return ""
    
    # Standard OpenAI-like response format
    if "choices" in response_obj and isinstance(response_obj["choices"], list):
        if len(response_obj["choices"]) > 0:
            choice = response_obj["choices"][0]
            if "message" in choice and isinstance(choice["message"], dict):
                return choice["message"].get("content", "")
    
    return ""


def build_dd_structure(sample_request: dict) -> dict:
    """
    Build a dependency-driven subtask structure from a sample request.
    
    Args:
        sample_request: Raw sample request from sample_requests/
    
    Returns:
        dict: Task with DD subtask structure (NO complexity_score, empty subtasks)
    """
    # Extract response content from sample request
    response_obj = sample_request.get("response", {})
    task_input = extract_response_content(response_obj)
    
    # Generate task ID
    task_id = generate_base_id()
    
    # Extract dependencies from task description
    dependencies = extract_dependencies_from_task(task_input)
    
    if not dependencies:
        # No dependencies found, but still strip complexity_score
        return {
            "task_id": task_id,
            "input": task_input,
            "required_inputs": [],  # Root task has no required inputs
            "outputs": ["result"],  # Depth-0 always outputs "result"
            "subtasks": [],  # Always empty in DD structure
            "dependency_structure": {
                "type": "dependency_driven",
                "graph": {},
                "total_subtasks": 0
            }
        }
    
    # Build dependency graph
    dep_graph = build_dependency_graph(dependencies)
    
    # Create subtasks with dependency info
    subtasks = []
    for task_name, graph_info in dep_graph.items():
        subtask = create_subtask_with_dependencies(
            task_id,
            task_name,
            graph_info["dependencies"],
            graph_info["order"]
        )
        subtasks.append(subtask)
    
    # Return task with DD structure (NO complexity_score - we've dropped it entirely)
    return {
        "task_id": task_id,
        "input": task_input,
        "required_inputs": [],  # Root task has no required inputs
        "outputs": ["result"],  # Depth-0 always outputs "result"
        "subtasks": [],  # Always empty in DD structure
        "dependency_structure": {
            "type": "dependency_driven",
            "graph": dep_graph,
            "total_subtasks": len(subtasks)
        }
    }


def convert_to_dd_structure(sample_file_path: str, output_dirs: list = None) -> tuple:
    """
    Convert a sample request to dependency-driven structure.
    Saves to multiple output directories.
    
    Args:
        sample_file_path: Path to sample request JSON
        output_dirs: List of directories to save DD request to (defaults to both dd_requests and dd_requests_v2)
    
    Returns:
        tuple: (success: bool, output_paths: list of str or None)
    """
    if output_dirs is None:
        output_dirs = [DD_REQUESTS_DIR, DD_REQUESTS_V2_DIR]
    
    try:
        with open(sample_file_path, "r", encoding="utf-8") as f:
            sample_request = json.load(f)
        
        # Build DD structure
        dd_task = build_dd_structure(sample_request)
        
        # Save to all output directories
        output_paths = []
        for output_dir in output_dirs:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, os.path.basename(sample_file_path))
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(dd_task, f, ensure_ascii=False, indent=2)
            
            output_paths.append(output_path)
        
        return True, output_paths
    
    except Exception as e:
        print(f"Error converting {sample_file_path}: {e}")
        return False, None


def convert_all_to_dd(sample_dir: str = SAMPLE_DIR, output_dirs: list = None) -> list:
    """
    Convert all sample requests to dependency-driven structure.
    Saves to both dd_requests and dd_requests_v2 directories.
    
    Args:
        sample_dir: Path to sample_requests directory
        output_dirs: List of output directories (defaults to both dd_requests and dd_requests_v2)
    
    Returns:
        list: Results of conversions
    """
    if output_dirs is None:
        output_dirs = [DD_REQUESTS_DIR, DD_REQUESTS_V2_DIR]
    
    if not os.path.exists(sample_dir):
        print(f"Sample requests directory not found: {sample_dir}")
        return []
    
    json_files = glob.glob(os.path.join(sample_dir, "*.json"))
    if not json_files:
        print(f"No JSON files found in {sample_dir}")
        return []
    
    results = []
    converted_count = 0
    skipped_count = 0
    
    print("=" * 60)
    print("CONVERTING TO DEPENDENCY-DRIVEN STRUCTURE")
    print("=" * 60)
    print(f"Output directories: {', '.join([os.path.basename(d) for d in output_dirs])}")
    print("=" * 60)
    
    for sample_file in sorted(json_files):
        filename = os.path.basename(sample_file)
        
        # Convert the file (overwrite if exists)
        print(f"Converting {filename}...", end=" ", flush=True)
        success, output_paths = convert_to_dd_structure(sample_file, output_dirs)
        
        if success:
            print(f"[OK] → {len(output_paths)} dirs")
            results.append((sample_file, True, output_paths))
            converted_count += 1
        else:
            print("[FAILED]")
            results.append((sample_file, False, None))
    
    print(f"\n{'='*60}")
    print(f"Results: {converted_count} converted, {skipped_count} skipped")
    print(f"Output directories:")
    for output_dir in output_dirs:
        print(f"  - {output_dir}")
    print(f"{'='*60}")
    
    return results


if __name__ == "__main__":
    convert_all_to_dd()
