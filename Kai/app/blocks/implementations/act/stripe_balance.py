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


@register_implementation("stripe_get_balance")
async def stripe_get_balance(inputs: dict[str, Any]) -> dict[str, Any]:
    """Retrieve the current Stripe account balance."""
    currency_filter = inputs.get("currency_filter", "")

    try:
        client = _get_client()
        balance = client.balance.retrieve()
    except ValueError:
        raise
    except Exception as e:
        logger.error("Stripe Balance error [%s]: %s", type(e).__name__, e)
        code = getattr(e, "code", None) or type(e).__name__
        raise ValueError(f"Stripe balance retrieval failed: {code}") from None

    available_amount = 0
    pending_amount = 0
    currency = currency_filter or "eur"

    for entry in balance.available:
        if not currency_filter or entry.currency == currency_filter:
            available_amount += entry.amount
            currency = entry.currency
            break

    for entry in balance.pending:
        if not currency_filter or entry.currency == currency_filter:
            pending_amount += entry.amount
            break

    return {
        "available_amount": available_amount,
        "pending_amount": pending_amount,
        "currency": currency,
    }
