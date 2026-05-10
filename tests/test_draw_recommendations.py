from src.active_draws.draw_parser import base_draw
from src.active_draws.draw_recommendation_engine import generate_home_recommendation
from src.active_draws.draw_validator import apply_validation
from src.recommendations.recommendation_score import calculate_recommendation_score


def test_recommendation_score_for_complete_sports_pool():
    draw = base_draw("progol", "Progol", "sports_pool", "https://official", "test", status="active")
    draw["matches"] = [{"local": "A", "visitante": "B"} for _ in range(14)]
    draw["has_recent_sports_data"] = True
    draw["has_internal_history"] = True
    draw["has_market_data"] = True
    draw["closing_date"] = "2099-01-01T12:00:00+00:00"
    draw = apply_validation(draw)

    assert calculate_recommendation_score(draw) > 70
    assert generate_home_recommendation(draw)["recommendation"] == "Recomendado"


def test_recommendation_for_protouch_with_missing_market_is_moderate_or_lower():
    draw = base_draw("protouch", "Protouch", "sports_pool", "https://official", "test", status="active")
    draw["matches"] = [{"local": "A", "visitante": "B"} for _ in range(13)]
    draw["has_recent_sports_data"] = True
    draw["has_internal_history"] = True
    draw["has_market_data"] = False
    draw = apply_validation(draw)

    recommendation = generate_home_recommendation(draw)

    assert recommendation["recommendation"] in {"Moderado", "No prioritario"}


def test_random_lottery_is_only_informative():
    draw = base_draw("melate", "Melate", "random_lottery", "https://official", "test", status="active")
    draw["accumulated_pool"] = "43.6"
    draw["cost_per_entry"] = "15"
    draw["draw_date"] = "2099-01-01T12:00:00+00:00"
    draw["has_internal_history"] = True
    draw["data_freshness"] = "actualizada"
    draw = apply_validation(draw)

    recommendation = generate_home_recommendation(draw)

    assert recommendation["recommendation"] == "Solo informativo"
    assert "no existe una ventaja predictiva" in recommendation["reason"]

