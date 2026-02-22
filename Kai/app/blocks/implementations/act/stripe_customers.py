from __future__ import annotations

import logging
from typing import Any

import stripe

from app.blocks.executor import register_implementation
from app.config import settings

logger = logging.getLogger("agentflow.blocks.stripe")


def _get_client() -> stripe.StripeClient:
    if not settings.stripe_secret_key:
        raise ValueError("STRIPE_SECRET_KEY not configured — add it to .env")
    return stripe.StripeClient(settings.stripe_secret_key)


@register_implementation("stripe_create_customer")
async def stripe_create_customer(inputs: dict[str, Any]) -> dict[str, Any]:
    """Create a Stripe customer record."""
    email = inputs["email"]
    name = inputs.get("name", "")
    description = inputs.get("description", "")

    try:
        client = _get_client()

        params: dict[str, Any] = {"email": email}
        if name:
            params["name"] = name
        if description:
            params["description"] = description

        customer = client.customers.create(params=params)
    except ValueError:
        raise
    except Exception as e:
        logger.error("Stripe Customer error [%s]: %s", type(e).__name__, e)
        code = getattr(e, "code", None) or type(e).__name__
        raise ValueError(f"Stripe customer creation failed: {code}") from None

    return {
        "customer_id": customer.id,
        "email": customer.email,
        "name": customer.name or "",
    }
