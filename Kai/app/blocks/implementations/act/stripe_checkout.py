from __future__ import annotations

import logging
import re
from typing import Any

import stripe

from app.blocks.executor import register_implementation
from app.config import settings

logger = logging.getLogger("agentflow.blocks.stripe")

VALID_INTERVALS = {"day", "week", "month", "year"}


def _validate_amount(amount_cents: int) -> None:
    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")
    if amount_cents > 99_999_999:
        raise ValueError("amount_cents exceeds maximum (99999999)")


def _validate_currency(currency: str) -> None:
    if not re.fullmatch(r"[a-z]{3}", currency):
        raise ValueError("currency must be a 3-letter ISO 4217 code")


def _validate_interval(interval: str | None) -> None:
    if interval and interval not in VALID_INTERVALS:
        raise ValueError(f"recurring_interval must be one of {VALID_INTERVALS}")


def _get_client() -> stripe.StripeClient:
    if not settings.stripe_secret_key:
        raise ValueError("STRIPE_SECRET_KEY not configured — add it to .env")
    return stripe.StripeClient(settings.stripe_secret_key)


@register_implementation("stripe_create_checkout")
async def stripe_create_checkout(inputs: dict[str, Any]) -> dict[str, Any]:
    """Generate a Stripe Checkout Session URL (hosted payment page)."""
    product_name = inputs["product_name"]
    amount_cents = int(inputs["amount_cents"])
    currency = inputs.get("currency", "eur")
    quantity = int(inputs.get("quantity", 1))
    success_url = inputs.get("success_url", "https://agentflow.ai/success")
    cancel_url = inputs.get("cancel_url", "https://agentflow.ai/cancel")

    _validate_amount(amount_cents)
    _validate_currency(currency)

    try:
        client = _get_client()

        session = client.checkout.sessions.create(
            params={
                "payment_method_types": ["card"],
                "line_items": [
                    {
                        "price_data": {
                            "currency": currency,
                            "product_data": {"name": product_name},
                            "unit_amount": amount_cents,
                        },
                        "quantity": quantity,
                    },
                ],
                "mode": "payment",
                "success_url": success_url,
                "cancel_url": cancel_url,
            }
        )
    except ValueError:
        raise
    except Exception as e:
        logger.error("Stripe Checkout error [%s]: %s", type(e).__name__, e)
        code = getattr(e, "code", None) or type(e).__name__
        raise ValueError(f"Stripe checkout creation failed: {code}") from None

    return {
        "checkout_url": session.url,
        "session_id": session.id,
        "status": session.status or "open",
    }


@register_implementation("stripe_create_payment_link")
async def stripe_create_payment_link(inputs: dict[str, Any]) -> dict[str, Any]:
    """Generate a reusable Stripe Payment Link (creates product + price automatically)."""
    product_name = inputs["product_name"]
    amount_cents = int(inputs["amount_cents"])
    currency = inputs.get("currency", "eur")
    recurring_interval = inputs.get("recurring_interval")

    _validate_amount(amount_cents)
    _validate_currency(currency)
    _validate_interval(recurring_interval)

    try:
        client = _get_client()

        product = client.products.create(params={"name": product_name})

        price_params: dict[str, Any] = {
            "product": product.id,
            "unit_amount": amount_cents,
            "currency": currency,
        }
        if recurring_interval:
            price_params["recurring"] = {"interval": recurring_interval}

        price = client.prices.create(params=price_params)

        link = client.payment_links.create(
            params={"line_items": [{"price": price.id, "quantity": 1}]}
        )
    except ValueError:
        raise
    except Exception as e:
        logger.error("Stripe Payment Link error [%s]: %s", type(e).__name__, e)
        code = getattr(e, "code", None) or type(e).__name__
        raise ValueError(f"Stripe payment link creation failed: {code}") from None

    return {
        "payment_link_url": link.url,
        "link_id": link.id,
        "product_id": product.id,
        "price_id": price.id,
    }
