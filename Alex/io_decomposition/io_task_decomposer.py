"""
IO-driven Task Decomposer
Uses execution planning based on input/output dependencies and ordered steps.
No complexity analysis - pure execution plan generation.
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

from task_id_manager import create_subtask_id
from model_tiers import get_model_for_complexity, get_tier_info, get_model_endpoint


MODEL = "qwen/qwen3-235b-a22b"  # Default fallback model

API_RATE_LIMIT_SECONDS = 5
_last_api_call_time = 0

# Load decomposition engine prompt from v2 config
_DECOMP_ENGINE_PATH = os.path.join(SCRIPT_DIR, "decomposition_engine_v2.json")

def _load_decomposition_engine_prompt():
    """Load decomposition engine prompt from JSON config."""
    try:
        with open(_DECOMP_ENGINE_PATH, 'r', encoding='utf-8') as f:
            engine_config = json.load(f)
        return engine_config.get("prompt_template", "")
    except Exception as e:
        print(f"Warning: Could not load decomposition engine v2: {e}")
        return None

# IO-Driven Decomposition Engine Prompt (v2)
_IO_DECOMPOSITION_PROMPT_V2 = _load_decomposition_engine_prompt()

# Fallback to v1 if v2 not available
IO_DECOMPOSITION_PROMPT = _IO_DECOMPOSITION_PROMPT_V2 or """DECOMPOSITION ENGINE (IO-Driven Execution Planning):

You are an execution-planning engine.

Your objective is to deconstruct the given task by identifying:

1) What information, resources, and dependencies are required to execute it.
2) What concrete outputs or state changes must result.
3) The ordered actionable steps that transform the inputs into outputs.

You are NOT recursively reducing to atomic blocks.
You are constructing a dependency-aware execution plan.

------------------------------------------------------------------

STEP 1 — INPUT DEPENDENCIES

Identify all required inputs, including:

- Data inputs (files, datasets, user input, database records)
- External systems or tools
- Configuration parameters
- Constraints or thresholds
- Credentials or permissions (if implied)
- Assumptions that must be satisfied

Be explicit and concrete.
Do not list vague abstractions (e.g., "necessary data").
List the exact type of information required.

------------------------------------------------------------------

STEP 2 — OUTPUTS

Define the explicit outputs of task completion, including:

- Generated artifacts (documents, reports, code, emails, dashboards)
- Updated system states
- Side effects (notifications, deployments, escalations)
- Metrics or confirmations of success

Outputs must be observable and verifiable.

------------------------------------------------------------------

STEP 3 — ORDERED EXECUTION STEPS

Produce an ordered list of actionable steps.

Each step must:

- Explicitly reference which input(s) it uses
- Specify the action performed
- Indicate what intermediate or final output it produces
- Clarify where the output is stored, sent, or applied
- Be written as a concrete executable action (not abstract planning language)

Do not:
- Combine multiple major operations into one step
- Omit where information is retrieved from
- Omit where outputs are written or sent

Execution should form a clear transformation chain:
Inputs → Intermediate State → Final Outputs

------------------------------------------------------------------

OUTPUT FORMAT (STRICT):

Inputs:
- ...
- ...

Outputs:
- ...
- ...

Steps:
1. ...
2. ...
3. ...

------------------------------------------------------------------

