"""
Заточка оружия +0…+15: стоимость, бросок успеха / провала / даунгрейд.
"""

from __future__ import annotations

import random
from typing import Literal

MAX_ENCHANT = 15

EnchantOutcome = Literal["success", "fail", "downgrade", "max"]


def current_enchant_level(item_data: dict | None) -> int:
    data = item_data or {}
    return max(0, min(MAX_ENCHANT, int(data.get("enchant", data.get("plus", 0)) or 0)))


def enchant_attempt_cost_gold(current_level: int) -> int:
    """Цена одной попытки заточки (золото)."""
    c = max(0, min(MAX_ENCHANT, current_level))
    return 30 + c * 45 + max(0, c - 6) * 80 + max(0, c - 11) * 120


def roll_enchant_outcome(current_level: int, *, success_chance_bonus: float = 0.0) -> EnchantOutcome:
    """
    Исход попытки (current_level — до попытки).
    success: +1; fail: без изменений; downgrade: −1 (не ниже 0).
    success_chance_bonus — абсолютная добавка к шансу успеха (например бонус профессии «кузнец»).
    """
    if current_level >= MAX_ENCHANT:
        return "max"
    # базовый шанс успеха падает с уровнем
    bonus = max(0.0, float(success_chance_bonus))
    p_ok = 0.88 - current_level * 0.038
    p_ok = max(0.22, min(0.88, p_ok))
    p_ok = min(0.95, p_ok + bonus)
    r = random.random()
    if r < p_ok:
        return "success"
    # часть «провалов» — даунгрейд
    if current_level > 0 and random.random() < 0.35:
        return "downgrade"
    return "fail"


def apply_enchant_change(item_data: dict, outcome: EnchantOutcome) -> tuple[dict, int]:
    """
    Возвращает (новый item_data, дельта уровня заточки: -1/0/+1).
    Для max и fail — дельта 0 (max обрабатывается до вызова).
    """
    data = dict(item_data or {})
    cur = current_enchant_level(data)
    if outcome == "success":
        new = min(MAX_ENCHANT, cur + 1)
        data["enchant"] = new
        return data, new - cur
    if outcome == "downgrade":
        new = max(0, cur - 1)
        data["enchant"] = new
        return data, new - cur
    data["enchant"] = cur
    return data, 0
