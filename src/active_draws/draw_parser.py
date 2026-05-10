"""Parsers for official draw pages."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urljoin


NOT_AVAILABLE = "Dato no disponible"


def html_to_text(html: str) -> str:
    """Convert a small HTML page to normalized text."""

    text = re.sub(r"<script.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def base_draw(
    game_id: str,
    game_name: str,
    game_type: str,
    official_url: str,
    raw_source: str,
    status: str = NOT_AVAILABLE,
) -> dict:
    """Create a draw record with safe defaults."""

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "game_id": game_id,
        "game_name": game_name,
        "game_type": game_type,
        "status": status,
        "draw_number": NOT_AVAILABLE,
        "closing_date": NOT_AVAILABLE,
        "draw_date": NOT_AVAILABLE,
        "estimated_prize": NOT_AVAILABLE,
        "accumulated_pool": NOT_AVAILABLE,
        "cost_per_entry": NOT_AVAILABLE,
        "official_url": official_url,
        "last_updated": now,
        "data_freshness": "no disponible",
        "data_quality_score": 0,
        "raw_source": raw_source,
        "matches": [],
        "source_errors": [],
        "missing_fields": [],
        "source_artifacts": [],
    }


def parse_home_results(html: str, official_url: str) -> list[dict]:
    """Parse available official result snippets without inventing active dates."""

    text = html_to_text(html)
    draws: list[dict] = []
    patterns = [
        ("progol", "Progol", "sports_pool", r"Resultados Progol\s+([LEV\s]+)\s+Resultados Revancha.*?Concurso\s+(\d+)\s+Fecha\s+(\d{2}/\d{2}/\d{4})"),
        ("progol_media_semana", "Progol Media Semana", "sports_pool", r"Resultados\s+([LEV\s]+)\s+Concurso\s+(\d+)\s+Fecha\s+(\d{2}/\d{2}/\d{4})"),
        ("protouch", "Protouch", "sports_pool", r"Resultados\s+([LDV\s]+)\s+\d+\s+Bolsa acumulada\s+([\d.]+).*?Concurso\s+(\d+)\s+Fecha\s+(\d{2}/\d{2}/\d{4})"),
        ("melate", "Melate", "random_lottery", r"Número ganador Melate\s+([\d\s-]+)\s+Bolsa acumulada\s+([\d.]+).*?Sorteo\s+(\d+)\s+Fecha\s+(\d{2}/\d{2}/\d{4})"),
    ]
    for game_id, name, game_type, pattern in patterns:
        draw = base_draw(game_id, name, game_type, official_url, "oficial_home_resultados")
        match = re.search(pattern, text, flags=re.I)
        if match:
            groups = match.groups()
            if game_id == "protouch":
                draw["accumulated_pool"] = groups[1]
                draw["draw_number"] = groups[2]
                draw["draw_date"] = groups[3]
            elif game_id == "melate":
                draw["accumulated_pool"] = groups[1]
                draw["draw_number"] = groups[2]
                draw["draw_date"] = groups[3]
            else:
                draw["draw_number"] = groups[1]
                draw["draw_date"] = groups[2]
            draw["status"] = "Dato no disponible"
            draw["data_freshness"] = "actualizada"
        else:
            draw["source_errors"].append("No se encontro informacion estructurada en la fuente oficial.")
        draws.append(draw)
    return draws


def parse_quiniela_page(html: str, game_id: str, game_name: str, official_url: str) -> dict:
    """Parse a quiniela page. If matches are images, keep missing fields explicit."""

    text = html_to_text(html)
    draw = base_draw(game_id, game_name, "sports_pool", official_url, "oficial_quiniela")
    if "quiniela" in text.lower() or game_name.lower() in text.lower():
        draw["data_freshness"] = "actualizada"
    match = re.search(r"Concurso\s+(\d+)", text, flags=re.I)
    if match:
        draw["draw_number"] = match.group(1)
    for image_url in extract_image_urls(html, official_url):
        draw["source_artifacts"].append({"type": "image", "url": image_url, "purpose": "quiniela_oficial"})
    # Do not OCR or invent matches. Many official pages expose quinielas as images.
    if draw["source_artifacts"]:
        draw["source_errors"].append(
            "La fuente oficial publico la quiniela como imagen. Se registro la imagen, pero se requiere OCR/API para convertirla a partidos estructurados."
        )
    else:
        draw["source_errors"].append(
            "Partidos no disponibles como texto estructurado en la fuente oficial; requiere conector web/OCR automatizado."
        )
    return draw


def parse_tulotero_home(html: str, official_url: str) -> list[dict]:
    """Parse public TuLotero snippets for active draw metadata.

    TuLotero is useful as a secondary public signal for vigency, prize/cost
    metadata and draw numbers. It is not treated as the source of truth for
    structured Progol/Protouch fixtures.
    """

    text = html_to_text(html)
    draws: list[dict] = []
    patterns = [
        (
            "progol_media_semana",
            "Progol Media Semana",
            r"PROGOL\s+MS\s+(\d+).*?(?:A las|En)\s+([^$]+?)(\$[\d,]+(?:\.\d+)?)",
        ),
        (
            "progol",
            "Progol",
            r"PROGOL\s+(\d+).*?(?:A las|En)\s+([^$]+?)(\$[\d,]+(?:\.\d+)?)",
        ),
        (
            "melate",
            "Melate",
            r"MELATE\s+(\d+).*?(?:A las|En)\s+([^$]+?)(\$[\d,]+(?:\.\d+)?)",
        ),
    ]
    for game_id, name, pattern in patterns:
        match = re.search(pattern, text, flags=re.I | re.S)
        if not match:
            continue
        draw = base_draw(
            game_id,
            name,
            "sports_pool" if game_id.startswith("progol") else "random_lottery",
            official_url,
            "tulotero_publico",
            status="active",
        )
        draw["draw_number"] = match.group(1).strip()
        draw["closing_date"] = _clean_snippet(match.group(2))
        draw["accumulated_pool"] = match.group(3).strip()
        draw["data_freshness"] = "actualizada"
        if game_id.startswith("progol"):
            draw["source_errors"].append(
                "TuLotero confirma vigencia y premio, pero no entrega partidos estructurados para prediccion deportiva."
            )
        draws.append(draw)
    return draws


def extract_image_urls(html: str, base_url: str) -> list[str]:
    """Extract image URLs from a source page."""

    urls = []
    preferred = []
    for match in re.finditer(r"<img[^>]+src=[\"']([^\"']+)[\"']", html, flags=re.I):
        url = urljoin(base_url, match.group(1))
        if url not in urls:
            urls.append(url)
        lower = url.lower()
        if any(token in lower for token in ["quiniela", "progol", "protouch", "media"]):
            preferred.append(url)
    return preferred or urls


def _clean_snippet(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" -:.")
