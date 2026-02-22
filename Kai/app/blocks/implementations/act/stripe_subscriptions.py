from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import stripe

from app.blocks.executor import register_implementation
from app.config import settings

logger = logging.getLogger("agentflow.blocks.stripe")


def _get_client() -> stripe.StripeClient:
    if not settings.stripe_secret_key:
        raise ValueError("STRIPE_SECRET_KEY not configured — add it to .env")
    return stripe.StripeClient(settings.stripe_secret_key)


@register_implementation("stripe_create_subscription")
async def stripe_create_subscription(inputs: dict[str, Any]) -> dict[str, Any]:
    """Create a recurring subscription for a Stripe customer."""
    customer_id = inputs["customer_id"]
    price_id = inputs["price_id"]

    if not customer_id.startswith("cus_"):
        raise ValueError("customer_id must be a valid Stripe customer ID (starts with 'cus_')")
    if not price_id.startswith("price_"):
        raise ValueError("price_id must be a valid Stripe price ID (starts with 'price_')")

    try:
        client = _get_client()

        subscription = client.subscriptions.create(
            params={
                "customer": customer_id,
                "items": [{"price": price_id}],
                "payment_behavior": "default_incomplete",
            }
        )
    except ValueError:
        raise
    except Exception as e:
        logger.error("Stripe Subscription error [%s]: %s", type(e).__name__, e)
        code = getattr(e, "code", None) or type(e).__name__
        raise ValueError(f"Stripe subscription creation failed: {code}") from None

    period_end_ts = subscription.billing_cycle_anchor
    period_end = datetime.fromtimestamp(period_end_ts, tz=timezone.utc).isoformat()

    return {
        "subscription_id": subscription.id,
        "status": subscription.status,
        "current_period_end": period_end,
    }
