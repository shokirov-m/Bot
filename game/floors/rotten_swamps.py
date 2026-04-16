"""
Зона «Гнилые Болота» (этажи 11–20): токсичный туман, пиявки, густой туман на карте, заброшенный лагерь.
Состояние лагеря: meta_progress["rotten_swamps_v1"].
Перенос яда пиявок: meta_progress["swamp_leech_target_floor"] (int — этаж первого боя с дотом).
"""

from __future__ import annotations

import random
from typing import Any

from db.models.character import Character

META_BUCKET = "rotten_swamps_v1"
META_LEECH_TARGET = "swamp_leech_target_floor"
LEECH_INFECTION_CHANCE = 0.22


def is_rotten_swamps_zone(floor_number: int) -> bool:
    return 11 <= int(floor_number) <= 20


def _bucket(character: Character) -> dict[str, Any]:
    mp = dict(character.meta_progress or {})
    raw = mp.get(META_BUCKET)
    return dict(raw) if isinstance(raw, dict) else {}


def _save_bucket(character: Character, b: dict[str, Any]) -> None:
    mp = dict(character.meta_progress or {})
    mp[META_BUCKET] = b
    character.meta_progress = mp


def abandoned_camp_used(character: Character) -> bool:
    return bool(_bucket(character).get("camp_used"))


def set_abandoned_camp_used(character: Character) -> None:
    b = _bucket(character)
    b["camp_used"] = True
    _save_bucket(character, b)


def on_travel_floor_change(character: Character, old_floor: int, new_floor: int) -> None:
    """Сброс «лагеря» при выходе с 11–20; флаг пиявок не трогаем."""
    o, n = int(old_floor), int(new_floor)
    if o == n:
        return
    was_swamp = is_rotten_swamps_zone(o)
    now_swamp = is_rotten_swamps_zone(n)
    if was_swamp and not now_swamp:
        mp = dict(character.meta_progress or {})
        mp.pop(META_BUCKET, None)
        character.meta_progress = mp


def get_leech_target_floor(character: Character) -> int | None:
    mp = character.meta_progress or {}
    raw = mp.get(META_LEECH_TARGET)
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def set_leech_target_floor(character: Character, target_floor: int) -> None:
    mp = dict(character.meta_progress or {})
    mp[META_LEECH_TARGET] = int(target_floor)
    character.meta_progress = mp


def clear_leech_target(character: Character) -> None:
    mp = dict(character.meta_progress or {})
    if META_LEECH_TARGET not in mp:
        return
    mp.pop(META_LEECH_TARGET, None)
    character.meta_progress = mp


def maybe_roll_leech_infection_after_swamp_win(character: Character, battle_floor: int) -> None:
    """После победы на этаже болот — шанс занести яд на следующий этаж (первый бой там)."""
    bf = int(battle_floor)
    if not is_rotten_swamps_zone(bf):
        return
    if random.random() >= LEECH_INFECTION_CHANCE:
        return
    set_leech_target_floor(character, bf + 1)


def dense_fog_hides_spawn_on_map(spawn) -> bool:
    """Скрыть имя цели на экране этажа (не боссы / не элита)."""
    return not spawn.is_elite and not spawn.is_mini_boss and not spawn.is_major_boss


def mystery_spawn_label() -> str:
    return "🌫️ Силуэт в тумане"

