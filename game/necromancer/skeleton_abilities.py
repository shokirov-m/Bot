"""
Боевые способности скелетов (КД в раундах боя).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

Outcome = str  # continue | win


@dataclass(frozen=True, slots=True)
class SkeletonAbility:
    key: str
    name_ru: str
    blurb: str
    cooldown: int
    kind: str  # damage | heal_self


SKELETON_ABILITIES: dict[str, SkeletonAbility] = {
    "skel_tank": SkeletonAbility(
        "skel_tank",
        "Костяной заслон",
        "Восстанавливает 18% своего HP.",
        3,
        "heal_self",
    ),
    "skel_blade": SkeletonAbility(
        "skel_blade",
        "Резкий удар",
        "Мощная атака (~×1.9 урона).",
        2,
        "damage",
    ),
    "skel_mage": SkeletonAbility(
        "skel_mage",
        "Пепельный заряд",
        "Магический удар (~×1.7 урона).",
        2,
        "damage",
    ),
    "skel_colossus": SkeletonAbility(
        "skel_colossus",
        "Топот колосса",
        "Сокрушающий удар (~×2.2 урона).",
        4,
        "damage",
    ),
}

_DAMAGE_MULT = {
    "skel_blade": 1.9,
    "skel_mage": 1.7,
    "skel_colossus": 2.2,
}


def ability_for_role(role_key: str) -> SkeletonAbility | None:
    return SKELETON_ABILITIES.get(str(role_key))


def _apply_damage(state: dict[str, Any], companion: dict[str, Any], mult: float, logs: list[str]) -> Outcome:
    m = state.get("monster") or {}
    base = max(1, int(companion.get("atk", 5)))
    hi_loy = int(companion.get("loyalty", 0)) >= 70
    sk = 1.1 if hi_loy else 1.0
    dmg = max(1, int(base * mult * random.uniform(0.92, 1.08) * sk))
    m["hp"] = max(0, int(m.get("hp", 0)) - dmg)
    from game.combat.engine import record_player_last_damage_to_monster

    record_player_last_damage_to_monster(state, dmg)
    nm = str(companion.get("name", "Нежить"))
    logs.append(f"⚡ <b>{nm}</b> — <b>{dmg}</b> урона (способность).")
    if int(m.get("hp", 0)) <= 0:
        return "win"
    return "continue"


def companion_skeleton_turn(companion: dict[str, Any], state: dict[str, Any], logs: list[str]) -> Outcome:
    """Один ход скелета: способность по КД или обычная атака."""
    if companion.get("dead") or int(companion.get("hp", 0) or 0) <= 0:
        return "continue"
    role = str(companion.get("role") or "")
    cd = int(companion.get("ability_cd", 0) or 0)
    ability = ability_for_role(role)

    if ability is not None and cd <= 0:
        companion["ability_cd"] = ability.cooldown
        if ability.kind == "heal_self":
            hp_max = max(1, int(companion.get("hp_max", companion.get("hp", 1))))
            heal = max(1, int(hp_max * 0.18))
            companion["hp"] = min(hp_max, int(companion.get("hp", 0)) + heal)
            nm = str(companion.get("name", "Страж"))
            logs.append(f"⚡ <b>{nm}</b> — {ability.name_ru}: +{heal} HP.")
            return "continue"
        mult = _DAMAGE_MULT.get(role, 1.5)
        return _apply_damage(state, companion, mult, logs)

    if cd > 0:
        companion["ability_cd"] = cd - 1

    base = max(1, int(companion.get("atk", 5)))
    hi_loy = int(companion.get("loyalty", 0)) >= 70
    sk = 1.1 if hi_loy else 1.0
    dmg = max(1, int(base * random.uniform(0.9, 1.1) * sk))
    m = state.get("monster") or {}
    m["hp"] = max(0, int(m.get("hp", 0)) - dmg)
    from game.combat.engine import record_player_last_damage_to_monster

    record_player_last_damage_to_monster(state, dmg)
    nm = str(companion.get("name", "Нежить"))
    logs.append(f"⚔️ <b>{nm}</b> наносит <b>{dmg}</b> урона.")
    if int(m.get("hp", 0)) <= 0:
        return "win"
    return "continue"
