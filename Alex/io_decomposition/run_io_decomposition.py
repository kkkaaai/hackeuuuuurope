"""
Run parallel decomposition using IO-driven execution planning engine.
This version uses input/output dependencies and ordered execution steps instead of complexity analysis.

Usage: python run_io_decomposition.py [threshold] [num_workers] [filename]
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

from staged_decomposition.parallel_recursive_decomposer import process_request_file_parallel
from complexity_evaluator import CLEANED_DIR
from task_id_manager import get_depth


def is_valid_starting_task(file_path):
    """Check if file contains a task with depth 0 and null complexity."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        task_id = data.get("task_id", "")
        complexity = data.get("complexity_score")
        depth = get_depth(task_id)
        
        # Must be depth 0 and have no complexity score yet
        return depth == 0 and complexity is None
    except Exception as e:
        return False


def find_first_valid_task():
    """Find first file with depth 0 task and null complexity."""
    all_files = sorted(glob.glob(os.path.join(CLEANED_DIR, "*.json")))
    
    if not all_files:
        print(f"No JSON files found in {CLEANED_DIR}")
        return None
    
    for file_path in all_files:
        if is_valid_starting_task(file_path):
            return file_path
    
    return None


def main():
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
    
    # Use specified file or find first valid task
    if len(sys.argv) > 3:
        filename = sys.argv[3]
        request_file = os.path.join(CLEANED_DIR, filename)
        if not os.path.exists(request_file):
            print(f"File not found: {request_file}")
            sys.exit(1)
    else:
        request_file = find_first_valid_task()
        if not request_file:
            print(f"No valid starting task found (need depth 0 with null complexity)")
            print(f"Searched in: {CLEANED_DIR}")
            sys.exit(1)
    
    print(f"Starting IO-driven decomposition on single file")
    print(f"  File: {os.path.basename(request_file)}")
    print(f"  Threshold: {threshold}")
    print(f"  Workers: {workers}\n")
    
    result = process_request_file_parallel(
        request_file,
        complexity_threshold=threshold,
        max_workers=workers
    )
    
    if result:
        print(f"Result: {result}")
    else:
        print(f"No result")

if __name__ == "__main__":
    main()
