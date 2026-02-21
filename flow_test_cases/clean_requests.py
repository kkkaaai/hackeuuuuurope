import os
import sys
import json
import glob
from pathlib import Path

# Add parent directory to path
SCRIPT_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.dirname(SCRIPT_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from task_id_manager import generate_base_id

SAMPLE_DIR = os.path.join(BASE_DIR, "sample_requests")
CLEANED_DIR = os.path.join(SCRIPT_DIR, "cleaned_requests")


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


def clean_request(request_file_path, output_dir=CLEANED_DIR):
    """
    Create a cleaned version of a request file.
    
    Args:
        request_file_path: Path to the request JSON file in sample_requests
        output_dir: Directory to save cleaned request to
    
    Returns:
        tuple: (success: bool, task_id: str or None, output_path: str or None)
    """
    try:
        with open(request_file_path, "r", encoding="utf-8") as f:
            request_data = json.load(f)
        
        # Extract response content
        response_obj = request_data.get("response", {})
        response_content = extract_response_content(response_obj)
        
        if not response_content:
            return False, None, None
        
        # Generate unique task ID
        task_id = generate_base_id()
        
        # Create cleaned request
        cleaned_request = {
            "task_id": task_id,
            "input": response_content,
            "complexity_score": None,
            "eval_gen": 1,
            "subtasks": []
        }
        
        # Save to cleaned_requests folder
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, os.path.basename(request_file_path))
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_request, f, ensure_ascii=False, indent=2)
        
        return True, task_id, output_path
    
    except Exception as e:
        print(f"Error cleaning {request_file_path}: {e}")
        return False, None, None


def clean_all_requests(sample_dir=SAMPLE_DIR, output_dir=CLEANED_DIR):
    """
    Clean all requests in sample_requests that don't already have a cleaned version.
    
    Args:
        sample_dir: Path to the sample_requests directory
        output_dir: Path to the cleaned_requests directory
    
    Returns:
        list: Tuples of (file_path, success, task_id)
    """
    if not os.path.exists(sample_dir):
        print(f"Sample directory not found: {sample_dir}")
        return []
    
    json_files = glob.glob(os.path.join(sample_dir, "*.json"))
    if not json_files:
        print(f"No JSON files found in {sample_dir}")
        return []
    
    results = []
    cleaned_count = 0
    skipped_count = 0
    
    for request_file in sorted(json_files):
        filename = os.path.basename(request_file)
        cleaned_file = os.path.join(output_dir, filename)
        
        # Skip if already cleaned
        if os.path.exists(cleaned_file):
            print(f"Skipping {filename} (already cleaned)")
            results.append((request_file, False, None, "already_cleaned"))
            skipped_count += 1
            continue
        
        # Clean the request
        print(f"Cleaning {filename}...", end=" ", flush=True)
        success, task_id, output_path = clean_request(request_file, output_dir)
        
        if success:
            print(f"[OK] Task ID: {task_id}")
            results.append((request_file, True, task_id, output_path))
            cleaned_count += 1
        else:
            print("[FAILED]")
            results.append((request_file, False, None, None))
    
    print(f"\n{'='*60}")
    print(f"Results: {cleaned_count} cleaned, {skipped_count} skipped")
    print(f"{'='*60}")
    
    return results


if __name__ == "__main__":
    clean_all_requests()
