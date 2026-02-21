"""Generate a budget within 5% above or below the given price."""

async def execute(inputs: dict, context: dict) -> dict:
    price = inputs['price']
    min_budget = price * 0.95
    max_budget = price * 1.05
    return {
        'min_budget': min_budget,
        'max_budget': max_budget
    }
