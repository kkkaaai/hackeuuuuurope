from __future__ import annotations

import logging
import re
from typing import Any

import stripe

from app.blocks.executor import register_implementation
from app.config import settings

logger = logging.getLogger("agentflow.blocks.stripe")


def _validate_amount(amount_cents: int) -> None:
    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")
    if amount_cents > 99_999_999:
        raise ValueError("amount_cents exceeds maximum (99999999)")


def _validate_currency(currency: str) -> None:
    if not re.fullmatch(r"[a-z]{3}", currency):
        raise ValueError("currency must be a 3-letter ISO 4217 code")


def _get_client() -> stripe.StripeClient:
    if not settings.stripe_secret_key:
        raise ValueError("STRIPE_SECRET_KEY not configured — add it to .env")
    return stripe.StripeClient(settings.stripe_secret_key)


@register_implementation("stripe_instant_purchase")
async def stripe_instant_purchase(inputs: dict[str, Any]) -> dict[str, Any]:
    """Complete a purchase instantly — agentic commerce.

    Creates customer, attaches payment method, charges, and confirms
    in a single step. The agent acts as a personal shopper.
    """
    product_name = inputs["product_name"]
    amount_cents = int(inputs["amount_cents"])
    currency = inputs.get("currency", "eur")
    customer_email = inputs["customer_email"]
    shipping_address = inputs.get("shipping_address", "")

    _validate_amount(amount_cents)
    _validate_currency(currency)

    try:
        client = _get_client()

        # 1. Create or reuse customer
        existing = client.customers.list(params={"email": customer_email, "limit": 1})
        if existing.data:
            customer = existing.data[0]
        else:
            customer = client.customers.create(
                params={"email": customer_email, "name": customer_email.split("@")[0]}
            )

        # 2. Attach a payment method (test mode: pm_card_visa)
        payment_method = client.payment_methods.attach(
            "pm_card_visa",
            params={"customer": customer.id},
        )

        # 3. Set as default payment method
        client.customers.update(
            customer.id,
            params={
                "invoice_settings": {"default_payment_method": payment_method.id},
            },
        )

        # 4. Create PaymentIntent and confirm immediately (auto-purchase)
        intent = client.payment_intents.create(
            params={
                "amount": amount_cents,
                "currency": currency,
                "customer": customer.id,
                "payment_method": payment_method.id,
                "confirm": True,
                "automatic_payment_methods": {
                    "enabled": True,
                    "allow_redirects": "never",
                },
                "description": f"AgentFlow purchase: {product_name}",
                "metadata": {
                    "product_name": product_name,
                    "shipping_address": shipping_address,
                    "source": "agentflow_agent",
                },
                "receipt_email": customer_email,
            }
        )
    except ValueError:
        raise
    except Exception as e:
        logger.error("Stripe instant purchase error [%s]: %s", type(e).__name__, e)
        code = getattr(e, "code", None) or type(e).__name__
        raise ValueError(f"Stripe instant purchase failed: {code}") from None

    receipt_url = ""
    if intent.latest_charge:
        try:
            charge = client.charges.retrieve(intent.latest_charge)
            receipt_url = charge.receipt_url or ""
        except Exception:
            pass

    return {
        "payment_id": intent.id,
        "status": intent.status,
        "amount_cents": intent.amount,
        "currency": intent.currency,
        "customer_id": customer.id,
        "receipt_url": receipt_url,
        "product_name": product_name,
    }