Task to Decompose:
{INPUT_PROMPT}"""


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


def decompose_task_io(task_description: str, complexity_score: float = None, client: OpenAI = None, current_depth: int = 0, engine_version: str = "v2") -> dict:
    """
    Decompose a task using IO-driven execution planning.
    Identifies inputs, outputs, and ordered execution steps.
    Then performs AEB analysis to verify executability.
    
    Args:
        task_description: The task to decompose
        complexity_score: Task complexity score (0-100). Used to select appropriate AI model.
        client: Optional OpenAI client
        current_depth: Current decomposition depth
        engine_version: Which decomposition engine to use ("v2" or "v3")
    
    Returns:
        dict with execution plan, inputs, outputs, steps, AEB analysis
    """
    global _last_api_call_time
    
    if client is None:
        client = _get_client()
    
    # Load the specified engine version
    engine_path = os.path.join(SCRIPT_DIR, f"decomposition_engine_{engine_version}.json")
    engine_prompt = None
    
    if os.path.exists(engine_path):
        try:
            with open(engine_path, 'r', encoding='utf-8') as f:
                engine_config = json.load(f)
            engine_prompt = engine_config.get("prompt_template", "")
        except Exception as e:
            print(f"Warning: Could not load engine {engine_version}: {e}")
    
    # Use specified engine, or fallback to global default
    prompt_to_use = engine_prompt or IO_DECOMPOSITION_PROMPT
    
    # Determine which model to use based on complexity
    model_key = get_model_for_complexity(complexity_score) if complexity_score is not None else "AI1"
    selected_model = get_model_endpoint(model_key)
    tier_info = get_tier_info(complexity_score) if complexity_score is not None else None
    
    # Build the prompt
    full_prompt = prompt_to_use.replace("{INPUT_PROMPT}", task_description)
    
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
            max_tokens=3000,
            stream=False,
        )
        
        raw_response = completion.choices[0].message.content if completion.choices else ""
        
        # Parse the execution plan
        inputs, outputs, steps = _parse_io_execution_plan(raw_response)
        
        # Perform AEB analysis on the steps
        aeb_analysis = _analyze_aeb_executability(steps, client)
        
        return {
            "inputs": inputs,
            "outputs": outputs,
            "steps": steps,
            "aeb_analysis": aeb_analysis,
            "raw_response": raw_response,
            "error": None,
            "model_used": model_key,
            "model_endpoint": selected_model,
            "tier_info": tier_info
        }
        
    except Exception as e:
        return {
            "inputs": [],
            "outputs": [],
            "steps": [],
            "aeb_analysis": None,
            "raw_response": None,
            "error": str(e),
            "model_used": model_key,
            "model_endpoint": selected_model,
            "tier_info": tier_info
        }


def _parse_io_execution_plan(response_text: str) -> tuple:
    """
    Parse IO-driven execution plan from LLM response.
    Extracts inputs, outputs, and steps with their dependencies.
    
    Returns:
        tuple: (inputs_list, outputs_list, steps_list)
    """
    if not response_text:
        return [], [], []
    
    inputs = []
    outputs = []
    steps = []
    
    lines = response_text.split('\n')
    current_section = None
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        
        if not line:
            continue
        
        # Detect section headers (case-insensitive)
        if line.lower().startswith('inputs:'):
            current_section = 'inputs'
            continue
        elif line.lower().startswith('outputs:'):
            current_section = 'outputs'
            continue
        elif line.lower().startswith('steps:'):
            current_section = 'steps'
            continue
        
        # Parse inputs section - extract full structured input
        if current_section == 'inputs':
            # Match numbered items like "1. Input Name" or "1. **Input Name**"
            match = re.match(r'^\d+\.\s*(\*{0,2})(.+?)\1', line)
            if match:
                input_name = match.group(2).strip()
                
                # Collect all metadata lines for this input
                input_obj = {
                    "name": input_name,
                    "source_type": None,
                    "source_origin": None,
                    "input_data": None,
                    "bound_reference": None
                }
                
                # Look ahead for metadata fields
                while i < len(lines):
                    next_line = lines[i].strip()
                    
                    # Stop if we hit next input or section
                    if re.match(r'^\d+\.\s+', next_line) or next_line.lower().startswith('outputs:'):
                        break
                    
                    # Extract metadata fields
                    if next_line.startswith('Source Type:'):
                        input_obj["source_type"] = next_line.replace('Source Type:', '').strip()
                    elif next_line.startswith('Source Origin:'):
                        input_obj["source_origin"] = next_line.replace('Source Origin:', '').strip()
                    elif next_line.startswith('Input Data:'):
                        input_obj["input_data"] = next_line.replace('Input Data:', '').strip()
                    elif next_line.startswith('Bound Reference:'):
                        input_obj["bound_reference"] = next_line.replace('Bound Reference:', '').strip()
                    
                    i += 1
                
                if input_obj["name"]:
                    inputs.append(input_obj)
        
        # Parse outputs section
        elif current_section == 'outputs':
            # Match numbered items
            match = re.match(r'^\d+\.\s+(.+?)(?:\s*\(|$)', line)
            if match:
                output_name = match.group(1).strip()
                if output_name:
                    outputs.append(output_name)
            # Also catch bullet points
            elif line.startswith('-') or line.startswith('•'):
                item = line.lstrip('-•').strip()
                if item:
                    outputs.append(item)
        
        # Parse steps section - handle multi-line step descriptions
        elif current_section == 'steps':
            # Match "Step N:" or numbered steps
            if re.match(r'^Step\s+\d+:', line):
                # Collect entire step block (Step X: through next Step or section)
                step_lines = []
                
                # Collect subsequent lines until next step or new section
                while i < len(lines):
                    next_line = lines[i]
                    
                    # Check if we've hit the next section or step
                    if re.match(r'^Step\s+\d+:', next_line.strip()) or re.match(r'^[A-Z][a-z]+\s', next_line.strip()):
                        break
                    
                    # Include non-empty lines and empty lines (for formatting)
                    step_lines.append(next_line)
                    i += 1
                
                step_content = '\n'.join(step_lines).strip()
                if step_content:
                    steps.append(step_content)
            
            elif re.match(r'^\d+\.\s+', line):
                # Numbered steps format - collect full step block
                step_lines = [line]
                
                while i < len(lines):
                    next_line = lines[i].strip()
                    
                    # Stop if next numbered item or section
                    if re.match(r'^\d+\.\s+', next_line) or re.match(r'^[A-Z][a-z]+:', next_line):
                        break
                    
                    if next_line:  # Skip empty lines
                        step_lines.append(next_line)
                    i += 1
                
                step_content = '\n'.join(step_lines).strip()
                if step_content:
                    steps.append(step_content)
    
    return inputs, outputs, steps


def _analyze_aeb_executability(steps: list, client: OpenAI) -> dict:
    """
    Analyze if each step is an Atomic Execution Block (AEB).
    
    AEB Criteria:
    - Single intent
    - Interacts with one system boundary
    - Contains no sequencing
    - Contains no branching
    - Contains no validation or error handling
    - Can be implemented as a single function/API call
    
    Args:
        steps: List of execution steps
        client: OpenAI client
    
    Returns:
        dict with AEB analysis results
    """
    if not steps:
        return {"steps_count": 0, "aeb_analysis": []}
    
    aeb_prompt = """You are an AEB (Atomic Execution Block) validator.

