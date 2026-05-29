from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


STRIPE_API_BASE_URL = "https://api.stripe.com/v1"
STRIPE_API_VERSION = "2026-02-25.clover"


@dataclass
class StripeConfig:
    secret_key: str
    app_base_url: str
    currency: str = "usd"
    api_version: str = STRIPE_API_VERSION

    @property
    def is_configured(self) -> bool:
        key = self.secret_key.strip()
        return (
            key.startswith(("sk_test_", "sk_live_"))
            and "replace" not in key.lower()
            and "your-" not in key.lower()
            and bool(self.app_base_url.strip())
        )


def _headers(config: StripeConfig) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.secret_key}",
        "Stripe-Version": config.api_version,
    }


def stripe_account(config: StripeConfig) -> dict[str, Any]:
    response = requests.get(
        f"{STRIPE_API_BASE_URL}/account",
        headers=_headers(config),
        timeout=25,
    )
    response.raise_for_status()
    return response.json()


def create_checkout_session(config: StripeConfig, product: dict[str, Any]) -> dict[str, Any]:
    price_cents = int(round(float(product["price_usd"]) * 100))
    if price_cents < 50:
        raise ValueError("Stripe requiere un monto minimo practico. Usa al menos $0.50 USD.")

    success_url = f"{config.app_base_url}?stripe_success=1&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{config.app_base_url}?stripe_cancel=1&product_slug={product['slug']}"
    payload = {
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": product["slug"],
        "line_items[0][price_data][currency]": config.currency.lower(),
        "line_items[0][price_data][unit_amount]": str(price_cents),
        "line_items[0][price_data][product_data][name]": product["title"][:120],
        "line_items[0][price_data][product_data][description]": product.get("subtitle", "")[:250],
        "line_items[0][quantity]": "1",
        "metadata[product_slug]": product["slug"],
        "metadata[product_title]": product["title"][:120],
    }
    response = requests.post(
        f"{STRIPE_API_BASE_URL}/checkout/sessions",
        headers=_headers(config),
        data=payload,
        timeout=25,
    )
    response.raise_for_status()
    session = response.json()
    if not session.get("url"):
        raise RuntimeError("Stripe no devolvio una URL de checkout.")
    return session


def retrieve_checkout_session(config: StripeConfig, session_id: str) -> dict[str, Any]:
    response = requests.get(
        f"{STRIPE_API_BASE_URL}/checkout/sessions/{session_id}",
        headers=_headers(config),
        timeout=25,
    )
    response.raise_for_status()
    return response.json()
