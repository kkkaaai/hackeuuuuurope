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


@register_implementation("stripe_pay")
async def stripe_pay(inputs: dict[str, Any]) -> dict[str, Any]:
    """Process a one-time payment using Stripe."""
    amount_cents = int(inputs["amount_cents"])
    currency = inputs.get("currency", "eur")
    description = inputs.get("description", "AgentFlow payment")
    metadata = inputs.get("metadata", {})

    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")
    if amount_cents > 99_999_999:
        raise ValueError("amount_cents exceeds maximum (99999999)")

    try:
        client = _get_client()

        intent = client.payment_intents.create(
            params={
                "amount": amount_cents,
                "currency": currency,
                "description": description,
                "metadata": metadata,
                "automatic_payment_methods": {"enabled": True},
            }
        )
    except ValueError:
        raise
    except Exception as e:
        logger.error("Stripe API error [%s]: %s", type(e).__name__, e)
        code = getattr(e, "code", None) or type(e).__name__
        raise ValueError(f"Stripe payment failed: {code}") from None

    return {
        "payment_id": intent.id,
        "status": intent.status,
        "amount_cents": intent.amount,
        "currency": intent.currency,
    }
