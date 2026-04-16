"""
Статусные эффекты в бою: доты тикают в apply_dot_*; длительность «чистых» баффов — в tick_effect_turns.
"""

from __future__ import annotations

import random
from typing import Any

# Длительность этих ключей уменьшается только в engine.apply_dot_damage_* (не дублировать в tick_effect_turns).
DOT_DURATION_KEYS = frozenset({"burn", "poison", "bleed", "hot"})


def _list_key(side: str) -> str:
    return f"{side}_effects"


def init_effects(state: dict[str, Any]) -> None:
    state.setdefault("player_effects", [])
    state.setdefault("monster_effects", [])
    state.setdefault("monster_rage", False)
    state.setdefault("player_block_next", False)
    state.setdefault("monster_def_mod", 0)  # отрицательное — снижение защиты
    state.setdefault("player_damage_mod", 1.0)
    state.setdefault("skip_player_turn", False)
    state.setdefault("player_shield_hp", 0)
    state.setdefault("player_temp_dodge", 0.0)
    state.setdefault("player_temp_dodge_turns", 0)
    state.setdefault("player_fortify_bonus", 0)
    state.setdefault("player_fortify_turns", 0)
    state.setdefault("monster_outgoing_mult", 1.0)
    state.setdefault("monster_debuff_turns", 0)


def tick_effect_turns(side: str, state: dict[str, Any]) -> list[str]:
    """Уменьшить длительность эффектов, вернуть строки лога."""
    key = _list_key(side)
    effs: list[dict[str, Any]] = list(state.get(key, []))
    log: list[str] = []
    new_effs: list[dict[str, Any]] = []
    for e in effs:
        ek = str(e.get("key", ""))
        if ek in DOT_DURATION_KEYS:
            new_effs.append(e)
            continue
        turns = int(e.get("turns", 0))
        if turns <= 1:
            log.append(f"Эффект {e.get('name', '?')} спал.")
            continue
        e["turns"] = turns - 1
        new_effs.append(e)
    state[key] = new_effs
    return log


def add_effect(side: str, state: dict[str, Any], name: str, key: str, turns: int, payload: dict[str, Any] | None = None) -> None:
    key_list = _list_key(side)
    state.setdefault(key_list, [])
    entry = {"name": name, "key": key, "turns": turns}
    if payload:
        entry.update(payload)
    state[key_list].append(entry)


def apply_dot_fire_player(state: dict[str, Any]) -> int:
    """Поджог: 5% от max_hp игрока за ход, минимум 1."""
    dmg = 0
    for e in list(state.get("player_effects", [])):
        if e.get("key") == "burn":
            # урон считается в engine от текущего max hp
            dmg += int(e.get("potency", 5))
    return dmg


def monster_has_effect(state: dict[str, Any], key: str) -> bool:
    return any(e.get("key") == key for e in state.get("monster_effects", []))


def remove_effects_with_key(side: str, state: dict[str, Any], effect_key: str) -> bool:
    """Удалить все эффекты с данным key. True, если что-то убрали."""
    lst_key = _list_key(side)
    effs: list[dict[str, Any]] = list(state.get(lst_key, []))
    new_effs = [e for e in effs if e.get("key") != effect_key]
    state[lst_key] = new_effs
    return len(new_effs) < len(effs)


def roll_chance(chance: float) -> bool:
    return random.random() < chance
