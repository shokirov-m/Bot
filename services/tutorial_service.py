"""
Онбординг: разовый бонус при создании героя, кнопки-подсказки (callback tut:*).
Состояние в character.meta_progress['tutorial_v1'].
"""

from __future__ import annotations

from typing import Any

from db.models.character import Character

META_KEY = "tutorial_v1"


def _slot(meta: dict[str, Any]) -> dict[str, Any]:
    raw = meta.get(META_KEY)
    if not isinstance(raw, dict):
        raw = {}
    return raw


def grant_creation_gold(character: Character, *, amount: int = 35) -> bool:
    """Разовый бонус при создании персонажа. True если выдали сейчас."""
    meta = dict(character.meta_progress or {})
    st = _slot(meta)
    if st.get("creation_bonus"):
        return False
    st["creation_bonus"] = True
    meta[META_KEY] = st
    character.meta_progress = meta
    character.gold = int(character.gold) + int(amount)
    return True


def try_claim_button_bonus(character: Character, *, amount: int = 18) -> tuple[bool, str]:
    """Кнопка «бонус новичка» в туториале. (успех, сообщение plain)."""
    meta = dict(character.meta_progress or {})
    st = _slot(meta)
    if st.get("button_bonus"):
        return False, "Бонус уже получен."
    st["button_bonus"] = True
    meta[META_KEY] = st
    character.meta_progress = meta
    character.gold = int(character.gold) + int(amount)
    return True, f"+{amount} золота."


def tip_floor_ru() -> str:
    return (
        "🗺️ Открой этаж через меню или /floor — выбери монстра и сражайся. "
        "Победы дают золото и опыт."
    )


def tip_inv_ru() -> str:
    return "🎒 В /inv смотри сумку и экипируй оружие — от него зависит урон."
