"""Recommendation scoring for active draws."""

from __future__ import annotations

from src.active_draws.draw_parser import NOT_AVAILABLE


def calculate_recommendation_score(draw: dict) -> int:
    """Calculate recommendation score from 0 to 100."""

    if draw.get("game_type") == "sports_pool":
        return _sports_pool_score(draw)
    if draw.get("game_type") == "random_lottery":
        return _random_lottery_score(draw)
    return min(40, int(draw.get("data_quality_score", 0)))


def _sports_pool_score(draw: dict) -> int:
    score = 0
    score += 20 if draw.get("status") == "active" else 8 if draw.get("status") != "closed" else 0
    score += 20 if draw.get("matches") else 0
    score += 20 if draw.get("has_recent_sports_data") else 5
    score += 15 if draw.get("has_internal_history") else 5
    score += 10 if draw.get("has_market_data") else 0
    score += min(10, int(draw.get("data_quality_score", 0)) // 10)
    score += 5 if draw.get("closing_date") not in (None, "", NOT_AVAILABLE) else 0
    if not draw.get("has_market_data"):
        score = min(score, 70)
    if not draw.get("matches"):
        score = min(score, 49)
    return max(0, min(100, score))


def _random_lottery_score(draw: dict) -> int:
    score = 0
    score += 25 if draw.get("status") == "active" else 8 if draw.get("status") != "closed" else 0
    score += 20 if draw.get("estimated_prize") not in (None, "", NOT_AVAILABLE) or draw.get("accumulated_pool") not in (None, "", NOT_AVAILABLE) else 0
    score += 15 if draw.get("cost_per_entry") not in (None, "", NOT_AVAILABLE) else 0
    score += 15 if draw.get("draw_date") not in (None, "", NOT_AVAILABLE) else 0
    score += 15 if draw.get("has_internal_history") else 5
    score += 10 if draw.get("data_freshness") == "actualizada" else 0
    return max(0, min(100, score))
