"""
Заточка оружия +0…+10: стоимость (золото + материалы), бросок успеха / провала / даунгрейд.

Каждый уровень заточки даёт +5% к базовому стату предмета (атака или защита).
"""

from __future__ import annotations

import random
from typing import Literal

MAX_ENCHANT = 10

EnchantOutcome = Literal["success", "fail", "downgrade", "max"]


def current_enchant_level(item_data: dict | None) -> int:
    data = item_data or {}
    return max(0, min(MAX_ENCHANT, int(data.get("enchant", data.get("plus", 0)) or 0)))


def enchant_stat_multiplier(enchant_level: int) -> float:
    """Множитель стата от заточки: +5% за уровень (×1.0 при +0, ×1.50 при +10)."""
    e = max(0, min(MAX_ENCHANT, int(enchant_level)))
    return 1.0 + e * 0.05


def enchant_attempt_cost_gold(current_level: int) -> int:
    """Золото за одну попытку заточки."""
    c = max(0, min(MAX_ENCHANT, current_level))
    return 50 + c * 80


def enchant_material_cost(current_level: int) -> int:
    """Материалы (той же редкости) за одну попытку заточки. Растут каждые 2 уровня."""
    c = max(0, min(MAX_ENCHANT - 1, current_level))
    return (c // 2) + 1  # 1,1,2,2,3,3,4,4,5,5


def roll_enchant_outcome(current_level: int, *, success_chance_bonus: float = 0.0) -> EnchantOutcome:
    """
    Исход попытки (current_level — до попытки).
    success: +1; fail: без изменений; downgrade: −1 (не ниже 0).
    """
    if current_level >= MAX_ENCHANT:
        return "max"
    bonus = max(0.0, float(success_chance_bonus))
    # шанс успеха: 90% на +0 → 36% на +9
    p_ok = 0.90 - current_level * 0.06
    p_ok = max(0.30, min(0.90, p_ok))
    p_ok = min(0.95, p_ok + bonus)
    r = random.random()
    if r < p_ok:
        return "success"
    if current_level > 0 and random.random() < 0.35:
        return "downgrade"
    return "fail"


def apply_enchant_change(item_data: dict, outcome: EnchantOutcome) -> tuple[dict, int]:
    """
    Возвращает (новый item_data, дельта уровня: -1/0/+1).
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
