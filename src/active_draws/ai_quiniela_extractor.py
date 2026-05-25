"""AI-assisted official quiniela extraction from image/PDF references."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from src.active_draws.draw_parser import base_draw
from src.active_draws.local_ocr_extractor import extract_text_from_image_payloads, parse_ocr_text_to_draw
from src.active_draws.official_guide_pdf import EXPECTED_MATCHES, extract_pdf_text, parse_guide_text
from src.ai.llm_clients import (
    anthropic_available,
    call_anthropic_json,
    call_openai_json,
    openai_available,
)


OFFICIAL_HOSTS = {"pronosticos.gob.mx", "www.pronosticos.gob.mx", "loterianacional.gob.mx", "www.loterianacional.gob.mx"}
SECONDARY_HOSTS = {"progol.es", "www.progol.es"}


def ai_extraction_enabled() -> bool:
    """Return whether optional AI extraction is enabled."""

    return os.getenv("ENABLE_AI_EXTRACTION", "true").lower() in {"1", "true", "yes", "si"}


def extract_draw_with_ai(
    game_id: str,
    game_name: str,
    source_urls: list[str],
    context_text: str = "",
    timeout_seconds: int = 45,
) -> tuple[dict | None, list[str]]:
    """Use configured AI providers to structure official quiniela references."""

    errors: list[str] = []
    if not ai_extraction_enabled():
        return None, ["Extraccion IA desactivada por ENABLE_AI_EXTRACTION."]
    allowed_urls = [url for url in source_urls if _is_allowed_reference_url(url)]
    if not allowed_urls:
        return None, ["Extraccion IA omitida: no hay URL oficial/secundaria permitida."]
    text_chunks = [context_text]
    images: list[dict[str, str]] = []
    errors.append(f"Extraccion automatica iniciada con {len(allowed_urls)} referencia(s) permitida(s).")
    for url in allowed_urls[:6]:
        content, mime_type, error = _fetch_binary(url, timeout_seconds=timeout_seconds)
        if error:
            errors.append(error)
            continue
        if mime_type.startswith("text/") or mime_type in {"application/xhtml+xml", "text/html"}:
            try:
                text_chunks.append(content.decode("utf-8", errors="replace")[:12000])
            except Exception:
                pass
        if mime_type == "application/pdf" or url.lower().split("?")[0].endswith(".pdf"):
            extracted_text, pdf_error = extract_pdf_text(content)
            if extracted_text:
                text_chunks.append(extracted_text[:12000])
            if pdf_error:
                errors.append(pdf_error)
            images.extend(_pdf_pages_as_images(content, max_pages=2))
        elif mime_type.startswith("image/"):
            images.append(_image_payload(content, mime_type))
    combined_text = "\n\n".join(chunk for chunk in text_chunks if chunk)
    errors.append(f"Extraccion automatica preparo {len(images)} imagen(es) y {len(combined_text)} caracteres de texto.")

    text_draw = _try_text_parse_draw(combined_text, game_id, game_name, allowed_urls[0])
    if text_draw:
        text_draw["source_warnings"] = list(
            dict.fromkeys([*(text_draw.get("source_warnings") or []), *errors])
        )
        return text_draw, errors

    ocr_text, ocr_errors = extract_text_from_image_payloads(images)
    errors.extend(ocr_errors)
    if ocr_text:
        ocr_draw = parse_ocr_text_to_draw(ocr_text, game_id, game_name, allowed_urls[0])
        if ocr_draw and _validate_draw(ocr_draw, game_id):
            ocr_draw["raw_text_preview"] = ocr_text[:4000]
            ocr_draw["source_warnings"] = list(
                dict.fromkeys([*(ocr_draw.get("source_warnings") or []), *errors])
            )
            return ocr_draw, errors
        combined_text = f"{combined_text}\n\nTexto OCR local:\n{ocr_text}"

    if not openai_available() and not anthropic_available():
        errors.append(
            "Extraccion IA por API omitida: configura OPENAI_API_KEY o ANTHROPIC_API_KEY para interpretar imagenes complejas."
        )
        return None, errors

    prompt = _build_prompt(game_id, game_name, combined_text, allowed_urls)
    responses = []
    if openai_available():
        responses.append(call_openai_json(prompt, images=images, timeout_seconds=timeout_seconds))
    if anthropic_available():
        responses.append(call_anthropic_json(prompt, images=images, timeout_seconds=timeout_seconds))
    for response in responses:
        if not response.ok:
            errors.append(response.error)
            continue
        parsed, parse_error = _parse_ai_json(response.text)
        if parse_error:
            errors.append(f"{response.provider}: {parse_error}")
            continue
        draw = _draw_from_ai_payload(parsed, game_id, game_name, allowed_urls[0], response.provider)
        if _validate_draw(draw, game_id):
            draw["source_warnings"] = list(
                dict.fromkeys([*(draw.get("source_warnings") or []), *errors])
            )
            return draw, errors
        errors.append(f"{response.provider}: respuesta IA sin partidos validos o conteo incorrecto.")
    return None, errors


def _try_text_parse_draw(text: str, game_id: str, game_name: str, official_url: str) -> dict | None:
    """Try deterministic text parsing before calling external AI providers."""

    if not text.strip():
        return None
    draw = parse_guide_text(text, game_id, game_name, official_url)
    if _validate_draw(draw, game_id):
        draw["raw_source"] = "texto_oficial_estructurado"
        return draw
    return None


def _build_prompt(game_id: str, game_name: str, context_text: str, source_urls: list[str]) -> str:
    expected = EXPECTED_MATCHES.get(game_id, 0)
    return f"""
