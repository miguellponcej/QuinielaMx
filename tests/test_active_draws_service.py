from src.active_draws.active_draws_service import get_active_draws
from src.active_draws.draw_cache import is_cache_fresh, load_active_draws_cache, save_active_draws_cache
from src.active_draws.draw_parser import base_draw
from src.active_draws.draw_validator import apply_validation
from src.active_draws.official_sources_client import FetchResult


class FakeClient:
    def __init__(self, result):
        self.result = result

    def fetch_official_active_draws(self):
        return self.result

    def probe_trusted_sources(self):
        return [{"source_id": "fake", "name": "Fake", "status": "reachable"}]


def test_detect_active_draws_from_client():
    draw = base_draw("progol", "Progol", "sports_pool", "https://official", "test", status="active")
    draw["matches"] = [{"local": "A", "visitante": "B"} for _ in range(14)]
    result = FetchResult(ok=True, draws=[draw], errors=[], sources=["https://official"])

    payload = get_active_draws(force_refresh=True, client=FakeClient(result), user_email="test@example.com")

    assert payload["summary"]["total_games"] == 1
    assert payload["draws"][0]["game_name"] == "Progol"
    assert "recommendation" in payload["draws"][0]
    assert payload["source_diagnostics"][0]["source_id"] == "fake"


def test_uses_cache_if_web_fails():
    cached = base_draw("melate", "Melate", "random_lottery", "https://official", "cache", status="active")
    save_active_draws_cache([cached])
    result = FetchResult(ok=False, draws=[], errors=["sin internet"], sources=["https://official"])

    payload = get_active_draws(force_refresh=True, client=FakeClient(result), user_email="test@example.com")

    assert payload["used_cache"]
    assert payload["draws"][0]["game_name"] == "Melate"


def test_incomplete_draw_reports_missing_fields():
    draw = base_draw("protouch", "Protouch", "sports_pool", "https://official", "test", status="active")
    result = FetchResult(ok=True, draws=[draw], errors=[], sources=["https://official"])

    payload = get_active_draws(force_refresh=True, client=FakeClient(result), user_email="test@example.com")

    assert payload["draws"][0]["missing_fields"]
    assert payload["summary"]["incomplete_games"] == 1


def test_corrupt_cache_is_ignored(tmp_path):
    cache_path = tmp_path / "bad_cache.json"
    cache_path.write_text("{bad json", encoding="utf-8")

    assert load_active_draws_cache(cache_path) is None
    assert not is_cache_fresh(cache_path=cache_path)


def test_expired_draw_is_marked_closed():
    draw = base_draw("progol", "Progol", "sports_pool", "https://official", "test", status="active")
    draw["closing_date"] = "2000-01-01T00:00:00+00:00"

    validated = apply_validation(draw)

    assert validated["status"] == "closed"
    assert "La fecha limite parece vencida." in validated["validation"]["warnings"]


def test_closed_sports_result_without_matches_is_not_shown():
    draw = base_draw("progol", "Progol", "sports_pool", "https://official/results", "oficial_home_resultados", status="closed")
    draw["draw_number"] = "2332"
    draw["draw_date"] = "11/05/2026"
    result = FetchResult(ok=True, draws=[draw], errors=[], sources=["https://official/results"])

    payload = get_active_draws(force_refresh=True, client=FakeClient(result), user_email="test@example.com")

    assert payload["draws"] == []
    assert payload["summary"]["sports_pools"] == 0


def test_official_future_matches_override_past_result_date():
    result_draw = base_draw(
        "progol",
        "Progol",
        "sports_pool",
        "https://official/results",
        "oficial_home_resultados",
        status="closed",
    )
    result_draw["draw_number"] = "2332"
    result_draw["draw_date"] = "11/05/2026"
    active_draw = base_draw(
        "progol",
        "Progol",
        "sports_pool",
        "https://official/quiniela",
        "oficial_quiniela_structured",
        status="active",
    )
    active_draw["draw_date"] = "2099-01-01T12:00:00+00:00"
    active_draw["matches"] = [
        {"id": idx, "local": "A", "visitante": "B", "liga": "Liga", "fecha": "2099-01-01T12:00:00+00:00"}
        for idx in range(1, 15)
    ]
    result = FetchResult(ok=True, draws=[result_draw, active_draw], errors=[], sources=["https://official"])

    payload = get_active_draws(force_refresh=True, client=FakeClient(result), user_email="test@example.com")

    assert payload["summary"]["sports_pools"] == 1
    assert payload["draws"][0]["status"] == "active"
    assert payload["draws"][0]["draw_date"] == "2099-01-01T12:00:00+00:00"
    assert len(payload["draws"][0]["matches"]) == 14


def test_official_quiniela_reference_survives_closed_results_record():
    result_draw = base_draw(
        "progol_media_semana",
        "Progol Media Semana",
        "sports_pool",
        "https://official/results",
        "oficial_home_resultados",
        status="closed",
    )
    result_draw["draw_number"] = "2330"
    result_draw["draw_date"] = "11/05/2026"
    official_draw = base_draw(
        "progol_media_semana",
        "Progol Media Semana",
        "sports_pool",
        "https://official/quiniela",
        "oficial_quiniela",
        status="Dato no disponible",
    )
    official_draw["alternate_sources"] = ["https://official/guia.pdf?v=1"]
    official_draw["source_artifacts"] = [
        {"type": "pdf", "url": "https://official/guia.pdf?v=1", "purpose": "guia_quiniela_oficial"}
    ]
    result = FetchResult(ok=True, draws=[result_draw, official_draw], errors=[], sources=["https://official"])

    payload = get_active_draws(force_refresh=True, client=FakeClient(result), user_email="test@example.com")

    assert payload["summary"]["sports_pools"] == 1
    assert payload["draws"][0]["status"] != "closed"
    assert payload["draws"][0]["draw_number"] == "Dato no disponible"
    assert payload["draws"][0]["source_artifacts"][0]["type"] == "pdf"
    assert payload["draws"][0]["alternate_sources"] == ["https://official/guia.pdf?v=1"]


def test_generic_espn_fixtures_are_not_actionable_for_official_pool():
    draw = base_draw(
        "progol_media_semana",
        "Progol Media Semana",
        "sports_pool",
        "https://official/quiniela",
        "oficial_quiniela+espn_scoreboard",
        status="active",
    )
    draw["matches"] = [
        {
            "id": idx,
            "local": "Brentford",
            "visitante": "Crystal Palace",
            "liga": "Premier League",
            "fecha": "2099-01-01T12:00:00+00:00",
            "fuente_partido": "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
        }
        for idx in range(1, 10)
    ]
    result = FetchResult(ok=True, draws=[draw], errors=[], sources=["https://official/quiniela"])

    payload = get_active_draws(force_refresh=True, client=FakeClient(result), user_email="test@example.com")

    assert payload["draws"][0]["matches"] == []
    assert payload["draws"][0]["candidate_matches"]
    assert "Partidos descartados" in payload["draws"][0]["source_errors"][0]
    assert payload["draws"][0]["recommendation"]["recommendation"] != "Recomendado"
