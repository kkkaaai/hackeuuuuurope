"""Stripe payment block — creates a payment intent via Stripe API."""

import os
import uuid

import httpx


async def execute(inputs: dict, context: dict) -> dict:
    amount = inputs["amount_cents"]
    currency = inputs.get("currency", "eur")
    description = inputs.get("description", "AgentFlow payment")

    api_key = os.environ.get("STRIPE_SECRET_KEY", "")

    if not api_key or api_key.startswith("sk_test_"):
        # Test/stub mode
        pid = f"pi_{uuid.uuid4().hex[:16]}"
        print(f"[STRIPE STUB] amount={amount} {currency} desc={description}")
        return {
            "payment_id": pid,
            "status": "succeeded (test)",
            "amount_cents": amount,
            "currency": currency,
        }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://api.stripe.com/v1/payment_intents",
            auth=(api_key, ""),
            data={
                "amount": amount,
                "currency": currency,
                "description": description,
                "confirm": "true",
                "automatic_payment_methods[enabled]": "true",
                "automatic_payment_methods[allow_redirects]": "never",
            },
        )

    if resp.status_code == 200:
        data = resp.json()
        return {
            "payment_id": data["id"],
            "status": data["status"],
            "amount_cents": data["amount"],
            "currency": data["currency"],
        }

    return {
        "payment_id": "",
        "status": f"failed ({resp.status_code})",
        "amount_cents": amount,
        "currency": currency,
    }
