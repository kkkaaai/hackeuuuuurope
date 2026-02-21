"""Compare the extracted AirPods price to the generated budget and determine if it fits within the budget."""

async def execute(inputs: dict, context: dict) -> dict:
    price = inputs['price']
    min_budget = inputs['min_budget']
    max_budget = inputs['max_budget']
    
    fits_within_budget = min_budget <= price <= max_budget
    
    return {'fits_within_budget': fits_within_budget}