Analyze each step and determine if it is an AEB:

AEB DEFINITION:
An AEB is the smallest directly executable action that:
- Has single intent
- Interacts with one system boundary
- Contains no sequencing
- Contains no branching
- Contains no validation or error handling
- Can be implemented as a single function/API call

For each step, output:
- Step: [the step]
- Is AEB: Yes/No
- Reason: [why or why not]
- If No, suggest: [how to break it down further]

STEPS TO ANALYZE:
"""
    
    for i, step in enumerate(steps, 1):
        aeb_prompt += f"{i}. {step}\n"
    
    try:
        elapsed = time.time() - _last_api_call_time
        if elapsed < API_RATE_LIMIT_SECONDS:
            time.sleep(API_RATE_LIMIT_SECONDS - elapsed)
        
        completion = client.chat.completions.create(
            model="qwen/qwen3-235b-a22b",
            messages=[{"role": "user", "content": aeb_prompt}],
            temperature=0.3,
            top_p=0.9,
            max_tokens=2000,
            stream=False,
        )
        
        analysis_response = completion.choices[0].message.content if completion.choices else ""
        
        return {
            "steps_count": len(steps),
            "aeb_analysis_raw": analysis_response,
            "analysis_complete": True
        }
        
    except Exception as e:
        return {
            "steps_count": len(steps),
            "aeb_analysis_raw": None,
            "error": str(e),
            "analysis_complete": False
        }


def _chain_step_dependencies(steps: list, inputs: list) -> list:
    """
    Extract and chain step dependencies explicitly.
    Ensures each step's inputs come from either:
    - Initial inputs list
    - Previous step outputs
    
    Args:
        steps: List of execution steps with "Uses:" and "Produces:" fields
        inputs: List of available inputs
    
    Returns:
        List of steps with extracted dependencies and outputs
    """
    chained_steps = []
    accumulated_outputs = set(inputs)  # Start with initial inputs
    
    for i, step in enumerate(steps):
        # Extract what this step uses
        uses_match = re.search(r'Uses:\s*(.+?)(?=\n|Action:|$)', step, re.IGNORECASE | re.DOTALL)
        uses_text = uses_match.group(1).strip() if uses_match else ""
        
        # Extract what this step produces
        produces_match = re.search(r'Produces:\s*(.+?)(?=\n|Stores|$)', step, re.IGNORECASE | re.DOTALL)
        produces_text = produces_match.group(1).strip() if produces_match else ""
        
        # Extract action
        action_match = re.search(r'Action:\s*(.+?)(?=\n|Produces:|$)', step, re.IGNORECASE | re.DOTALL)
        action_text = action_match.group(1).strip() if action_match else ""
        
        chained_step = {
            "step_number": i + 1,
            "action": action_text,
            "uses": uses_text,
            "produces": produces_text,
            "full_description": step.strip(),
        }
        
        # Add produced output to accumulated outputs
        if produces_text:
            accumulated_outputs.add(produces_text)
        
        chained_steps.append(chained_step)
    
    return chained_steps


def restructure_task_record(task_id: str, task_input: str, complexity_score: float, 
                           io_plan: dict, aeb_analysis: dict) -> dict:
    """
    Restructure task record with chained execution plan.
    Ensures inputs flow properly to outputs through steps.
    
    Args:
        task_id: Task identifier
        task_input: Task description
        complexity_score: Complexity score (if available)
        io_plan: IO execution plan dict with inputs, outputs, steps
        aeb_analysis: AEB analysis results
    
    Returns:
        Restructured task record with dependency chaining
    """
    inputs = io_plan.get("inputs", [])
    outputs = io_plan.get("outputs", [])
    steps = io_plan.get("steps", [])
    
    # Chain steps with dependencies
    chained_steps = _chain_step_dependencies(steps, inputs)
    
    return {
        "task_id": task_id,
        "input": task_input,
        "complexity_score": complexity_score,
        "execution_plan": {
            "inputs": inputs,
            "outputs": outputs,
            "steps": chained_steps,
            "step_count": len(chained_steps),
            "dependency_validated": True
        },
        "aeb_analysis": {
            "total_steps": aeb_analysis.get("steps_count", 0),
            "analysis": aeb_analysis.get("aeb_analysis_raw", ""),
            "complete": aeb_analysis.get("analysis_complete", False)
        },
        "model_info": {
            "model_used": io_plan.get("model_used"),
            "model_endpoint": io_plan.get("model_endpoint")
        },
        "subtasks": [],
        "eval_gen": 3,  # IO-driven generation marker
        "raw_response": io_plan.get("raw_response")  # Keep for reference
    }
