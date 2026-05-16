"""Tests for ESPN structured fixture fallback."""

from __future__ import annotations

from src.data_sources.espn_client import parse_espn_events


def test_parse_espn_events_returns_structured_matches_with_market_line() -> None:
    payload = {
        "events": [
            {
                "date": "2026-05-15T02:00Z",
                "status": {"type": {"completed": False, "state": "pre"}},
                "competitions": [
                    {
                        "competitors": [
                            {"homeAway": "home", "team": {"displayName": "Equipo Local"}},
                            {"homeAway": "away", "team": {"displayName": "Equipo Visitante"}},
                        ],
                        "odds": [
                            {
                                "provider": {"name": "ESPN BET"},
                                "details": "LOCAL -120",
                                "homeTeamOdds": {"moneyLine": -120},
                                "awayTeamOdds": {"moneyLine": 180},
                                "drawOdds": {"moneyLine": 240},
                            }
                        ],
                    }
                ],
            }
        ]
    }

    matches = parse_espn_events(payload, "https://example.test/scoreboard", "Liga MX")

    assert matches == [
        {
            "id": 0,
            "local": "Equipo Local",
            "visitante": "Equipo Visitante",
            "liga": "Liga MX",
            "fecha": "2026-05-15T02:00Z",
            "fuente_partido": "https://example.test/scoreboard",
            "fuente_momio": "ESPN Scoreboard / ESPN BET",
            "linea_mercado": "LOCAL -120",
            "momio_texto": "LOCAL -120",
            "american_l": -120.0,
            "american_e": 240.0,
            "american_v": 180.0,
        }
    ]


def test_parse_espn_events_skips_completed_games() -> None:
    payload = {
        "events": [
            {
                "date": "2026-05-15T02:00Z",
                "status": {"type": {"completed": True, "state": "post"}},
                "competitions": [
                    {
                        "competitors": [
                            {"homeAway": "home", "team": {"displayName": "A"}},
                            {"homeAway": "away", "team": {"displayName": "B"}},
                        ]
                    }
                ],
            }
        ]
    }

    assert parse_espn_events(payload, "https://example.test/scoreboard", "Liga MX") == []
