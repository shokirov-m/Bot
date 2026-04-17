"""
События зоны «Лес Начал» (этажи 1–10): грибы, дух, привал.
Состояние в character.meta_progress["forest_bg_v1"].
"""

from __future__ import annotations

import random
from typing import Any, Literal

from db.models.character import Character

META_KEY = "forest_bg_v1"


def is_forest_beginnings_zone(floor_number: int) -> bool:
    return 1 <= int(floor_number) <= 10


def _bucket(character: Character) -> dict[str, Any]:
    mp = dict(character.meta_progress or {})
    raw = mp.get(META_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def _save_bucket(character: Character, b: dict[str, Any]) -> None:
    mp = dict(character.meta_progress or {})
    mp[META_KEY] = b
    character.meta_progress = mp


def camp_used(character: Character) -> bool:
    return bool(_bucket(character).get("camp_used"))


def set_camp_used(character: Character) -> None:
    b = _bucket(character)
    b["camp_used"] = True
    _save_bucket(character, b)


def spirit_used(character: Character) -> bool:
    return bool(_bucket(character).get("spirit_used"))


def set_spirit_used(character: Character) -> None:
    b = _bucket(character)
    b["spirit_used"] = True
    _save_bucket(character, b)


def eligible_for_forest_tricks(spawn) -> bool:
    """Грибы / дух — только обычные цели (не элита и не боссы)."""
    return not spawn.is_elite and not spawn.is_mini_boss and not spawn.is_major_boss


def roll_prefight_kind(character: Character) -> Literal["mushroom", "spirit", "combat"]:
    """
    Распределение при нажатии на обычного монстра в зоне 1–10.
    Дух леса — не чаще одного раза за проход зоны (пока не ушёл на 11+).
    """
    r = random.random()
    if r < 0.28:
        return "mushroom"
    if r < 0.42 and not spirit_used(character):
        return "spirit"
    return "combat"


def mushroom_intro_html() -> str:
    return (
        "🍄 <b>Ядовитые грибы</b>\n"
        "<i>Лесной обман: съесть — иногда целебно, рискнуть — яд кусает плоть.</i>\n\n"
        "Выбери действие."
    )


def spirit_intro_html() -> str:
    return (
        "🦊 <b>Лесной дух</b>\n"
        "<i>«Три тропы — одна лжёт, одна жжёт, одна дарит удачу. Выбери, странник.»</i>\n\n"
        "Нажми <b>одну</b> из кнопок ниже."
    )


def spirit_outcome_for_choice(choice: int, correct: int) -> tuple[str, int, int, int]:
    """
    choice 0..2, correct 0..2.
    Возвращает (html_line, gold_delta, hp_delta, mp_delta).
    """
    if choice == correct:
        return ("✨ Дух доволен: <b>удача</b> на твоей стороне.", 12, 0, 2)
    if (choice + 1) % 3 == correct:
        return ("🌫️ Тропа была <b>иллюзией</b> — лёгкая усталость.", 0, -max(3, 5), 0)
    return ("🍃 Тропа <b>нейтральна</b> — ни богатства, ни беды.", 4, 0, 0)
