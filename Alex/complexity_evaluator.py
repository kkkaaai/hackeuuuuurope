import os
import re
import json
import glob
import time
from pathlib import Path
from openai import OpenAI

from task_id_manager import generate_base_id


MODEL = "qwen/qwen3-235b-a22b"

BASE_DIR = os.path.dirname(__file__)
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_requests")
CLEANED_DIR = os.path.join(BASE_DIR, "cleaned_requests")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
EVAL_ENGINE_PATH = os.path.join(BASE_DIR, "evaluation_engine.json")

EVAL_GEN = 2  # Generation 2: Task Decomposition Stage Evaluator
API_RATE_LIMIT_SECONDS = 5
_last_api_call_time = 0


def _load_evaluation_engine(path: str, eval_gen: int) -> str:
    """
    Load the evaluation prompt template from evaluation_engine.json.
    
    Args:
        path: Path to evaluation_engine.json
        eval_gen: The evaluation generation number to load
    
    Returns:
        str: The prompt template for the given generation
    
    Raises:
        FileNotFoundError: If evaluation_engine.json is not found
        KeyError: If the evaluation generation is not found
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"evaluation_engine.json not found at {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        engine_data = json.load(f)
    
    eval_key = str(eval_gen)
    if eval_key not in engine_data.get("evaluations", {}):        raise KeyError(f"Evaluation generation {eval_gen} not found in evaluation_engine.json")
    
    return engine_data["evaluations"][eval_key]["prompt_template"]


# Load the complexity prompt template from evaluation_engine.json
try:
    COMPLEXITY_PROMPT_TEMPLATE = _load_evaluation_engine(EVAL_ENGINE_PATH, EVAL_GEN)
except (FileNotFoundError, KeyError) as e:
    print(f"Warning: Could not load evaluation engine: {e}")
    COMPLEXITY_PROMPT_TEMPLATE = "ERROR: Could not load prompt template"


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


def evaluate_complexity(task_input: str, client: OpenAI = None):
    """
    Evaluate task complexity using generation 2 (decomposition depth evaluator).
    
    Args:
        task_input: The task description to evaluate
        client: Optional OpenAI client
    
    Returns:
        dict with 'score', 'decomposition_depth', 'justification'
    """
    global _last_api_call_time
    
    if client is None:
        client = _get_client()
    
    # Rate limiting
    elapsed = time.time() - _last_api_call_time
    if elapsed < API_RATE_LIMIT_SECONDS:
        time.sleep(API_RATE_LIMIT_SECONDS - elapsed)
    
    prompt = COMPLEXITY_PROMPT_TEMPLATE.replace("{INPUT_PROMPT}", task_input).replace("{EVAL_GEN}", str(EVAL_GEN))
    
    try:
        _last_api_call_time = time.time()
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            top_p=0.9,
            max_tokens=500,
            stream=False,
        )
        
        raw_response = completion.choices[0].message.content if completion.choices else ""
        
        # Parse response for complexity score and decomposition depth
        result = {"score": None, "decomposition_depth": None, "raw_response": raw_response}
        
        # Extract Complexity Score
        for line in raw_response.split("\n"):
            if "Complexity Score:" in line:
                try:
                    score_str = line.split("Complexity Score:")[1].strip().split()[0]
                    result["score"] = int(score_str)
                except (ValueError, IndexError):
                    pass
            elif "Decomposition Depth:" in line:
                try:
                    depth_str = line.split("Decomposition Depth:")[1].strip().split()[0]
                    result["decomposition_depth"] = int(depth_str)
                except (ValueError, IndexError):
                    pass
        
        return result
        
    except Exception as e:
        return {"score": None, "decomposition_depth": None, "error": str(e)}
