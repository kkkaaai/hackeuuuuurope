# Tiered AI Model System

## Overview

The parallel decomposition system now uses **tiered AI models** to optimize task decomposition based on task complexity. Different AI models are automatically selected for different complexity levels.

## Default Tier Configuration

| Complexity Range | Model | Description |
|------------------|-------|-------------|
| 80-100 | AI2 | Very Complex (premium model) |
| 60-80 | AI1 | Complex (standard model) |
| 40-60 | AI2 | Moderate (premium model) |
| 0-40 | AI1 | Simple (standard model) |

## Default Model Mappings

- **AI1**: `qwen/qwen3-235b-a22b` (standard model)
- **AI2**: `deepseek-ai/deepseek-v3.2` (premium model)

## How It Works

1. When a task is decomposed, its **complexity_score** is evaluated first
2. Based on the score, the appropriate AI model is automatically selected
3. The task is decomposed using that model
4. Logs show which model was used for each decomposition

## Example Output

```
[DECOMP] d694a9e573a0: Decomposing (complexity 75)...
[DECOMP] d694a9e573a0: Using model AI2 (Very Complex (80-100))
[DECOMP] d694a9e573a0: Created 5 subtasks
```

## Customizing the Tiers

### Option 1: Edit model_tiers.py Directly

Edit the `COMPLEXITY_TIERS` list in `model_tiers.py`:

```python
COMPLEXITY_TIERS = [
    {"min": 85, "max": 100, "model": "AI2", "description": "Very Complex (85-100)"},
    {"min": 60, "max": 85, "model": "AI1", "description": "Complex (60-85)"},
    # ... more tiers
]
```

### Option 2: Configure at Runtime

In your script:

```python
from model_tiers import configure_tiered_models

custom_tiers = [
    {"min": 80, "max": 100, "model": "AI2", "description": "Very Complex"},
    {"min": 60, "max": 80, "model": "AI1", "description": "Complex"},
    {"min": 0, "max": 60, "model": "AI2", "description": "Simple/Moderate"},
]

configure_tiered_models(custom_tiers=custom_tiers)
```

### Option 3: Add Custom Models

Define new models in `model_tiers.py`:

```python
AI_MODELS = {
    "AI1": "qwen/qwen3-235b-a22b",
    "AI2": "deepseek-ai/deepseek-v3.2",
    "AI3": "your-new-model/identifier",  # Add custom model
}

COMPLEXITY_TIERS = [
    {"min": 80, "max": 100, "model": "AI3", "description": "Very Complex"},
    # ...
]
```

## API Reference

### get_model_for_complexity(complexity_score)

Returns the model key for a given complexity score.

```python
from model_tiers import get_model_for_complexity

model = get_model_for_complexity(75)  # Returns "AI2"
```

### get_model_endpoint(model_key)

Returns the full model identifier/endpoint.

```python
from model_tiers import get_model_endpoint

endpoint = get_model_endpoint("AI2")  # Returns "deepseek-ai/deepseek-v3.2"
```

### get_tier_info(complexity_score)

Returns detailed tier information.

```python
from model_tiers import get_tier_info

info = get_tier_info(75)
# Returns:
# {
#   "min": 80,
#   "max": 100,
#   "model": "AI2",
#   "description": "Very Complex (80-100)",
#   "model_endpoint": "deepseek-ai/deepseek-v3.2",
#   "complexity_score": 75
# }
```

## Cost Optimization

By using tiered models:
- **Simple tasks** use cheaper/faster models (AI1)
- **Complex tasks** use more capable models (AI2)
- **Balanced trade-off** between cost and quality

## Logging

The decomposition logs show which model was used:

```
[DECOMP] task_id: Using model AI2 (Very Complex (80-100))
```

This helps track:
- Which models are being used most frequently
- Cost analysis per complexity tier
- Model performance across complexity levels

## Integration with Decomposer

The tiered system is automatically integrated into:
- `parallel_recursive_decomposer.py` - parallel decomposition
- `recursive_decomposer.py` - sequential decomposition

Both scripts will use the appropriate model based on task complexity.

## Files

- **model_tiers.py** - Configuration and API
- **task_decomposer.py** - Updated to use tiered models
- **parallel_recursive_decomposer.py** - Updated to log model usage
- **recursive_decomposer.py** - Updated to log model usage
- **MODEL_TIERS.md** - This documentation
