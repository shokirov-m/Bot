"""
Каталог монстров: все записи в Python (game/floors/monster_registry.py).

Бой подмешивает hp/atk/def из каталога с масштабом по этажу (reference_floor / level).
Элита / мини / мажор — см. catalog_skip_spawn_mults в карточке и combat_service.

Дополнительный JSON больше не используется (устарел в пользу .py реестра).
"""

from __future__ import annotations

import copy
from typing import Any

from game.floors.monster_registry import get_all_definitions


def _base_template_key(template_key: str) -> str:
    k = (template_key or "").strip()
    if k.startswith("elite_"):
        return k[7:]
    return k


def get_definition(template_key: str) -> dict[str, Any] | None:
    """Карточка монстра по ключу шаблона (elite_* сопоставляется с базовым id)."""
    bid = _base_template_key(template_key)
    row = get_all_definitions().get(bid)
    if row is None:
        return None
    return copy.deepcopy(row)


def has_explicit_stats(defn: dict[str, Any]) -> bool:
    return (
        defn.get("hp") is not None
        and defn.get("atk") is not None
        and defn.get("def") is not None
    )


def floor_ratio(defn: dict[str, Any], floor_number: int) -> float:
    ref = defn.get("reference_floor")
    if ref is None:
        ref = defn.get("level")
    r = max(1, int(ref or floor_number))
    ratio = float(floor_number) / float(r)
    return max(0.2, min(5.0, ratio))


def scaled_gold_exp(
    defn: dict[str, Any],
    floor_number: int,
) -> tuple[int | None, int | None]:
    """Переопределение золота и опыта; None — нет поля в карточке."""
    ratio = floor_ratio(defn, floor_number)
    g_raw = defn.get("gold")
    x_raw = defn.get("exp")
    gold: int | None = None
    xp: int | None = None
    if g_raw is not None:
        gold = max(1, int(round(float(g_raw) * ratio)))
    if x_raw is not None:
        xp = max(1, int(round(float(x_raw) * ratio)))
    return gold, xp
