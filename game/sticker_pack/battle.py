"""Стихийное «камень-ножницы-бумага» для стикер-дуэлей: только fire / water / earth."""

from __future__ import annotations

# water > fire > earth > water
_BEATS: dict[str, str] = {
    "water": "fire",
    "fire": "earth",
    "earth": "water",
}


def rps_score_bonus_multiplier(attacker_el: str, defender_el: str) -> float:
    """Если стихия атакующего бьёт стихию защитника — +15% к его базовому «очку»."""
    a = (attacker_el or "").strip().lower()
    d = (defender_el or "").strip().lower()
    if a not in _BEATS or d not in _BEATS:
        return 1.0
    if _BEATS.get(a) == d:
        return 1.15
    return 1.0


def resolve_duel_scores(
    *,
    atk_a: int,
    def_a: int,
    atk_b: int,
    def_b: int,
    elem_a: str,
    elem_b: str,
) -> tuple[float, float]:
    """
    Возвращает (score_a, score_b) после ATK/DEF и RPS.
    score = max(0, ATK - DEF_противника) * RPS_mult(attacker vs defender_element).
    """
    base_a = max(0, int(atk_a) - int(def_b))
    base_b = max(0, int(atk_b) - int(def_a))
    sa = float(base_a) * rps_score_bonus_multiplier(elem_a, elem_b)
    sb = float(base_b) * rps_score_bonus_multiplier(elem_b, elem_a)
    return sa, sb


def duel_winner_from_scores(score_a: float, score_b: float) -> str:
    """'a' | 'b' | 'draw'"""
    if abs(score_a - score_b) < 1e-6:
        return "draw"
    return "a" if score_a > score_b else "b"
