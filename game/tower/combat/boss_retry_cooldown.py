"""Кулдаун повторного боя с сильным боссом (×10) после победы."""

from __future__ import annotations

import random
import time
from typing import Any

from db.models.character import Character
from game.enemies.floors.spawns import FloorMonsterSpawn
from game.tower_cards import monster_cards as tower_cards_mod

META_KEY = "major_boss_retry_v1"
DEFAULT_COOLDOWN_MIN_MINUTES = 15
DEFAULT_COOLDOWN_MAX_MINUTES = 20


def _cooldown_map(character: Character) -> dict[str, float]:
    raw = (character.meta_progress or {}).get(META_KEY)
    if not isinstance(raw, dict):
        return {}
    return {str(k): float(v) for k, v in raw.items() if v is not None}


def _save_cooldown_map(character: Character, cd: dict[str, float]) -> None:
    meta = dict(character.meta_progress or {})
    meta[META_KEY] = cd
    character.meta_progress = meta


def cooldown_bounds_seconds(floor_number: int) -> tuple[int, int]:
    from game.tower.trials.pack_config import get_trial_config

    cfg = get_trial_config(int(floor_number)) or {}
    mn = max(1, int(cfg.get("boss_retry_cooldown_min_minutes") or DEFAULT_COOLDOWN_MIN_MINUTES))
    mx = max(mn, int(cfg.get("boss_retry_cooldown_max_minutes") or DEFAULT_COOLDOWN_MAX_MINUTES))
    return mn * 60, mx * 60


def set_retry_cooldown_after_victory(character: Character, floor_number: int) -> int:
    """Записать таймер; вернуть длительность кулдауна в секундах."""
    lo, hi = cooldown_bounds_seconds(int(floor_number))
    duration = random.randint(lo, hi)
    until = time.time() + duration
    cd = _cooldown_map(character)
    cd[str(int(floor_number))] = until
    _save_cooldown_map(character, cd)
    return duration


def retry_seconds_left(character: Character, floor_number: int) -> int:
    until = _cooldown_map(character).get(str(int(floor_number)))
    if until is None:
        return 0
    return max(0, int(until - time.time()))


def format_retry_wait_ru(seconds: int) -> str:
    return tower_cards_mod.format_wait_hm_ru(seconds)


def check_can_fight_major_boss(
    character: Character,
    spawn: FloorMonsterSpawn,
    *,
    floor_number: int | None = None,
) -> tuple[bool, str]:
    if not spawn.is_major_boss:
        return True, ""
    fl = int(floor_number if floor_number is not None else character.floor_number)
    left = retry_seconds_left(character, fl)
    if left <= 0:
        return True, ""
    wait = format_retry_wait_ru(left)
    return (
        False,
        f"⏳ <b>Сильный босс восстанавливается.</b> Повторный бой через {wait}.",
    )


def apply_trial_floor_stat_mult(bundle: dict[str, Any], floor_number: int) -> None:
    """Доп. множитель из JSON пака (floor_stat_mult)."""
    from game.tower.trials.pack_config import get_trial_config

    cfg = get_trial_config(int(floor_number)) or {}
    mult = float(cfg.get("floor_stat_mult") or 1.0)
    if mult <= 1.0:
        return
    bundle["hp"] = max(1, int(bundle["hp"] * mult))
    bundle["max_hp"] = bundle["hp"]
    bundle["atk"] = max(1, int(bundle["atk"] * mult))
    bundle["defense"] = max(0, int(bundle.get("defense", 0) * mult))
