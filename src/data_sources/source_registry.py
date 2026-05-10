"""Registry of trusted web sources for active draws, fixtures and market odds."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class WebSource:
    """A configured source with usage rules."""

    source_id: str
    name: str
    url: str
    category: str
    priority: int
    games: tuple[str, ...]
    data_types: tuple[str, ...]
    access_mode: str
    notes: str
    env_var: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return serializable representation."""

        return asdict(self)


TRUSTED_WEB_SOURCES: tuple[WebSource, ...] = (
    WebSource(
        "pronosticos_progol",
        "Pronosticos/Loteria Nacional - Progol",
        "https://pronosticos.gob.mx/Progol/Quiniela",
        "official",
        100,
        ("progol", "progol_revancha"),
        ("active_draw", "fixtures", "official_results"),
        "public_html",
        "Fuente primaria para quiniela de la semana; puede publicar partidos como imagen.",
    ),
    WebSource(
        "pronosticos_media_semana",
        "Pronosticos/Loteria Nacional - Progol Media Semana",
        "https://pronosticos.gob.mx/ProgolMediaSemana/Quiniela",
        "official",
        100,
        ("progol_media_semana",),
        ("active_draw", "fixtures", "official_results"),
        "public_html",
        "Fuente primaria para Progol Media Semana.",
    ),
    WebSource(
        "pronosticos_protouch",
        "Pronosticos/Loteria Nacional - Protouch",
        "https://pronosticos.gob.mx/Protouch/Quiniela",
        "official",
        100,
        ("protouch",),
        ("active_draw", "fixtures", "official_results"),
        "public_html",
        "Fuente primaria para Protouch; puede requerir OCR si la quiniela esta en imagen.",
    ),
    WebSource(
        "loteria_resultados",
        "Loteria Nacional - Resultados",
        "https://www.loterianacional.gob.mx/Home/Resultados",
        "official",
        95,
        ("progol", "progol_revancha", "progol_media_semana", "protouch", "random_lottery"),
        ("official_results", "draw_metadata"),
        "public_html",
        "Fuente oficial para resultados y metadatos de sorteos.",
    ),
    WebSource(
        "tulotero_mx",
        "TuLotero Mexico",
        "https://tulotero.mx/",
        "authorized_sales_channel",
        80,
        ("progol", "random_lottery"),
        ("active_draw", "draw_metadata", "sales_channel"),
        "public_html_or_app",
        "Canal de venta autorizado; util para contrastar sorteos vigentes cuando expone contenido publico.",
    ),
    WebSource(
        "as_mexico_progol",
        "AS Mexico - Resultados Progol",
        "https://mexico.as.com/actualidad/",
        "media_results",
        55,
        ("progol", "progol_revancha"),
        ("official_results_summary",),
        "public_html",
        "Respaldo periodistico para resultados recientes, no sustituye fuente oficial.",
    ),
    WebSource(
        "caliente_liga_mx",
        "Caliente.mx - Liga MX",
        "https://sports.caliente.mx/es_MX/Liga-MX",
        "bookmaker",
        70,
        ("progol", "progol_media_semana"),
        ("market_odds", "fixtures"),
        "public_html_best_effort",
        "Momios de mercado; usar solo respetando terminos, disponibilidad geografica y acceso permitido.",
    ),
    WebSource(
        "caliente_futbol",
        "Caliente.mx - Futbol",
        "https://sports.caliente.mx/es_MX/Futbol",
        "bookmaker",
        65,
        ("progol", "progol_media_semana"),
        ("market_odds", "fixtures"),
        "public_html_best_effort",
        "Respaldo para momios de ligas internacionales cuando el HTML sea accesible.",
    ),
    WebSource(
        "bet365_football",
        "bet365 - Football Odds",
        "https://www.bet365.com/hub/en-us/football",
        "bookmaker",
        65,
        ("progol", "progol_media_semana"),
        ("market_odds", "fixtures"),
        "public_html_best_effort",
        "Momios 1X2 visibles en algunas regiones; no depender de scraping si requiere sesion o bloquea bots.",
    ),
    WebSource(
        "codere_mx",
        "Codere Mexico - Apuestas deportivas",
        "https://www.codere.mx/",
        "bookmaker",
        60,
        ("progol", "progol_media_semana", "protouch"),
        ("market_odds", "fixtures"),
        "public_html_best_effort",
        "Casa regulada en Mexico; usar solo contenido publico permitido o integracion oficial.",
    ),
    WebSource(
        "betcris_mx",
        "Betcris Mexico - Apuestas deportivas",
        "https://www.betcris.com.mx/",
        "bookmaker",
        60,
        ("progol", "progol_media_semana", "protouch"),
        ("market_odds", "fixtures"),
        "public_html_best_effort",
        "Referencia alternativa de mercado; puede requerir sesion o bloquear automatizacion.",
    ),
    WebSource(
        "betsson_mx",
        "Betsson Mexico - Apuestas deportivas",
        "https://www.betsson.mx/",
        "bookmaker",
        58,
        ("progol", "progol_media_semana", "protouch"),
        ("market_odds", "fixtures"),
        "public_html_best_effort",
        "Referencia alternativa para contrastar momios cuando el acceso publico lo permita.",
    ),
    WebSource(
        "the_odds_api",
        "The Odds API",
        "https://the-odds-api.com/",
        "odds_api",
        90,
        ("progol", "progol_media_semana", "protouch"),
        ("market_odds", "fixtures"),
        "api_key_required",
        "Proveedor estructurado de momios; configurar THE_ODDS_API_KEY en backend.",
        "THE_ODDS_API_KEY",
    ),
    WebSource(
        "odds_api_io",
        "Odds-API.io",
        "https://docs.odds-api.io/api-reference/introduction",
        "odds_api",
        88,
        ("progol", "progol_media_semana", "protouch"),
        ("market_odds", "fixtures"),
        "api_key_required",
        "Proveedor estructurado con bookmakers como Bet365; configurar ODDS_API_IO_KEY.",
        "ODDS_API_IO_KEY",
    ),
    WebSource(
        "football_data_org",
        "football-data.org",
        "https://www.football-data.org/",
        "sports_data_api",
        75,
        ("progol", "progol_media_semana"),
        ("fixtures", "results", "tables"),
        "api_key_required",
        "Fixtures, resultados y tablas; configurar FOOTBALL_DATA_API_KEY.",
        "FOOTBALL_DATA_API_KEY",
    ),
    WebSource(
        "api_football",
        "API-Football",
        "https://www.api-football.com/",
        "sports_data_api",
        76,
        ("progol", "progol_media_semana"),
        ("fixtures", "results", "standings", "odds"),
        "api_key_required",
        "Fuente estructurada para fixtures, resultados y estadisticas; configurar API_FOOTBALL_KEY.",
        "API_FOOTBALL_KEY",
    ),
    WebSource(
        "sports_game_odds_ligamx",
        "SportsGameOdds - Liga MX Odds API",
        "https://sportsgameodds.com/leagues/liga-mx-odds-api",
        "odds_api",
        80,
        ("progol", "progol_media_semana"),
        ("market_odds", "fixtures"),
        "api_key_required",
        "API de momios y eventos Liga MX; util para respaldo estructurado.",
        "SPORTS_GAME_ODDS_API_KEY",
    ),
)


def sources_for_game(game_id: str) -> list[WebSource]:
    """Return sources relevant to one game ordered by priority."""

    return sorted(
        [source for source in TRUSTED_WEB_SOURCES if game_id in source.games],
        key=lambda source: source.priority,
        reverse=True,
    )


def source_registry_as_dicts(game_id: str | None = None) -> list[dict[str, Any]]:
    """Return source registry for UI/API diagnostics."""

    sources = sources_for_game(game_id) if game_id else sorted(TRUSTED_WEB_SOURCES, key=lambda item: item.priority, reverse=True)
    return [source.as_dict() for source in sources]
