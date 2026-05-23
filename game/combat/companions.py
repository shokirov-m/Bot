"""
Ходы наёмников в бою башни (после игрока, до монстра).
Навыки «по всем врагам» в ТЗ при 1v1 сводятся к удару по одной цели (см. план engine-note-aoe).
"""

from __future__ import annotations

import random
from typing import Literal

Outcome = Literal["continue", "win", "lose"]


def apply_tank_intercept_to_player_damage(state: dict, base_dmg: int, logs: list[str]) -> int:
    """Танк живой — перехватывает ~40% урона, предназначенного игроку."""
    if base_dmg <= 0:
        return base_dmg
    comps = list(state.get("companions") or [])
    tank = next(
        (
            c
            for c in comps
            if c.get("is_tank") and not c.get("dead") and int(c.get("hp", 0) or 0) > 0
        ),
        None,
    )
    if tank is None:
        return base_dmg
    intercept = max(0, int(round(base_dmg * 0.4)))
    if intercept <= 0:
        return base_dmg
    thp = int(tank.get("hp", 0))
    real = min(intercept, thp)
    tank["hp"] = thp - real
    if int(tank["hp"]) <= 0:
        tank["dead"] = True
        logs.append(f"☠️ <b>{tank.get('name', 'Страж')}</b> выбит из боя (нокаут).")
    else:
        logs.append(
            f"🛡️ <b>{tank.get('name', 'Страж')}</b> перехватывает <b>{real}</b> урона.",
        )
    return max(0, base_dmg - real)


def companions_turn(state: dict) -> tuple[list[str], Outcome]:
    logs: list[str] = []
    m = state.get("monster") or {}
    if int(m.get("hp", 0)) <= 0:
        return logs, "win"

    for c in list(state.get("companions") or []):
        if c.get("dead") or int(c.get("hp", 0) or 0) <= 0:
            continue
        if c.get("is_skeleton"):
            from game.necromancer.skeleton_abilities import companion_skeleton_turn

            outcome = companion_skeleton_turn(c, state, logs)
            if outcome == "win":
                return logs, "win"
            continue
        base = max(1, int(c.get("atk", 5)))
        hi_loy = int(c.get("loyalty", 0)) >= 70
        sk = 1.1 if hi_loy else 1.0
        dmg = max(1, int(base * random.uniform(0.9, 1.1) * sk))
        m["hp"] = max(0, int(m.get("hp", 0)) - dmg)
        from game.combat.engine import record_player_last_damage_to_monster

        record_player_last_damage_to_monster(state, dmg)
        nm = str(c.get("name", "Наёмник"))
        logs.append(f"⚔️ <b>{nm}</b> наносит <b>{dmg}</b> урона.")
        if int(m.get("hp", 0)) <= 0:
            return logs, "win"
    return logs, "continue"
