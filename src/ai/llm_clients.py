"""Small optional clients for OpenAI and Anthropic extraction.

The app never hardcodes keys. Calls are attempted only when the corresponding
environment variable is configured.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMResponse:
    """Normalized LLM response."""

    ok: bool
    provider: str
    text: str
    error: str = ""


def openai_available() -> bool:
    """Return whether OpenAI extraction can be used."""

    return bool(os.getenv("OPENAI_API_KEY"))


def anthropic_available() -> bool:
    """Return whether Anthropic extraction can be used."""

    return bool(os.getenv("ANTHROPIC_API_KEY"))


def call_openai_json(
    prompt: str,
    images: list[dict[str, str]] | None = None,
    timeout_seconds: int = 45,
) -> LLMResponse:
    """Call OpenAI vision/text model and request JSON."""

    response = _call_openai_chat_json(prompt, images=images, timeout_seconds=timeout_seconds)
    if response.ok:
        return response
    fallback = _call_openai_responses_json(prompt, images=images, timeout_seconds=timeout_seconds)
    if fallback.ok:
        return fallback
    return LLMResponse(False, "openai", "", f"{response.error} | fallback responses: {fallback.error}")


def _call_openai_chat_json(
    prompt: str,
    images: list[dict[str, str]] | None = None,
    timeout_seconds: int = 45,
) -> LLMResponse:
    """Call legacy-compatible Chat Completions JSON mode."""

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return LLMResponse(False, "openai", "", "OPENAI_API_KEY no configurada.")
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image in images or []:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image['mime_type']};base64,{image['base64']}"},
            }
        )
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    return _send_json_request(request, "openai", timeout_seconds, _parse_openai_text)


def _call_openai_responses_json(
    prompt: str,
    images: list[dict[str, str]] | None = None,
    timeout_seconds: int = 45,
) -> LLMResponse:
    """Call OpenAI Responses API as fallback."""

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return LLMResponse(False, "openai", "", "OPENAI_API_KEY no configurada.")
    content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    for image in images or []:
        content.append(
            {
                "type": "input_image",
                "image_url": f"data:{image['mime_type']};base64,{image['base64']}",
            }
        )
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "input": [{"role": "user", "content": content}],
        "text": {"format": {"type": "json_object"}},
        "temperature": 0.0,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    return _send_json_request(request, "openai", timeout_seconds, _parse_openai_responses_text)


def call_anthropic_json(
    prompt: str,
    images: list[dict[str, str]] | None = None,
    timeout_seconds: int = 45,
) -> LLMResponse:
    """Call Anthropic vision/text model and request JSON."""

    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return LLMResponse(False, "anthropic", "", "ANTHROPIC_API_KEY no configurada.")
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image in images or []:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image["mime_type"],
                    "data": image["base64"],
                },
            }
        )
    payload = {
        "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
        "max_tokens": 4096,
        "temperature": 0.0,
        "messages": [{"role": "user", "content": content}],
    }
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": key,
            "anthropic-version": os.getenv("ANTHROPIC_VERSION", "2023-06-01"),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    return _send_json_request(request, "anthropic", timeout_seconds, _parse_anthropic_text)


def _send_json_request(request: urllib.request.Request, provider: str, timeout_seconds: int, parser) -> LLMResponse:
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
        return LLMResponse(True, provider, parser(payload))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        return LLMResponse(False, provider, "", f"{provider} HTTP {exc.code}: {body}")
    except Exception as exc:
        return LLMResponse(False, provider, "", f"{provider} no disponible: {exc}")


def _parse_openai_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    return str(choices[0].get("message", {}).get("content", ""))


def _parse_openai_responses_text(payload: dict[str, Any]) -> str:
    if payload.get("output_text"):
        return str(payload["output_text"])
    texts = []
    for item in payload.get("output", []) or []:
        for part in item.get("content", []) or []:
            if part.get("type") in {"output_text", "text"} and part.get("text"):
                texts.append(str(part["text"]))
    return "\n".join(texts)


def _parse_anthropic_text(payload: dict[str, Any]) -> str:
    parts = payload.get("content") or []
    return "\n".join(str(part.get("text", "")) for part in parts if part.get("type") == "text")
