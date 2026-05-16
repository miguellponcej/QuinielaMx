"""Responsible client for official/configured active draw sources."""

from __future__ import annotations

import urllib.error
import urllib.request
import os
import http.client
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from src.active_draws.draw_parser import base_draw, parse_home_results, parse_quiniela_page, parse_tulotero_home
from src.data_sources.espn_client import fetch_football_fixtures, fetch_soccer_fixtures
from src.data_sources.source_registry import TRUSTED_WEB_SOURCES, WebSource


OFFICIAL_URLS = {
    "home_results": "https://www.loterianacional.gob.mx/Home/Resultados",
    "data_open": "https://www.loterianacional.gob.mx/DatosAbiertos/NumerosGanadores",
    "progol": "https://pronosticos.gob.mx/Progol/Quiniela",
    "progol_revancha": "https://pronosticos.gob.mx/Progol/Quiniela",
    "progol_media_semana": "https://pronosticos.gob.mx/ProgolMediaSemana/Quiniela",
    "protouch": "https://pronosticos.gob.mx/Protouch/Quiniela",
    "tulotero": "https://tulotero.mx/",
}


@dataclass(frozen=True)
class FetchResult:
    """Fetch result with diagnostics."""

    ok: bool
    draws: list[dict]
    errors: list[str]
    sources: list[str]


class OfficialSourcesClient:
    """Fetch official public pages with timeouts and safe fallbacks."""

    def __init__(self, timeout_seconds: int = 8) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch_official_active_draws(self) -> FetchResult:
        """Fetch all configured official active draw sources."""

        draws: list[dict] = []
        errors: list[str] = []
        sources: list[str] = []
        fetchers = [
            self.fetch_active_lottery_draws,
            self.fetch_active_tulotero_draws,
            self.fetch_active_progol,
            self.fetch_active_progol_revancha,
            self.fetch_active_progol_media_semana,
            self.fetch_active_protouch,
        ]
        with ThreadPoolExecutor(max_workers=len(fetchers)) as executor:
            for future in as_completed([executor.submit(fetcher) for fetcher in fetchers]):
                try:
                    result = future.result()
                except Exception as exc:
                    result = FetchResult(ok=False, draws=[], errors=[f"Error inesperado consultando fuente: {exc}"], sources=[])
                draws.extend(result.draws)
                errors.extend(result.errors)
                sources.extend(result.sources)
        deduped = _dedupe_draws(draws)
        return FetchResult(ok=bool(deduped) and len(errors) < len(sources or [1]), draws=deduped, errors=errors, sources=sources)

    def probe_trusted_sources(self) -> list[dict]:
        """Probe trusted web sources without extracting protected content."""

        diagnostics_by_id = {}
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(self._probe_source, source): source for source in TRUSTED_WEB_SOURCES}
            for future in as_completed(futures):
                source = futures[future]
                try:
                    status, error = future.result()
                except Exception as exc:
                    status, error = "unavailable", f"Error inesperado al diagnosticar fuente: {exc}"
                diagnostics_by_id[source.source_id] = {
                    **source.as_dict(),
                    "status": status,
                    "error": error or "",
                }
        return [diagnostics_by_id[source.source_id] for source in TRUSTED_WEB_SOURCES]

    def fetch_active_progol(self) -> FetchResult:
        """Fetch active Progol page."""

        return self._fetch_sports_pool("progol", "Progol", OFFICIAL_URLS["progol"])

    def fetch_active_progol_revancha(self) -> FetchResult:
        """Fetch active Progol Revancha page."""

        return self._fetch_sports_pool("progol_revancha", "Progol Revancha", OFFICIAL_URLS["progol_revancha"])

    def fetch_active_progol_media_semana(self) -> FetchResult:
        """Fetch active Progol Media Semana page."""

        return self._fetch_sports_pool(
            "progol_media_semana",
            "Progol Media Semana",
            OFFICIAL_URLS["progol_media_semana"],
        )

    def fetch_active_protouch(self) -> FetchResult:
        """Fetch active Protouch page."""

        return self._fetch_sports_pool("protouch", "Protouch", OFFICIAL_URLS["protouch"])

    def fetch_active_lottery_draws(self) -> FetchResult:
        """Fetch active/random lottery summary from official results page."""

        url = OFFICIAL_URLS["home_results"]
        html, error = self._fetch_url(url)
        if error:
            return FetchResult(ok=False, draws=[], errors=[error], sources=[url])
        return FetchResult(ok=True, draws=parse_home_results(html, url), errors=[], sources=[url])

    def fetch_active_tulotero_draws(self) -> FetchResult:
        """Fetch public TuLotero snippets as a secondary vigency source."""

        url = OFFICIAL_URLS["tulotero"]
        html, error = self._fetch_url(url)
        if error:
            return FetchResult(ok=False, draws=[], errors=[error], sources=[url])
        return FetchResult(ok=True, draws=parse_tulotero_home(html, url), errors=[], sources=[url])

    def _fetch_sports_pool(self, game_id: str, game_name: str, url: str) -> FetchResult:
        html, error = self._fetch_url(url)
        if error:
            draw = base_draw(game_id, game_name, "sports_pool", url, "oficial_quiniela")
            draw["source_errors"].append(error)
            return FetchResult(ok=False, draws=[draw], errors=[error], sources=[url])
        draw = parse_quiniela_page(html, game_id, game_name, url)
        fixture_errors: list[str] = []
        fixture_sources: list[str] = []
        if not draw.get("matches"):
            matches, fixture_errors, fixture_sources = self._fetch_structured_fixture_fallback(game_id)
            if matches:
                _attach_fixture_fallback(draw, matches, fixture_sources)
        sources = [url, *fixture_sources]
        errors = fixture_errors if not draw.get("matches") else []
        return FetchResult(ok=bool(draw.get("matches")) or not errors, draws=[draw], errors=errors, sources=sources)

    def _fetch_structured_fixture_fallback(self, game_id: str) -> tuple[list[dict], list[str], list[str]]:
        if game_id == "protouch":
            return fetch_football_fixtures(limit=13, timeout_seconds=self.timeout_seconds)
        if game_id in {"progol", "progol_revancha", "progol_media_semana"}:
            return fetch_soccer_fixtures(limit=14, timeout_seconds=self.timeout_seconds)
        return [], [], []

    def _fetch_url(self, url: str) -> tuple[str, str | None]:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "QuinielaPredictorMX/0.1 (+private personal data updater; responsible scraping)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read().decode("utf-8", errors="replace"), None
        except urllib.error.URLError as exc:
            return "", f"No fue posible consultar {url}: {exc}"
        except TimeoutError:
            return "", f"Timeout consultando {url}"
        except http.client.IncompleteRead as exc:
            return "", f"Respuesta incompleta consultando {url}: {exc}"
        except OSError as exc:
            return "", f"Error de red consultando {url}: {exc}"

    def _probe_source(self, source: WebSource) -> tuple[str, str | None]:
        if source.access_mode == "api_key_required":
            if source.env_var and os.getenv(source.env_var):
                return "api_key_configured", None
            return "requires_api_key", f"Requiere {source.env_var or 'API key'} configurada en backend."
        html, error = self._fetch_url(source.url)
        if error:
            return "unavailable", error
        if html.strip():
            return "reachable", None
        return "empty_response", "La fuente respondio sin contenido util."


