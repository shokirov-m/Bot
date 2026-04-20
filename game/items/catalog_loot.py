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


def roll_catalog_item(floor: int, rarities: list[str]) -> dict[str, Any] | None:
    """Случайный предмет из каталога, подходящий для данного этажа и редкостей.

    Возвращает глубокую копию словаря предмета или None если пул пуст.
    """
    rarity_set = set(r.lower() for r in rarities)
    pool: list[dict[str, Any]] = []
    for item in _get_catalog():
        if str(item.get("rarity") or "common").lower() not in rarity_set:
            continue
        note = str(item.get("export_floor_note") or "").strip()
        if note:
            try:
                lo, hi = _parse_floor_note(note)
                if not (lo <= int(floor) <= hi):
                    continue
            except (ValueError, TypeError):
                pass
        pool.append(item)
    if not pool:
        return None
    return copy.deepcopy(random.choice(pool))
