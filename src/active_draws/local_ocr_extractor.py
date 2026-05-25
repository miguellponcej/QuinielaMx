"""Local OCR fallback for official quiniela images.

This module intentionally does not invent teams. It only returns structured
matches when OCR text contains enough separators to identify local and visitor.
"""

from __future__ import annotations

import base64
import io
import os
import re
from typing import Any

from src.active_draws.draw_parser import base_draw
from src.active_draws.official_guide_pdf import EXPECTED_MATCHES, parse_guide_text


def local_ocr_enabled() -> bool:
    """Return whether local OCR is enabled."""

    return os.getenv("ENABLE_LOCAL_OCR", "true").lower() in {"1", "true", "yes", "si"}


def extract_text_from_image_payloads(
    image_payloads: list[dict[str, str]],
    lang: str | None = None,
) -> tuple[str, list[str]]:
    """Extract text from base64 image payloads using local Tesseract when available."""

    diagnostics: list[str] = []
    if not local_ocr_enabled():
        return "", ["OCR local desactivado por ENABLE_LOCAL_OCR."]
    if not image_payloads:
        return "", ["OCR local omitido: no hay imagenes para leer."]
    try:
        import pytesseract  # type: ignore
        from PIL import Image, ImageEnhance, ImageOps  # type: ignore
    except ImportError:
        return "", ["OCR local no disponible: faltan pillow/pytesseract."]
    try:
        pytesseract.get_tesseract_version()
    except Exception as exc:
        return "", [f"OCR local no disponible: Tesseract no esta instalado o no responde ({exc})."]

    ocr_lang = lang or os.getenv("LOCAL_OCR_LANG", "spa+eng")
    texts: list[str] = []
    for index, payload in enumerate(image_payloads, start=1):
        try:
            raw = base64.b64decode(payload.get("base64", ""))
            image = Image.open(io.BytesIO(raw))
            image = _prepare_image_for_ocr(image, ImageEnhance, ImageOps)
            text = pytesseract.image_to_string(image, lang=ocr_lang, config="--psm 6")
            if text.strip():
                texts.append(text)
                diagnostics.append(f"OCR local leyo imagen {index} con {len(text.strip())} caracteres.")
            else:
                diagnostics.append(f"OCR local no encontro texto util en imagen {index}.")
        except Exception as exc:
            diagnostics.append(f"OCR local fallo en imagen {index}: {exc}")
    return "\n\n".join(texts), diagnostics


def parse_ocr_text_to_draw(text: str, game_id: str, game_name: str, official_url: str) -> dict | None:
    """Convert OCR text to a draw only when the expected program can be validated."""

    if not text.strip():
        return None
    guide_draw = parse_guide_text(text, game_id, game_name, official_url)
    if _draw_has_expected_matches(guide_draw, game_id):
        guide_draw["raw_source"] = "ocr_local_guia_pdf"
        guide_draw["source_warnings"] = list(
            dict.fromkeys(
                [
                    *(guide_draw.get("source_warnings") or []),
                    "Partidos estructurados con OCR local gratuito sobre imagen/PDF oficial.",
                ]
            )
        )
        return guide_draw

    rows = _parse_numbered_vs_rows(text)
    if not rows:
        return None
    draw = base_draw(game_id, game_name, "sports_pool", official_url, "ocr_local", status="active")
    draw["draw_number"] = _extract_draw_number(text)
    draw["draw_date"] = _extract_draw_date(text)
    draw["data_freshness"] = "actualizada"
    draw["has_recent_sports_data"] = True
    draw["source_warnings"] = [
        "Partidos estructurados con OCR local gratuito. Validar visualmente la guia oficial antes de jugar."
    ]
    draw["matches"] = [
        {
            "id": match_id,
            "local": local,
            "visitante": visitante,
            "liga": "Quiniela oficial",
            "fecha": draw["draw_date"],
            "fuente_partido": "OCR local sobre guia oficial",
        }
        for match_id, local, visitante in rows
    ]
    return draw if _draw_has_expected_matches(draw, game_id) else None


def _prepare_image_for_ocr(image: Any, image_enhance: Any, image_ops: Any) -> Any:
    image = image.convert("L")
    width, height = image.size
    if max(width, height) < 1800:
        image = image.resize((width * 2, height * 2))
    image = image_ops.autocontrast(image)
    image = image_enhance.Contrast(image).enhance(1.8)
    return image.point(lambda pixel: 255 if pixel > 165 else 0)


def _parse_numbered_vs_rows(text: str) -> list[tuple[int, str, str]]:
    rows: dict[int, tuple[int, str, str]] = {}
    for raw_line in text.splitlines():
        line = _clean_ocr_line(raw_line)
        if not line:
            continue
        match = re.match(r"^(?:CASILLERO\s*)?(\d{1,2})[\).:\-\s]+(.+)$", line, flags=re.I)
        if not match:
            continue
        match_id = int(match.group(1))
        body = _remove_market_columns(match.group(2))
        parsed = _split_vs_body(body)
        if parsed:
            local, visitante = parsed
            rows.setdefault(match_id, (match_id, local, visitante))
    return [rows[key] for key in sorted(rows)]


def _split_vs_body(body: str) -> tuple[str, str] | None:
    parts = re.split(r"\b(?:VS|V\.|VERSUS)\b", body, maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return None
    local = _clean_team(parts[0])
    visitante = _clean_team(parts[1])
    if local and visitante:
        return local, visitante
    return None


def _remove_market_columns(value: str) -> str:
    value = re.sub(r"\bLOCAL\b|\bEMPATE\b|\bVISITA(?:NTE)?\b", " ", value, flags=re.I)
    value = re.sub(r"\b\d+(?:[.,]\d+)?\b\s*$", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _clean_team(value: str) -> str:
    value = re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9&.' -]", " ", value)
    value = re.sub(r"\b\d+(?:[.,]\d+)?\b", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" -:.|")
    if len(value) < 2:
        return ""
    return value.upper()


def _clean_ocr_line(value: str) -> str:
    value = value.replace("|", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _draw_has_expected_matches(draw: dict, game_id: str) -> bool:
    expected = EXPECTED_MATCHES.get(game_id, 0)
    matches = draw.get("matches") or []
    if expected and len(matches) != expected:
        return False
    ids = sorted(int(match.get("id", 0)) for match in matches)
    return not expected or ids == list(range(1, expected + 1))


def _extract_draw_number(text: str) -> str:
    match = re.search(r"\b(?:CONCURSO|JUEGO|SORTEO)\s*(?:NO\.?|NUM\.?|#)?\s*(\d+)\b", text, flags=re.I)
    return match.group(1) if match else "Dato no disponible"


def _extract_draw_date(text: str) -> str:
    match = re.search(
        r"(?:Juegos?\s+del|Fecha(?:\s+de\s+sorteo)?[:\s]+)(.{6,90}?)(?:\n|$)",
        text,
        flags=re.I,
    )
    return re.sub(r"\s+", " ", match.group(1)).strip(" -:.") if match else "Dato no disponible"
