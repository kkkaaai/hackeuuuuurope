"""
Recursive IO-Driven Task Decomposer
Recursively decomposes each requirement into concrete steps showing the path from current state to desired state.
"""

import os
import sys
import re
import json
import time
from pathlib import Path
from openai import OpenAI

# Add parent directory to path to enable relative imports
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from complexity_evaluator import (
    evaluate_complexity,
    SAMPLE_DIR,
    CLEANED_DIR,
    LOGS_DIR,
    EVAL_GEN
)
from task_id_manager import create_subtask_id
from model_tiers import get_model_for_complexity, get_tier_info, get_model_endpoint


MODEL = "qwen/qwen3-235b-a22b"
API_RATE_LIMIT_SECONDS = 5
_last_api_call_time = 0


REQUIREMENT_DECOMPOSITION_PROMPT = """You are a requirement-to-steps decomposer.

Given a requirement, identify the concrete steps needed to transform from the CURRENT STATE to the DESIRED STATE.

Each step must:
1) Have a clear starting point (what state we're in before this step)
2) Have a clear action (what we do in this step)
3) Have a clear ending point (what state we're in after this step)
4) Reference what inputs/resources are needed
5) Reference what output is produced

Format each requirement breakdown as:

REQUIREMENT: [the requirement]

CURRENT STATE: [where we start]
DESIRED STATE: [where we need to be]

STEPS TO ACHIEVE:
1. [Step 1 description - what we do and what changes]
2. [Step 2 description - what we do and what changes]
3. [Continue for each step needed]

KEY DEPENDENCIES:
- [dependency 1]
- [dependency 2]

VERIFICATION:
- [How do we know this requirement is satisfied?]

------------------------------------------------------------------

REQUIREMENTS TO DECOMPOSE:

{REQUIREMENTS_LIST}"""


def _load_key_from_dotenv(path: Path):
    """Load API key from .env file."""
    if not path.exists():
        return None
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k in ("NVAPI_KEY", "NVIDIA_API_KEY"):
            return v
    return None


def _get_api_key():
    """Get NVIDIA API key from environment or .env file."""
    api_key = os.getenv("NVAPI_KEY") or os.getenv("NVIDIA_API_KEY")
    if not api_key:
        current = Path(__file__).resolve().parent
        for p in [current] + list(current.parents):
            env_path = p / ".env"
            api_key = _load_key_from_dotenv(env_path)
            if api_key:
                break
    return api_key


def _get_client():
    """Create and return OpenAI client configured for NVIDIA API."""
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("Please set NVAPI_KEY or NVIDIA_API_KEY environment variable, or add it to a .env file")
    
    return OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )


def decompose_requirements_to_steps(requirements_list: list, client: OpenAI = None, complexity_score: float = None, max_depth: int = None) -> dict:
    """
    Recursively decompose each requirement into concrete steps showing the transformation path.
    
    Args:
        requirements_list: List of requirement strings
        client: Optional OpenAI client
        complexity_score: Task complexity score for model selection
        max_depth: Maximum recursion depth (None = infinite)
    
    Returns:
        dict with step breakdowns for each requirement
    """
    global _last_api_call_time
    
    if client is None:
        client = _get_client()
    
    if not requirements_list:
        return {
            "requirements": [],
            "decompositions": {},
            "error": "No requirements provided"
        }
    
    # Select model based on complexity
    model_key = get_model_for_complexity(complexity_score) if complexity_score is not None else "AI1"
    selected_model = get_model_endpoint(model_key)
    tier_info = get_tier_info(complexity_score) if complexity_score is not None else None
    
    # Format requirements for prompt
    requirements_text = ""
    for i, req in enumerate(requirements_list, 1):
        requirements_text += f"{i}. {req}\n"
    
    # Build prompt
    full_prompt = REQUIREMENT_DECOMPOSITION_PROMPT.replace("{REQUIREMENTS_LIST}", requirements_text)
    
    # Rate limiting
    elapsed = time.time() - _last_api_call_time
    if elapsed < API_RATE_LIMIT_SECONDS:
        time.sleep(API_RATE_LIMIT_SECONDS - elapsed)
    
    try:
        _last_api_call_time = time.time()
        completion = client.chat.completions.create(
            model=selected_model,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.3,
            top_p=0.9,
            max_tokens=4000,
            stream=False,
        )
        
        raw_response = completion.choices[0].message.content if completion.choices else ""
        
        # Parse the decompositions
        decompositions = _parse_requirement_decompositions(raw_response)
        
        return {
            "requirements": requirements_list,
            "decompositions": decompositions,
            "raw_response": raw_response,
            "error": None,
            "model_used": model_key,
            "model_endpoint": selected_model,
            "tier_info": tier_info,
            "max_depth": max_depth,
            "depth_reached": 1
        }
        
    except Exception as e:
        return {
            "requirements": requirements_list,
            "decompositions": {},
            "raw_response": None,
            "error": str(e),
            "model_used": model_key,
            "model_endpoint": selected_model,
            "tier_info": tier_info,
            "max_depth": max_depth,
            "depth_reached": 0
        }


def _parse_requirement_decompositions(response_text: str) -> dict:
    """
    Parse requirement decompositions from LLM response.
    
    Returns:
        dict mapping requirement to its decomposition details
    """
    if not response_text:
        return {}
    
    decompositions = {}
    current_requirement = None
    current_section = None
    current_content = []
    
    lines = response_text.split('\n')
    
    for line in lines:
        stripped = line.strip()
        
        # Detect requirement header
        if stripped.lower().startswith('requirement:'):
            if current_requirement and current_content:
                decompositions[current_requirement] = {
                    "content": '\n'.join(current_content)
                }
            current_requirement = stripped.replace('REQUIREMENT:', '').replace('requirement:', '').strip()
            current_content = []
            current_section = None
            continue
        
        # Detect section headers
        if stripped.lower().startswith('current state:'):
            current_section = 'current_state'
            current_content.append(line)
            continue
        elif stripped.lower().startswith('desired state:'):
            current_section = 'desired_state'
            current_content.append(line)
            continue
        elif stripped.lower().startswith('steps to achieve:'):
            current_section = 'steps'
            current_content.append(line)
            continue
        elif stripped.lower().startswith('key dependencies:'):
            current_section = 'dependencies'
            current_content.append(line)
            continue
        elif stripped.lower().startswith('verification:'):
            current_section = 'verification'
            current_content.append(line)
            continue
        
        # Collect content
        if current_requirement and line:
            current_content.append(line)
    
    # Save last requirement
    if current_requirement and current_content:
        decompositions[current_requirement] = {
            "content": '\n'.join(current_content)
        }
    
    return decompositions


def restructure_task_with_requirement_steps(task_id: str, task_input: str, complexity_score: float, 
                                           requirements: list, decompositions: dict) -> dict:
    """
    Restructure task with requirement-to-steps decompositions.
    
    Args:
        task_id: Task identifier
        task_input: Task description
        complexity_score: Complexity score
        requirements: List of requirements
        decompositions: Decompositions dict from decompose_requirements_to_steps
    
    Returns:
        Restructured task record
    """
    return {
        "task_id": task_id,
        "input": task_input,
        "complexity_score": complexity_score,
        "requirements": {
            "total": len(requirements),
            "items": requirements
        },
        "requirement_decompositions": {
            "total_decomposed": len(decompositions),
            "decompositions": decompositions
        },
        "subtasks": [],
        "eval_gen": 4  # Requirement-driven generation marker
    }
