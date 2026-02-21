"""Commerce place order block — stub for demo (logs the order)."""

import uuid
from datetime import datetime, timedelta, timezone


async def execute(inputs: dict, context: dict) -> dict:
    product_name = inputs["product_name"]
    price = inputs["price"]
    quantity = inputs.get("quantity", 1)

    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    total = round(price * quantity, 2)
    delivery = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%d")

    print(f"[ORDER STUB] {product_name} x{quantity} = {total}")
    return {
        "order_id": order_id,
        "status": "confirmed",
        "total": total,
        "estimated_delivery": delivery,
    }
