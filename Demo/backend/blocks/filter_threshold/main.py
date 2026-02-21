"""Filter threshold block — compare a value against a threshold."""

import operator as op

OPERATORS = {
    "<": op.lt,
    "<=": op.le,
    ">": op.gt,
    ">=": op.ge,
    "==": op.eq,
    "!=": op.ne,
}


async def execute(inputs: dict, context: dict) -> dict:
    value = float(inputs["value"])
    threshold = float(inputs["threshold"])
    op_str = inputs["operator"]
    op_func = OPERATORS.get(op_str)
    if op_func is None:
        raise ValueError(f"Unknown operator: {op_str}")
    return {"passed": op_func(value, threshold), "value": value}
