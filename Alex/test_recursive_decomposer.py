#!/usr/bin/env python
"""
Dry-run test for recursive decomposer.
Tests the basic functionality without running actual decomposition.
"""

import json
import sys
import os

from recursive_decomposer import find_first_root_file, CLEANED_DIR
from task_id_manager import get_depth

def test_find_root_file():
    """Test finding the first root file."""
    print("=" * 80)
    print("TEST 1: Find First Root File")
    print("=" * 80)
    print()
    
    root_file = find_first_root_file(CLEANED_DIR)
    
    if not root_file:
        print("ERROR: No root file found")
        return False
    
    print(f"Found: {root_file}")
    print(f"Filename: {os.path.basename(root_file)}")
    print()
    
    return True, root_file


def test_load_and_inspect(root_file):
    """Test loading and inspecting the root file."""
    print("=" * 80)
    print("TEST 2: Load and Inspect File")
    print("=" * 80)
    print()
    
    try:
        with open(root_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load file: {e}")
        return False, None
    
    task_id = data.get('task_id')
    complexity = data.get('complexity_score')
    subtasks = data.get('subtasks', [])
    input_text = data.get('input', '')
    eval_gen = data.get('eval_gen')
    
    print(f"Task ID: {task_id}")
    print(f"Task ID Depth: {get_depth(task_id)}")
    print(f"Root Complexity: {complexity}")
    print(f"Eval Generation: {eval_gen}")
    print(f"Current Subtasks: {len(subtasks)}")
    print(f"Input: {input_text[:70]}...")
    print()
    
    return True, data


def test_readiness_for_decomposition(data, threshold=50):
    """Test if file is ready for decomposition."""
    print("=" * 80)
    print(f"TEST 3: Readiness Check (Threshold: {threshold})")
    print("=" * 80)
    print()
    
    complexity = data.get('complexity_score')
    subtasks = data.get('subtasks', [])
    
    checks = {
        'Has complexity score': complexity is not None,
        f'Complexity > threshold ({threshold})': complexity is not None and complexity > threshold,
        'Has no subtasks yet': len(subtasks) == 0,
    }
    
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check}")
        if not passed:
            if check.startswith('Complexity'):
                print(f"       Current complexity: {complexity}")
            elif check.startswith('Has no'):
                print(f"       Current subtasks: {len(subtasks)}")
    
    print()
    
    all_passed = all(checks.values())
    if all_passed:
        print("READY FOR DECOMPOSITION: Yes")
    else:
        print("READY FOR DECOMPOSITION: No")
    
    print()
    return all_passed


def test_complexity_distribution(data):
    """Test current complexity distribution in the file."""
    print("=" * 80)
    print("TEST 4: Complexity Distribution")
    print("=" * 80)
    print()
    
    def collect_all_tasks(task_data, depth=0):
        """Recursively collect all tasks with their depths."""
        tasks = [{
            'task_id': task_data.get('task_id'),
            'complexity': task_data.get('complexity_score'),
            'depth': depth,
            'input': task_data.get('input', '')[:50]
        }]
        
        for subtask in task_data.get('subtasks', []):
            tasks.extend(collect_all_tasks(subtask, depth + 1))
        
        return tasks
    
    all_tasks = collect_all_tasks(data)
    
    print(f"Total tasks in tree: {len(all_tasks)}")
    print()
    
    print("Tasks by depth:")
    for task in all_tasks:
        depth = task['depth']
        task_id = task['task_id']
        complexity = task['complexity']
        prefix = "  " * depth + "|- "
        print(f"{prefix}[{task_id}] (Complexity: {complexity})")
    
    print()
    return all_tasks


def main():
    """Run all tests."""
    print("\n")
    print("*" * 80)
    print("RECURSIVE DECOMPOSER - DRY RUN TEST")
    print("*" * 80)
    print("\n")
    
    # Test 1: Find root file
    result = test_find_root_file()
    if not result or not result[0]:
        print("FAILED at Test 1")
        return False
    
    root_file = result[1]
    
    # Test 2: Load and inspect
    result = test_load_and_inspect(root_file)
    if not result or not result[0]:
        print("FAILED at Test 2")
        return False
    
    data = result[1]
    
    # Test 3: Readiness check
    ready = test_readiness_for_decomposition(data, threshold=50)
    
    # Test 4: Complexity distribution
    all_tasks = test_complexity_distribution(data)
    
    # Summary
    print("=" * 80)
    print("DRY RUN SUMMARY")
    print("=" * 80)
    print()
    print(f"File ready for decomposition: {'YES' if ready else 'NO'}")
    print(f"Current task count: {len(all_tasks)}")
    print()
    
    if ready:
        print("Next step: Run 'python recursive_decomposer.py 50'")
    else:
        print("Cannot proceed with decomposition.")
    
    print("\n")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
