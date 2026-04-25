"""
Модификаторы боя с этажного «первого захода» события: хранятся в meta, применяются
при старте следующего боя, затем сбрасываются (см. consume_floor_mod_to_state).
"""

from __future__ import annotations

import copy
from typing import Any

from db.models.character import Character

# Вероятность особого события (при первом заходе на этаж, обычный этаж).
FLOOR_ENTRY_EVENT_CHANCE: float = 0.20

# Одноразовый пакет для следующего боя (см. maybe_roll_floor_entry_event).
FLOOR_MOD_META_KEY = "floor_mod_v1"
# Доп. бои на арене без лимита дня.
SPIRIT_ARENA_FIGHTS_KEY = "spirit_arena_fights_v1"


def _pop_floor_mod_from_character(character: Character) -> dict[str, Any] | None:
    mp = dict(character.meta_progress or {})
    raw = mp.pop(FLOOR_MOD_META_KEY, None)
    if raw is None or not isinstance(raw, dict):
        character.meta_progress = mp
        return None
    character.meta_progress = mp
    return copy.deepcopy(raw)


def consume_floor_mod_to_combat_state(character: Character, state: dict[str, Any]) -> list[str]:
    """
    Переносит floor_mod_v1 в combat state и очищает meta.
    Возвращает строки для батл-лога.
    """
    data = _pop_floor_mod_from_character(character)
    if not data:
        return []

    logs: list[str] = []

    ftk = float(data.get("fog_taken_mult") or 0.0)  # урон по игроку от врага
    if 0.01 < ftk < 1.0:
        state["fe_monster_to_player_mult"] = ftk
    gm = float(data.get("gold_mult") or 1.0)
    if gm > 1.01:
        state["floor_event_gold_mult"] = float(state.get("floor_event_gold_mult", 1.0)) * gm
    if ftk or gm > 1.01:
        parts: list[str] = []
        if 0.01 < ftk < 1.0:
            parts.append(f"урон врага ×{ftk:.0%}")
        if gm > 1.01:
            parts.append(f"золото +{int(round((gm - 1.0) * 100))}%")
        logs.append("🌫️ <b>Туман этажа:</b> " + ", ".join(parts) + ".")

    if data.get("cursed"):
        state["fe_cursed_dot"] = max(1, int(data.get("cursed_dmg", 5)))
        state["fe_cursed_phase"] = 0
        logs.append("🕯️ <b>Проклятие зоны:</b> тебя сжигает тьма (урон раз в 2 твоих хода).")

    ex = float(data.get("lightning_exec") or 0.0)
    if 0.0 < ex < 0.5:
        state["fe_lightning_execute"] = ex
        logs.append("⚡ <b>Небеса рвутся:</b> если враг <15% HP — в конце твоих ударов сработает казнь.")

    return logs


def floor_curse_on_player_phase_start(state: dict[str, Any]) -> list[str]:
    """
    Проклятие этажа: урон fe_cursed_dot, каждые 2 хода (2-й, 4-й, …) после 1-го.
    """
    d = int(state.get("fe_cursed_dot") or 0)
    if d <= 0:
        return []
    ph = int(state.get("fe_cursed_phase") or 0) + 1
    state["fe_cursed_phase"] = ph
    if ph < 2 or (ph % 2) != 0:
        return []
    pre = int(state["player_hp"])
    state["player_hp"] = max(0, pre - d)
    if int(state["player_hp"]) < pre:
        return [f"🕯️ <b>Проклятие:</b> −{d} HP (зона)."]
    return []


def maybe_lightning_execute_after_monster_damaged(
    state: dict[str, Any], logs: list[str]
) -> str | None:
    """
    Если враг жив, но current_hp/max_hp <= порога — казнить (победа).
    Возвращает 'win' | None.
    """
    thr = float(state.get("fe_lightning_execute") or 0.0)
    if thr <= 0.0:
        return None
    m = state.get("monster") or {}
    try:
        mhp, mmx = int(m["hp"]), int(m.get("max_hp") or 0)
    except (TypeError, ValueError, KeyError):
        return None
    if mmx <= 0 or mhp <= 0:
        return None
    if (mhp / max(1, mmx)) > thr + 1e-9:
        return None
    m["hp"] = 0
    state["fe_lightning_execute_fired"] = True
    logs.append("⚡ <b>Молния</b> обрушилась — враг погиб!")
    return "win"
