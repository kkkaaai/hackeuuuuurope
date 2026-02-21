"""
Tiered AI model configuration for complexity-based decomposition.
Different models are used based on task complexity levels.
"""

import os
import sys
from pathlib import Path

# Add script directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


# Define AI models for different complexity tiers
# Format: {tier_name: {complexity_range: (min, max], model_name}}

AI_MODELS = {
    "AI1": "qwen/qwen3-235b-a22b",  # Default/fallback model
    "AI2": "deepseek-ai/deepseek-v3.2",  # Premium model for mid-complexity
}

# Complexity tiers and their corresponding models
# Ordered from highest to lowest complexity
COMPLEXITY_TIERS = [
    {"min": 80, "max": 100, "model": "AI2", "description": "Very Complex (80-100)"},
    {"min": 60, "max": 80, "model": "AI1", "description": "Complex (60-80)"},
    {"min": 40, "max": 60, "model": "AI2", "description": "Moderate (40-60)"},
    {"min": 0, "max": 40, "model": "AI1", "description": "Simple (0-40)"},
]


def get_model_for_complexity(complexity_score: float) -> str:
    """
    Get the appropriate AI model name based on complexity score.
    
    Args:
        complexity_score: Task complexity score (0-100)
    
    Returns:
        str: Model name (e.g., "AI1", "AI2")
    """
    for tier in COMPLEXITY_TIERS:
        if tier["min"] <= complexity_score < tier["max"]:
            return tier["model"]
    # Fallback to AI1 if score is at boundary
    return "AI1"


def get_model_endpoint(model_key: str) -> str:
    """
    Get the full model endpoint/identifier.
    
    Args:
        model_key: Model key from AI_MODELS (e.g., "AI1", "AI2")
    
    Returns:
        str: Full model identifier
    """
    return AI_MODELS.get(model_key, AI_MODELS["AI1"])


def get_tier_info(complexity_score: float) -> dict:
    """
    Get detailed tier information for a complexity score.
    
    Args:
        complexity_score: Task complexity score (0-100)
    
    Returns:
        dict: Tier information including model, description, min/max
    """
    for tier in COMPLEXITY_TIERS:
        if tier["min"] <= complexity_score < tier["max"]:
            return {
                **tier,
                "model_endpoint": get_model_endpoint(tier["model"]),
                "complexity_score": complexity_score
            }
    # Fallback
    fallback = COMPLEXITY_TIERS[-1]
    return {
        **fallback,
        "model_endpoint": get_model_endpoint(fallback["model"]),
        "complexity_score": complexity_score
    }


def configure_tiered_models(custom_models: dict = None, custom_tiers: list = None):
    """
    Configure custom models and tiers at runtime.
    
    Args:
        custom_models: Dict mapping model keys to model identifiers
        custom_tiers: List of tier definitions with min, max, model, description
    """
    global AI_MODELS, COMPLEXITY_TIERS
    
    if custom_models:
        AI_MODELS.update(custom_models)
    
    if custom_tiers:
        COMPLEXITY_TIERS = custom_tiers


# Example usage:
# from model_tiers import get_model_for_complexity, get_tier_info
# 
# complexity = 75
# model = get_model_for_complexity(complexity)  # Returns "AI2"
# tier_info = get_tier_info(complexity)  # Returns full tier details
