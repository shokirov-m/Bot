"""Выдача предметов из каталога game/data/items/ по этажу и редкости."""

from __future__ import annotations

import copy
import random
from typing import Any

_CATALOG: list[dict[str, Any]] | None = None


def _load_catalog() -> list[dict[str, Any]]:
    from game.data.items.amulets import amulet_examples
    from game.data.items.armor import armor_examples, gloves_examples, helmet_examples, pants_examples
    from game.data.items.offhand import dagger_examples, grimoire_examples, shield_examples
    from game.data.items.rings import ring_examples
    from game.data.items.weapons import two_handed_weapon_examples, weapon_main_examples, weapon_offhand_examples

    items: list[dict[str, Any]] = []
    for fn in (
        amulet_examples,
        armor_examples,
        helmet_examples,
        pants_examples,
        gloves_examples,
        shield_examples,
        grimoire_examples,
        dagger_examples,
        ring_examples,
        weapon_main_examples,
        weapon_offhand_examples,
        two_handed_weapon_examples,
    ):
        items.extend(fn())
    return items


def _get_catalog() -> list[dict[str, Any]]:
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = _load_catalog()
    return _CATALOG


def _parse_floor_note(note: str) -> tuple[int, int]:
    """"1–20" → (1, 20);  "90+" → (90, 100)."""
    s = str(note).strip()
    if s.endswith("+"):
        return int(s[:-1]), 100
    for sep in ("–", "—", "-"):
        if sep in s:
            lo_s, hi_s = s.split(sep, 1)
            return int(lo_s.strip()), int(hi_s.strip())
    n = int(s)
    return n, n


def rarities_for_floor(floor: int) -> list[str]:
    """Редкости из каталога, доступные на данном этаже.

    Схема дропа:
      Обычный    1-20
      Необычный  11-30
      Редкий     21-50
      Эпический  41-80
      Легендарный 70-90
      Мифический  90+
    """
    f = int(floor)
    result: list[str] = []
    if f <= 20:
        result.append("common")
    if 11 <= f <= 30:
        result.append("uncommon")
    if 21 <= f <= 50:
        result.append("rare")
    if 41 <= f <= 80:
        result.append("epic")
    if 70 <= f <= 90:
        result.append("legendary")
    if f >= 90:
        result.append("mythic")
    return result


# На этажах выше верхней границы export_floor_note предмет всё ещё может выпасть,
# но с меньшим весом — чтобы не гнать игрока на низкие этажи за «старыми» рессами.
_CATALOG_RELAXED_FLOOR_WEIGHT = 0.44

# Множитель веса при выборе предмета: реже эпик+ в случайных крутках каталога.
_RARITY_ROLL_WEIGHT: dict[str, float] = {
    "common": 1.0,
    "uncommon": 0.62,
    "rare": 0.36,
    "epic": 0.16,
    "legendary": 0.07,
    "mythic": 0.035,
}


def roll_catalog_item(floor: int, rarities: list[str] | None = None) -> dict[str, Any] | None:
    """Случайный предмет из каталога для данного этажа.

    Если rarities не передан — используется rarities_for_floor(floor).
    Возвращает глубокую копию словаря предмета или None если пул пуст.
    """
    rarity_set = set(r.lower() for r in (rarities if rarities is not None else rarities_for_floor(floor)))
    fl = int(floor)
    weighted: list[tuple[float, dict[str, Any]]] = []
    for item in _get_catalog():
        if str(item.get("rarity") or "common").lower() not in rarity_set:
            continue
        note = str(item.get("export_floor_note") or "").strip()
        w = 1.0
        if note:
            try:
                lo, hi = _parse_floor_note(note)
                if lo <= fl <= hi:
                    w = 1.0
                elif fl > hi:
                    w = float(_CATALOG_RELAXED_FLOOR_WEIGHT)
                else:
                    continue
            except (ValueError, TypeError):
                w = 1.0
        rw = float(_RARITY_ROLL_WEIGHT.get(str(item.get("rarity") or "common").lower(), 1.0))
        weighted.append((w * rw, item))
    if not weighted:
        return None
    items = [it for _, it in weighted]
    weights = [wt for wt, _ in weighted]
    pick = random.choices(items, weights=weights, k=1)[0]
    return copy.deepcopy(pick)
