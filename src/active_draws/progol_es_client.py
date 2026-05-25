"""Secondary Progol.es references for current program images.

This is not an official source of truth. It is used only as a fallback reference
when official pages do not expose structured matches. Any extracted matches are
marked as secondary and still require strict validation before prediction.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any

from src.active_draws.draw_parser import base_draw, extract_image_urls, html_to_text


PROGOL_ES_URLS = {
    "progol": "https://www.progol.es/",
    "progol_revancha": "https://www.progol.es/progol_revancha.html?id=progol_revancha",
    "progol_media_semana": "https://www.progol.es/progol_media_semana.html?id=progol_media_semana",
}


def secondary_url_for_game(game_id: str) -> str | None:
    """Return secondary program URL for supported Progol games."""

    return PROGOL_ES_URLS.get(game_id)


def parse_progol_es_reference(html: str, game_id: str, game_name: str, url: str) -> dict[str, Any]:
    """Parse secondary references and images from Progol.es."""

    draw = base_draw(game_id, game_name, "sports_pool", url, "secundaria_progol_es", status="active")
    text = html_to_text(html)
    draw["data_freshness"] = "actualizada" if _looks_like_current_program(text) else "aceptable"
    draw["draw_number"] = _latest_archive_number(text) or "Dato no disponible"
    draw["source_warnings"] = [
        "Fuente secundaria Progol.es registrada para programa/momios. Validar contra la fuente oficial antes de jugar."
    ]
    image_urls = _program_image_urls(html, url, game_id)
    for image_url in image_urls:
        draw.setdefault("source_artifacts", []).append(
            {"type": "image", "url": image_url, "purpose": "programa_secundario_progol_es"}
        )
    draw["alternate_sources"] = image_urls
    if not image_urls:
        draw["source_errors"].append("Progol.es no entrego imagen de programa legible.")
    return draw


def _program_image_urls(html: str, url: str, game_id: str) -> list[str]:
    urls = extract_image_urls(html, url)
    preferred_tokens = {
        "progol_media_semana": ("resultados_media", "media", "progol-media"),
        "progol_revancha": ("resultados", "revancha", "progol"),
        "progol": ("resultados", "progol"),
    }.get(game_id, ("progol",))
    preferred = [
        image_url
        for image_url in urls
        if any(token in image_url.lower() for token in preferred_tokens)
    ]
    # Some pages include program images in inline CSS or lazy-load attributes.
    for match in re.finditer(r"['\"]([^'\"]*(?:resultados|media|progol)[^'\"]*\.(?:jpg|png|webp)(?:\?[^'\"]*)?)['\"]", html, re.I):
        image_url = urllib.parse.urljoin(url, match.group(1))
        if image_url not in preferred:
            preferred.append(image_url)
    return list(dict.fromkeys(preferred or urls))[:3]


def _latest_archive_number(text: str) -> str:
    numbers = [int(value) for value in re.findall(r"\b(?:Archivo:)?\s*(\d{3,5})\b", text)]
    return str(max(numbers)) if numbers else ""


def _looks_like_current_program(text: str) -> bool:
    return "programa" in text.lower() or "momios" in text.lower() or "resultados" in text.lower()
