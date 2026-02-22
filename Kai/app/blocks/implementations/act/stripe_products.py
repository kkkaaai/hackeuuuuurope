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


@register_implementation("stripe_create_product")
async def stripe_create_product(inputs: dict[str, Any]) -> dict[str, Any]:
    """Create a product in Stripe's catalog."""
    name = inputs["name"]
    description = inputs.get("description", "")

    try:
        client = _get_client()

        params: dict[str, Any] = {"name": name}
        if description:
            params["description"] = description

        product = client.products.create(params=params)
    except ValueError:
        raise
    except Exception as e:
        logger.error("Stripe Product error [%s]: %s", type(e).__name__, e)
        code = getattr(e, "code", None) or type(e).__name__
        raise ValueError(f"Stripe product creation failed: {code}") from None

    return {
        "product_id": product.id,
        "name": product.name,
        "active": product.active,
    }


@register_implementation("stripe_create_price")
async def stripe_create_price(inputs: dict[str, Any]) -> dict[str, Any]:
    """Attach a price to a Stripe product."""
    product_id = inputs["product_id"]
    amount_cents = int(inputs["amount_cents"])
    currency = inputs.get("currency", "eur")
    recurring_interval = inputs.get("recurring_interval")

    if not product_id.startswith("prod_"):
        raise ValueError("product_id must be a valid Stripe product ID (starts with 'prod_')")
    _validate_amount(amount_cents)
    _validate_currency(currency)
    _validate_interval(recurring_interval)

    try:
        client = _get_client()

        params: dict[str, Any] = {
            "product": product_id,
            "unit_amount": amount_cents,
            "currency": currency,
        }
        if recurring_interval:
            params["recurring"] = {"interval": recurring_interval}

        price = client.prices.create(params=params)
    except ValueError:
        raise
    except Exception as e:
        logger.error("Stripe Price error [%s]: %s", type(e).__name__, e)
        code = getattr(e, "code", None) or type(e).__name__
        raise ValueError(f"Stripe price creation failed: {code}") from None

    return {
        "price_id": price.id,
        "amount_cents": price.unit_amount,
        "currency": price.currency,
        "recurring": price.recurring is not None,
    }
