"""
Пассивы снаряжения: `item_data["passive"]` — словарь с числовыми ключами, суммируются
по всем надетым вещам и попадают в `combat_state` с префиксом `gear_`.
"""

from __future__ import annotations

import copy
from typing import Any

# Готовые шаблоны по ключу, если item_data: "passive_key": "lifesteal_small"
PASSIVE_PRESETS: dict[str, dict[str, Any]] = {
    "lifesteal_small": {"lifesteal_percent": 3.0},
    "lifesteal_medium": {"lifesteal_percent": 5.0},
    "vampire_touch": {"lifesteal_percent": 2.0, "on_kill_heal": 8},
    "steadfast": {"on_kill_heal": 6},
    "regen_aura": {"turn_regen": 2},
}


def _resolve_one_payload(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, str) and raw in PASSIVE_PRESETS:
        return copy.deepcopy(PASSIVE_PRESETS[raw])
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items()}
    return None


def apply_to_combat_state(
    state: dict[str, Any], item_datas: list[dict[str, Any] | None] | None
) -> list[str]:
    """
    Суммирует пассивы и пишет в state.
    Ключи passive:
    - lifesteal_percent — % от нанесённого HP-урона по врагу (см. engine, атака/скилл).
    - on_kill_heal — +HP в конце боя (при победе, combat_service).
    - turn_regen — +HP в начале твоего хода (как regen, после дотов).
    """
    ls = 0.0
    okh = 0
    trg = 0
    for d in item_datas or []:
        if not d:
            continue
        p = d.get("passive")
        if p is None and d.get("passive_key"):
            p = d.get("passive_key")
        pl = _resolve_one_payload(p)
        if not pl:
            continue
        ls += float(pl.get("lifesteal_percent", 0) or 0)
        okh += int(pl.get("on_kill_heal", 0) or 0)
        trg += int(pl.get("turn_regen", 0) or 0)

    logs: list[str] = []
    if ls > 0.0:
        state["gear_lifesteal_percent"] = float(state.get("gear_lifesteal_percent", 0.0)) + ls
    if okh:
        state["gear_on_kill_heal"] = int(state.get("gear_on_kill_heal", 0)) + okh
    if trg:
        state["gear_turn_regen"] = int(state.get("gear_turn_regen", 0)) + trg
    return logs


def apply_lifesteal_for_damage(state: dict[str, Any], damage_dealt: int, logs: list[str]) -> None:
    """После нанесения damage_dealt по врагу (атака/урон скила)."""
    p = float(state.get("gear_lifesteal_percent", 0) or 0.0)
    if p <= 0.0 or damage_dealt <= 0:
        return
    heal = max(1, int(int(damage_dealt) * p / 100.0))
    cur = int(state["player_hp"])
    mx = int(state["player_hp_max"])
    nh = min(mx, cur + heal)
    if nh > cur:
        state["player_hp"] = nh
        logs.append(f"✨ <b>Экип (поглощение):</b> +{nh - cur} HP.")


def turn_start_regen_from_gear(state: dict[str, Any]) -> list[str]:
    r = int(state.get("gear_turn_regen", 0) or 0)
    if r <= 0:
        return []
    cur = int(state["player_hp"])
    mx = int(state["player_hp_max"])
    nh = min(mx, cur + r)
    if nh > cur:
        state["player_hp"] = nh
        return [f"✨ <b>Экип (аура):</b> +{nh - cur} HP в начале хода."]
    return []