Eres un extractor de datos deportivos. Extrae SOLO la quiniela oficial vigente de {game_name}.
Fuentes consultadas: {", ".join(source_urls)}
Numero esperado de partidos/casilleros: {expected or "desconocido"}.

Reglas:
- Devuelve exclusivamente JSON valido.
- No inventes equipos.
- Si no puedes leer un partido, omite ese partido.
- Usa equipo local y visitante tal como aparezcan en la guia/programa consultado.
- No uses calendarios genericos externos.
- Si la fuente es secundaria, extrae solo el programa/momios visible en esa fuente, no resultados historicos.

Formato:
{{
  "draw_number": "numero de concurso o Dato no disponible",
  "draw_date": "fecha o ventana de celebracion o Dato no disponible",
  "matches": [
    {{"id": 1, "local": "Equipo Local", "visitante": "Equipo Visitante", "liga": "Liga si aparece", "fecha": "fecha si aparece"}}
  ]
}}

Texto extraido disponible:
{context_text[:16000]}
""".strip()


def _draw_from_ai_payload(payload: dict[str, Any], game_id: str, game_name: str, official_url: str, provider: str) -> dict:
    draw = base_draw(game_id, game_name, "sports_pool", official_url, f"oficial_ia_{provider}", status="active")
    draw["draw_number"] = str(payload.get("draw_number") or "Dato no disponible")
    draw["draw_date"] = str(payload.get("draw_date") or "Dato no disponible")
    draw["data_freshness"] = "actualizada"
    draw["has_recent_sports_data"] = True
    source_label = "fuente oficial" if _is_official_url(official_url) else "fuente secundaria"
    draw["source_warnings"] = [
        f"Partidos estructurados por IA ({provider}) a partir de {source_label}. Validar visualmente antes de jugar."
    ]
    matches = []
    for raw in payload.get("matches", []) or []:
        try:
            match_id = int(raw.get("id"))
        except (TypeError, ValueError):
            continue
        local = _clean_team(raw.get("local"))
        visitante = _clean_team(raw.get("visitante"))
        if not local or not visitante:
            continue
        matches.append(
            {
                "id": match_id,
                "local": local,
                "visitante": visitante,
                "liga": str(raw.get("liga") or "Quiniela oficial"),
                "fecha": str(raw.get("fecha") or draw["draw_date"] or "Dato no disponible"),
                "fuente_partido": f"IA {provider} sobre guia oficial",
            }
        )
    draw["matches"] = _dedupe_matches(matches)
    return draw


def _validate_draw(draw: dict, game_id: str) -> bool:
    expected = EXPECTED_MATCHES.get(game_id, 0)
    matches = draw.get("matches") or []
    if expected and len(matches) != expected:
        return False
    if not all(match.get("local") and match.get("visitante") for match in matches):
        return False
    ids = sorted(int(match.get("id", 0)) for match in matches)
    if expected and ids != list(range(1, expected + 1)):
        return False
    return _is_allowed_reference_url(str(draw.get("official_url", "")))


def _parse_ai_json(text: str) -> tuple[dict[str, Any], str | None]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.I).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return {}, f"JSON invalido: {exc}"
    if not isinstance(payload, dict):
        return {}, "La respuesta no fue un objeto JSON."
    return payload, None


def _fetch_binary(url: str, timeout_seconds: int) -> tuple[bytes, str, str | None]:
    try:
        parsed = urllib.parse.urlparse(url)
        referer = f"{parsed.scheme}://{parsed.netloc}/"
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 QuinielaPredictorMX/0.1 (+official AI extractor)",
                "Accept": "text/html,application/pdf,image/avif,image/webp,image/png,image/jpeg,*/*",
                "Referer": referer,
            },
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            content = response.read()
            mime_type = response.headers.get_content_type() or mimetypes.guess_type(url)[0] or "application/octet-stream"
        return content, mime_type, None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return b"", "", f"No se pudo descargar referencia oficial {url}: {exc}"


def _pdf_pages_as_images(content: bytes, max_pages: int = 2) -> list[dict[str, str]]:
    try:
        import fitz  # type: ignore
    except ImportError:
        return []
    images = []
    try:
        with fitz.open(stream=content, filetype="pdf") as document:
            for page_index in range(min(max_pages, len(document))):
                page = document.load_page(page_index)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                images.append(_image_payload(pixmap.tobytes("png"), "image/png"))
    except Exception:
        return []
    return images


def _image_payload(content: bytes, mime_type: str) -> dict[str, str]:
    return {"mime_type": mime_type, "base64": base64.b64encode(content).decode("ascii")}


def _is_official_url(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    return host in OFFICIAL_HOSTS


def _is_allowed_reference_url(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    return host in OFFICIAL_HOSTS or host in SECONDARY_HOSTS


def _clean_team(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().upper()


def _dedupe_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {}
    for match in matches:
        by_id.setdefault(int(match["id"]), match)
    return [by_id[key] for key in sorted(by_id)]
