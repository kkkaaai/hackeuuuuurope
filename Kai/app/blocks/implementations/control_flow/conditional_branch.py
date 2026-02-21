from __future__ import annotations

import operator
import re
from typing import Any

from app.blocks.executor import register_implementation

OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


@register_implementation("conditional_branch")
async def conditional_branch(inputs: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a condition and return which branch to take.

    Supports:
    - Simple comparison: "value < 400" with a separate 'value' input
    - Direct boolean: value is already True/False
    """
    condition = inputs.get("condition", "")
    value = inputs.get("value")

    # If value is already a boolean, use it directly
    if isinstance(value, bool):
        return {"branch": "true" if value else "false", "evaluated_value": value}

    # Try to parse condition as "field op threshold"
    match = re.match(r"(\w+)\s*(<=?|>=?|==|!=)\s*(.+)", condition)
    if match and value is not None:
        _, op_str, threshold_str = match.groups()
        try:
            threshold = float(threshold_str)
            num_value = float(value)
            op_fn = OPERATORS.get(op_str, operator.eq)
            result = op_fn(num_value, threshold)
            return {
                "branch": "true" if result else "false",
                "evaluated_value": value,
            }
        except (ValueError, TypeError):
            pass

    # Fallback: truthy check on value
    result = bool(value)
    return {"branch": "true" if result else "false", "evaluated_value": value}
