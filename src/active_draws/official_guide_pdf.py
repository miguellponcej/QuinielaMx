"""Parser for official Progol/Protouch guide PDFs.

The official quiniela pages can publish the playable list as a rendered image,
while the "Guia de la Quiniela" PDF often contains extractable text with the
contest number, date window and casilleros. This module only accepts official
PDFs linked from the official page.
"""

from __future__ import annotations

import io
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from src.active_draws.draw_parser import NOT_AVAILABLE, base_draw


EXPECTED_MATCHES = {
    "progol": 14,
    "progol_revancha": 7,
    "progol_media_semana": 9,
    "protouch": 13,
}


def extract_guide_pdf_urls(html: str, base_url: str, game_id: str) -> list[str]:
    """Extract official guide PDF URLs from an official game page."""

    urls: list[str] = []
    for match in re.finditer(r"href=[\"']([^\"']+\.pdf(?:\?[^\"']*)?)[\"']", html, flags=re.I):
        url = urllib.parse.urljoin(base_url, match.group(1))
        lower = url.lower()
        if game_id == "progol_media_semana" and "progol_media_guia_quiniela" not in lower:
            continue
        if game_id in {"progol", "progol_revancha"} and "progol_guia_quiniela" not in lower:
            continue
        if game_id == "protouch" and "protouch_guia_quiniela" not in lower:
            continue
        if url not in urls:
            urls.append(url)
    return urls


def fetch_guide_pdf_draw(
    url: str,
    game_id: str,
    game_name: str,
    timeout_seconds: int = 8,
) -> tuple[dict | None, str | None]:
    """Fetch and parse one official guide PDF."""

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "QuinielaPredictorMX/0.1 (+official guide reader)",
            "Accept": "application/pdf,*/*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            content = response.read()
    except urllib.error.URLError as exc:
        return None, f"No fue posible consultar guia oficial {url}: {exc}"
    except TimeoutError:
        return None, f"Timeout consultando guia oficial {url}"
    except OSError as exc:
        return None, f"Error de red consultando guia oficial {url}: {exc}"

    text, error = extract_pdf_text(content)
    if error:
        return None, error
    draw = parse_guide_text(text, game_id, game_name, url)
    if draw.get("matches"):
        return draw, None
    return draw, "La guia oficial se consulto, pero no se pudieron estructurar los casilleros."


def extract_pdf_text(content: bytes) -> tuple[str, str | None]:
    """Extract text from PDF bytes using optional pypdf."""

    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        return "", "No se pudo leer la guia PDF: falta instalar pypdf."
    try:
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text, None
    except Exception as exc:
        return "", f"No se pudo extraer texto de la guia PDF oficial: {exc}"


def parse_guide_text(text: str, game_id: str, game_name: str, official_url: str) -> dict:
    """Parse contest metadata and matches from extracted guide text."""

    draw = base_draw(game_id, game_name, "sports_pool", official_url, "oficial_guia_pdf", status="active")
    normalized = _normalize_text(text)
    number = re.search(r"CONCURSO\s+(\d+)", normalized, flags=re.I)
    if number:
        draw["draw_number"] = number.group(1)
    window = re.search(r"Juegos?\s+del\s+(.+?)(?=\s+BOLSA|\s+CASILLERO|\s+LOCAL|\s+VISITANTE|$)", normalized, flags=re.I)
    if window:
        draw["draw_date"] = _clean(window.group(1))
    matches = parse_casilleros(text, EXPECTED_MATCHES.get(game_id, 0))
    draw["matches"] = matches
    draw["raw_text_preview"] = normalized[:4000]
    draw["data_freshness"] = "actualizada"
    draw["has_recent_sports_data"] = bool(matches)
    draw["source_warnings"] = [
        "Partidos extraidos de la Guia de la Quiniela oficial enlazada por Loteria Nacional."
    ]
    if not matches:
        draw["source_errors"].append("La guia oficial no pudo convertirse a partidos estructurados.")
    return draw


def parse_casilleros(text: str, expected: int) -> list[dict[str, Any]]:
    """Parse casillero rows from PDF text."""

    matches: list[dict[str, Any]] = []
    lines = [_clean(line) for line in text.splitlines() if _clean(line)]
    for idx, line in enumerate(lines):
        slot = re.search(r"CASILLERO\s+(\d+)", line, flags=re.I)
        if not slot:
            continue
        match_id = int(slot.group(1))
        local = visitante = ""
        scan = _casillero_block(lines, idx)
        for candidate in scan:
            parsed = _parse_versus_line(candidate)
            if parsed:
                local, visitante = parsed
                break
        if not local or not visitante:
            parsed = _parse_neighbor_lines(scan)
            if parsed:
                local, visitante = parsed
        if local and visitante:
            matches.append(
                {
                    "id": match_id,
                    "local": local,
                    "visitante": visitante,
                    "liga": "Quiniela oficial",
                    "fecha": "Dato no disponible",
                    "fuente_partido": "Guia oficial de la Quiniela",
                }
            )
    deduped = _dedupe_by_id(matches)
    if expected and len(deduped) > expected:
        deduped = deduped[:expected]
    return deduped


def _parse_versus_line(line: str) -> tuple[str, str] | None:
    if " VS " not in f" {line.upper()} ":
        return None
    parts = re.split(r"\bVS\b", line, maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return None
    local = _team_name(parts[0])
    visitante = _team_name(parts[1])
    if local and visitante:
        return local, visitante
    return None


def _casillero_block(lines: list[str], start_idx: int) -> list[str]:
    block = [lines[start_idx]]
    for line in lines[start_idx + 1 :]:
        if re.search(r"CASILLERO\s+\d+", line, flags=re.I):
            break
        block.append(line)
    return block[:10]


def _parse_neighbor_lines(lines: list[str]) -> tuple[str, str] | None:
    for idx, line in enumerate(lines):
        if line.upper() == "VS" and idx > 0 and idx + 1 < len(lines):
            previous = idx - 1
            while previous >= 0 and re.search(r"CASILLERO\s+\d+", lines[previous], flags=re.I):
                previous -= 1
            if previous < 0:
                continue
            local = _team_name(lines[previous])
            visitante = _team_name(lines[idx + 1])
            if local and visitante:
                return local, visitante
    return None


def _team_name(value: str) -> str:
    value = re.sub(r"CASILLERO\s+\d+", " ", value, flags=re.I)
    value = re.sub(r"\bLOCAL\b|\bVISITANTE\b", " ", value, flags=re.I)
    value = re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9&.' -]", " ", value)
    value = _clean(value)
    value = re.sub(r"\b(Jornada|Liga|Último|Ultimo|resultado|se|ubica|encuentra)\b.*$", "", value, flags=re.I)
    return _clean(value).upper()


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" -:.|")


def _dedupe_by_id(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[int, dict[str, Any]] = {}
    for match in matches:
        by_id.setdefault(int(match["id"]), match)
    return [by_id[key] for key in sorted(by_id)]
