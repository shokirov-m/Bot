"""
Онбординг: разовый бонус при создании героя, кнопки-подсказки (callback tut:*).
Состояние в character.meta_progress['tutorial_v1'].
"""

from __future__ import annotations

from typing import Any

from db.models.character import Character
import services.progression.character_service as character_service

META_KEY = "tutorial_v1"

STEP_FIGHT = "fight"
STEP_EQUIP = "equip"
STEP_UNLOCKS = "unlocks"


def _slot(meta: dict[str, Any]) -> dict[str, Any]:
    raw = meta.get(META_KEY)
    if not isinstance(raw, dict):
        raw = {}
    return raw


def current_step(character: Character) -> str:
    meta = dict(character.meta_progress or {})
    st = _slot(meta)
    step = str(st.get("step") or STEP_FIGHT).strip().lower()
    if step not in (STEP_FIGHT, STEP_EQUIP, STEP_UNLOCKS):
        step = STEP_FIGHT
    return step


def set_step(character: Character, step: str) -> None:
    meta = dict(character.meta_progress or {})
    st = dict(_slot(meta))
    st["step"] = str(step or STEP_FIGHT)
    meta[META_KEY] = st
    character.meta_progress = meta
    try:
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(character, "meta_progress")
    except Exception:
        pass


def advance_step_if_needed(character: Character) -> None:
    """
    Progression:
    - fight: until tutorial battle is done
    - equip: until player equips any weapon/offhand (flag set from inventory handler)
    - unlocks: generic step while features unlock by level (kept for hinting)
    """
    step = current_step(character)
    if step == STEP_FIGHT:
        from services.combat.tutorial_battle_service import tutorial_battle_pending

        if not tutorial_battle_pending(character):
            set_step(character, STEP_EQUIP)
        return
    if step == STEP_EQUIP:
        meta = dict(character.meta_progress or {})
        st = _slot(meta)
        if bool(st.get("equipped_any")):
            set_step(character, STEP_UNLOCKS)
        return


def mark_equipped_any(character: Character) -> None:
    """Mark that player has equipped any gear at least once (tutorial step helper)."""
    meta = dict(character.meta_progress or {})
    st = dict(_slot(meta))
    if st.get("equipped_any"):
        return
    st["equipped_any"] = True
    meta[META_KEY] = st
    character.meta_progress = meta
    try:
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(character, "meta_progress")
    except Exception:
        pass


def grant_creation_gold(character: Character, *, amount: int = 35) -> bool:
    """Разовый бонус при создании персонажа. True если выдали сейчас."""
    meta = dict(character.meta_progress or {})
    st = _slot(meta)
    if st.get("creation_bonus"):
        return False
    st["creation_bonus"] = True
    meta[META_KEY] = st
    character.meta_progress = meta
    character_service.add_gold(character, int(amount))
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
    character_service.add_gold(character, int(amount))
    return True, f"+{amount} золота."


def tip_floor_ru() -> str:
    return (
        "🗺️ Открой этаж через меню или /floor — выбери монстра и сражайся. "
        "Победы дают золото и опыт."
    )


def tip_inv_ru() -> str:
    return "🎒 В /inv смотри сумку и экипируй оружие — от него зависит урон."