def _dedupe_draws(draws: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result = []
    for draw in draws:
        key = str(draw.get("game_id"))
        if key not in seen:
            seen.add(key)
            result.append(draw)
        else:
            existing = next(item for item in result if str(item.get("game_id")) == key)
            _merge_draw(existing, draw)
    return result


def _merge_draw(existing: dict, incoming: dict) -> None:
    """Merge duplicated draw records without discarding source evidence."""

    existing.setdefault("alternate_sources", [])
    incoming_url = incoming.get("official_url")
    if incoming_url and incoming_url != existing.get("official_url"):
        existing["alternate_sources"].append(incoming_url)
    for field in [
        "draw_number",
        "closing_date",
        "draw_date",
        "estimated_prize",
        "accumulated_pool",
        "cost_per_entry",
        "status",
    ]:
        if _is_missing(existing.get(field)) and not _is_missing(incoming.get(field)):
            existing[field] = incoming[field]
    if incoming.get("raw_source") == "oficial_quiniela":
        existing["official_url"] = incoming.get("official_url", existing.get("official_url"))
    existing["matches"] = existing.get("matches") or incoming.get("matches") or []
    existing["source_errors"] = list(
        dict.fromkeys([*(existing.get("source_errors") or []), *(incoming.get("source_errors") or [])])
    )
    existing["source_artifacts"] = [*(existing.get("source_artifacts") or []), *(incoming.get("source_artifacts") or [])]
    if incoming.get("data_freshness") == "actualizada":
        existing["data_freshness"] = "actualizada"
    existing["raw_source"] = "+".join(dict.fromkeys([existing.get("raw_source", ""), incoming.get("raw_source", "")]))


def _is_missing(value: object) -> bool:
    return value in (None, "", "Dato no disponible")


def _attach_fixture_fallback(draw: dict, matches: list[dict], sources: list[str]) -> None:
    """Attach structured fixtures while preserving source transparency."""

    draw["matches"] = matches
    draw["status"] = "active"
    draw["data_freshness"] = "actualizada"
    draw["raw_source"] = f"{draw.get('raw_source', '')}+espn_scoreboard"
    draw["has_recent_sports_data"] = True
    draw["has_market_data"] = any(match.get("linea_mercado") not in (None, "", "Dato no disponible") for match in matches)
    if _is_missing(draw.get("draw_date")) and matches:
        draw["draw_date"] = matches[0].get("fecha", "Dato no disponible")
    draw.setdefault("alternate_sources", [])
    draw["alternate_sources"] = list(dict.fromkeys([*draw["alternate_sources"], *sources]))
    previous_errors = draw.get("source_errors") or []
    warning = (
        "La fuente oficial no entrego partidos como texto. Se uso ESPN Scoreboard como "
        "fuente deportiva estructurada complementaria; validar contra el volante oficial antes de jugar."
    )
    draw["source_warnings"] = list(dict.fromkeys([*previous_errors, warning]))
    draw["source_errors"] = []
