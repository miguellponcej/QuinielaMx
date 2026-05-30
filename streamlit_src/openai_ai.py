from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests

from streamlit_src.product_engine import ProductDraft, generate_product, sanitize_copy


OPENAI_API_URL = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"


PRODUCT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "niche",
        "product_type",
        "title",
        "subtitle",
        "description",
        "price_usd",
        "sales_bullets",
        "table_of_contents",
        "sections",
    ],
    "properties": {
        "niche": {"type": "string"},
        "product_type": {"type": "string"},
        "title": {"type": "string"},
        "subtitle": {"type": "string"},
        "description": {"type": "string"},
        "price_usd": {"type": "number"},
        "sales_bullets": {"type": "array", "items": {"type": "string"}},
        "table_of_contents": {"type": "array", "items": {"type": "string"}},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["heading", "body"],
                "properties": {
                    "heading": {"type": "string"},
                    "body": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}


@dataclass
class OpenAIConfig:
    api_key: str
    model: str = DEFAULT_OPENAI_MODEL

    @property
    def is_configured(self) -> bool:
        key = self.api_key.strip()
        return key.startswith("sk-") and "replace" not in key.lower()


def _extract_output_text(response_payload: dict[str, Any]) -> str:
    if response_payload.get("output_text"):
        return str(response_payload["output_text"])
    chunks: list[str] = []
    for output_item in response_payload.get("output", []):
        for content_item in output_item.get("content", []):
            if content_item.get("type") in {"output_text", "text"} and content_item.get("text"):
                chunks.append(str(content_item["text"]))
    return "".join(chunks)


def _clean_generated_product(value: dict[str, Any], fallback: ProductDraft) -> ProductDraft:
    sales_bullets = [sanitize_copy(str(item)) for item in value.get("sales_bullets", []) if str(item).strip()]
    toc = [sanitize_copy(str(item)) for item in value.get("table_of_contents", []) if str(item).strip()]
    sections = []
    for section in value.get("sections", []):
        heading = sanitize_copy(str(section.get("heading", ""))).strip()
        body = [sanitize_copy(str(item)) for item in section.get("body", []) if str(item).strip()]
        if heading and body:
            sections.append({"heading": heading, "body": body})

    try:
        price = float(value.get("price_usd", fallback.price_usd))
    except (TypeError, ValueError):
        price = fallback.price_usd
    price = min(max(price, 5.0), 99.0)

    return ProductDraft(
        niche=sanitize_copy(str(value.get("niche", fallback.niche)))[:120] or fallback.niche,
        product_type=sanitize_copy(str(value.get("product_type", fallback.product_type)))[:60] or fallback.product_type,
        title=sanitize_copy(str(value.get("title", fallback.title)))[:120] or fallback.title,
        subtitle=sanitize_copy(str(value.get("subtitle", fallback.subtitle)))[:220] or fallback.subtitle,
        description=sanitize_copy(str(value.get("description", fallback.description)))[:420] or fallback.description,
        price_usd=price,
        sales_bullets=sales_bullets[:8] or fallback.sales_bullets,
        table_of_contents=toc[:10] or fallback.table_of_contents,
        sections=sections[:10] or fallback.sections,
    )


def generate_ai_product(config: OpenAIConfig, market: str, idea: dict[str, Any]) -> ProductDraft:
    fallback = generate_product(market, idea)
    if not config.is_configured:
        return fallback

    prompt = {
        "market": market,
        "idea": idea,
        "requirements": [
            "Create a legitimate, useful digital product in Spanish.",
            "Avoid guaranteed income claims, fraud, phishing, malware, trading promises, private keys, seed phrases, and misleading copy.",
            "Keep the product practical enough to sell as a low-cost PDF, checklist, guide, template, report, or mini-course.",
            "Use specific but realistic benefits and a commercial tone suitable for a landing page.",
        ],
    }
    payload = {
        "model": config.model.strip() or DEFAULT_OPENAI_MODEL,
        "input": [
            {
                "role": "developer",
                "content": [
                    {
                        "type": "input_text",
                        "text": "You generate safe, legitimate digital products. Return only JSON matching the schema.",
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": json.dumps(prompt, ensure_ascii=False)}],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "digital_product",
                "strict": True,
                "schema": PRODUCT_SCHEMA,
            }
        },
    }
    response = requests.post(
        OPENAI_API_URL,
        headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=45,
    )
    response.raise_for_status()
    output_text = _extract_output_text(response.json())
    generated = json.loads(output_text)
    return _clean_generated_product(generated, fallback)
