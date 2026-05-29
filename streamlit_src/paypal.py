from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class PayPalConfig:
    mode: str
    client_id: str
    client_secret: str
    app_base_url: str

    @property
    def base_url(self) -> str:
        if self.mode == "live":
            return "https://api-m.paypal.com"
        return "https://api-m.sandbox.paypal.com"

    @property
    def is_configured(self) -> bool:
        placeholders = ("replace", "your-", "")
        values = (self.client_id.strip(), self.client_secret.strip(), self.app_base_url.strip())
        return all(value and not any(value.lower().startswith(prefix) for prefix in placeholders if prefix) for value in values)


def paypal_access_token(config: PayPalConfig) -> str:
    credentials = f"{config.client_id}:{config.client_secret}".encode("utf-8")
    basic = base64.b64encode(credentials).decode("ascii")
    response = requests.post(
        f"{config.base_url}/v1/oauth2/token",
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
        timeout=25,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_order(config: PayPalConfig, product: dict[str, Any]) -> dict[str, Any]:
    token = paypal_access_token(config)
    return_url = f"{config.app_base_url}?paypal_return=1&product_slug={product['slug']}"
    cancel_url = f"{config.app_base_url}?paypal_cancel=1&product_slug={product['slug']}"
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": product["slug"],
                "description": product["title"][:120],
                "amount": {
                    "currency_code": "USD",
                    "value": f"{float(product['price_usd']):.2f}",
                },
            }
        ],
        "payment_source": {
            "paypal": {
                "experience_context": {
                    "brand_name": "AI Digital Product Money Machine",
                    "shipping_preference": "NO_SHIPPING",
                    "user_action": "PAY_NOW",
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                }
            }
        },
    }
    response = requests.post(
        f"{config.base_url}/v2/checkout/orders",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        json=payload,
        timeout=25,
    )
    response.raise_for_status()
    data = response.json()
    approval_url = next(
        (link["href"] for link in data.get("links", []) if link.get("rel") in {"payer-action", "approve"}),
        None,
    )
    if not approval_url:
        raise RuntimeError("PayPal did not return an approval URL.")
    data["approval_url"] = approval_url
    return data


def capture_order(config: PayPalConfig, order_id: str) -> dict[str, Any]:
    token = paypal_access_token(config)
    response = requests.post(
        f"{config.base_url}/v2/checkout/orders/{order_id}/capture",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        timeout=25,
    )
    response.raise_for_status()
    return response.json()
