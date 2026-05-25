from src.active_draws.ai_quiniela_extractor import _draw_from_ai_payload, _validate_draw, extract_draw_with_ai
from src.ai.llm_clients import _parse_openai_responses_text


def test_ai_payload_converts_to_valid_media_semana_draw():
    payload = {
        "draw_number": "797",
        "draw_date": "Juegos del martes al jueves",
        "matches": [
            {"id": idx, "local": f"Local {idx}", "visitante": f"Visita {idx}", "liga": "Liga"}
            for idx in range(1, 10)
        ],
    }

    draw = _draw_from_ai_payload(payload, "progol_media_semana", "Progol Media Semana", "https://pronosticos.gob.mx/x", "test")

    assert _validate_draw(draw, "progol_media_semana")
    assert draw["draw_number"] == "797"
    assert len(draw["matches"]) == 9
    assert draw["matches"][0]["local"] == "LOCAL 1"


def test_ai_payload_rejects_incomplete_expected_count():
    payload = {
        "draw_number": "797",
        "matches": [{"id": 1, "local": "A", "visitante": "B"}],
    }

    draw = _draw_from_ai_payload(payload, "progol_media_semana", "Progol Media Semana", "https://pronosticos.gob.mx/x", "test")

    assert not _validate_draw(draw, "progol_media_semana")


def test_ai_payload_rejects_non_consecutive_casilleros():
    payload = {
        "draw_number": "797",
        "matches": [
            {"id": idx, "local": f"L{idx}", "visitante": f"V{idx}"}
            for idx in [1, 2, 3, 4, 5, 6, 7, 8, 10]
        ],
    }

    draw = _draw_from_ai_payload(payload, "progol_media_semana", "Progol Media Semana", "https://pronosticos.gob.mx/x", "test")

    assert not _validate_draw(draw, "progol_media_semana")


def test_ai_extraction_requires_configured_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    draw, errors = extract_draw_with_ai(
        "progol_media_semana",
        "Progol Media Semana",
        ["https://pronosticos.gob.mx/ProgolMediaSemana/Quiniela"],
    )

    assert draw is None
    assert any("OPENAI_API_KEY" in error or "ANTHROPIC_API_KEY" in error for error in errors)


def test_parse_openai_responses_text():
    payload = {
        "output": [
            {
                "content": [
                    {"type": "output_text", "text": '{"matches":[]}'},
                ]
            }
        ]
    }

    assert _parse_openai_responses_text(payload) == '{"matches":[]}'
