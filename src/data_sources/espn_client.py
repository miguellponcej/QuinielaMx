"""Public ESPN scoreboard connector for structured sports fixtures.

ESPN is used as a complementary fixture/market-line source when the official
Pronosticos page exposes a quiniela as an image instead of structured text.
The official draw page remains the primary source for the contest itself.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any


ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"

SOCCER_LEAGUES: tuple[tuple[str, str], ...] = (
    ("mex.1", "Liga MX"),
    ("mex.2", "Liga de Expansion MX"),
    ("usa.1", "MLS"),
    ("eng.1", "Premier League"),
    ("esp.1", "LaLiga"),
    ("ita.1", "Serie A"),
    ("ger.1", "Bundesliga"),
    ("fra.1", "Ligue 1"),
    ("uefa.champions", "UEFA Champions League"),
)

FOOTBALL_LEAGUES: tuple[tuple[str, str], ...] = (
    ("nfl", "NFL"),
    ("college-football", "NCAA Football"),
)


def fetch_soccer_fixtures(limit: int = 14, timeout_seconds: int = 8) -> tuple[list[dict], list[str], list[str]]:
    """Fetch upcoming soccer fixtures from public ESPN scoreboards."""

    return _fetch_fixture_group(
        sport="soccer",
        leagues=SOCCER_LEAGUES,
        limit=limit,
        timeout_seconds=timeout_seconds,
        game_type="soccer",
    )


def fetch_football_fixtures(limit: int = 13, timeout_seconds: int = 8) -> tuple[list[dict], list[str], list[str]]:
    """Fetch upcoming NFL/NCAA football fixtures from public ESPN scoreboards."""

    return _fetch_fixture_group(
        sport="football",
        leagues=FOOTBALL_LEAGUES,
        limit=limit,
        timeout_seconds=timeout_seconds,
        game_type="football",
    )


def parse_espn_events(payload: dict[str, Any], source_url: str, league_name: str) -> list[dict]:
    """Parse ESPN scoreboard JSON into the app's match schema."""

    matches: list[dict] = []
    for event in payload.get("events", []) or []:
        competition = _first(event.get("competitions"))
        if not isinstance(competition, dict):
            continue
        status = event.get("status", {}).get("type", {})
        if bool(status.get("completed")) or str(status.get("state", "")).lower() == "post":
            continue
        competitors = competition.get("competitors") or []
        home = _find_competitor(competitors, "home")
        away = _find_competitor(competitors, "away")
        if not home or not away:
            continue
        market = _extract_market_line(competition)
        match = {
            "id": 0,
            "local": _team_name(home),
            "visitante": _team_name(away),
            "liga": league_name,
            "fecha": str(event.get("date") or "Dato no disponible"),
            "fuente_partido": source_url,
            "fuente_momio": market["source"],
            "linea_mercado": market["line"],
            "momio_texto": market["line"],
        }
        match.update(market["odds"])
        matches.append(match)
    return matches


def _fetch_fixture_group(
    sport: str,
    leagues: tuple[tuple[str, str], ...],
    limit: int,
    timeout_seconds: int,
    game_type: str,
) -> tuple[list[dict], list[str], list[str]]:
    errors: list[str] = []
    sources: list[str] = []
    matches: list[dict] = []
    for league_code, league_name in leagues:
        url = _scoreboard_url(sport, league_code)
        sources.append(url)
        payload, error = _fetch_json(url, timeout_seconds)
        if error:
            errors.append(error)
            continue
        matches.extend(parse_espn_events(payload, url, league_name))
    matches = _dedupe_matches(matches)
    matches.sort(key=lambda item: str(item.get("fecha", "")))
    matches = matches[:limit]
    for idx, match in enumerate(matches, start=1):
        match["id"] = idx
        match["fuente_partido"] = match.get("fuente_partido") or f"ESPN Scoreboard {game_type}"
    return matches, errors, sources


def _scoreboard_url(sport: str, league_code: str) -> str:
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=21)
    query = urllib.parse.urlencode(
        {
            "dates": f"{now:%Y%m%d}-{end:%Y%m%d}",
            "limit": "100",
        }
    )
    return f"{ESPN_BASE_URL}/{sport}/{league_code}/scoreboard?{query}"


def _fetch_json(url: str, timeout_seconds: int) -> tuple[dict[str, Any], str | None]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "QuinielaPredictorMX/0.1 (+private personal sports updater)",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            content = response.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return {}, f"No fue posible consultar ESPN Scoreboard {url}: {exc}"
    except TimeoutError:
        return {}, f"Timeout consultando ESPN Scoreboard {url}"
    except OSError as exc:
        return {}, f"Error de red consultando ESPN Scoreboard {url}: {exc}"
    try:
        return json.loads(content), None
    except json.JSONDecodeError as exc:
        return {}, f"ESPN Scoreboard respondio con JSON invalido {url}: {exc}"


def _first(values: object) -> object | None:
    if isinstance(values, list) and values:
        return values[0]
    return None


def _find_competitor(competitors: list[dict], home_away: str) -> dict | None:
    for competitor in competitors:
        if str(competitor.get("homeAway", "")).lower() == home_away:
            return competitor
    return None


def _team_name(competitor: dict) -> str:
    team = competitor.get("team") or {}
    return str(team.get("displayName") or team.get("name") or team.get("shortDisplayName") or "").strip()


def _extract_market_line(competition: dict) -> dict[str, Any]:
    odds_entry = _first(competition.get("odds")) or {}
    if not isinstance(odds_entry, dict):
        odds_entry = {}
    provider = odds_entry.get("provider") or {}
    provider_name = provider.get("name") if isinstance(provider, dict) else ""
    source = f"ESPN Scoreboard / {provider_name}".strip(" /") if provider_name else "ESPN Scoreboard"
    line = str(odds_entry.get("details") or odds_entry.get("summary") or "Dato no disponible")
    return {
        "source": source,
        "line": line,
        "odds": _extract_odds_fields(odds_entry),
    }


def _extract_odds_fields(odds_entry: dict) -> dict[str, float]:
    fields: dict[str, float] = {}
    mapping = {
        "L": ("homeTeamOdds", "homeOdds", "home"),
        "E": ("drawOdds", "tieOdds", "draw"),
        "V": ("awayTeamOdds", "awayOdds", "away"),
    }
    for option, keys in mapping.items():
        value = None
        for key in keys:
            raw = odds_entry.get(key)
            value = _extract_american_or_decimal(raw)
            if value is not None:
                break
        if value is not None:
            fields[f"american_{option.lower()}"] = value
    return fields


def _extract_american_or_decimal(raw: object) -> float | None:
    if isinstance(raw, (int, float)):
        return float(raw)
    if not isinstance(raw, dict):
        return None
    for key in ("moneyLine", "american", "americanOdds", "odds"):
        value = raw.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _dedupe_matches(matches: list[dict]) -> list[dict]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict] = []
    for match in matches:
        key = (
            str(match.get("local", "")).lower(),
            str(match.get("visitante", "")).lower(),
            str(match.get("fecha", ""))[:10],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(match)
    return deduped
