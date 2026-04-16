"""
Глобальные пассивы: не от класса и не от титула/звания.
Разблокировка по прогрессу, список ключей в meta.global_passives_unlocked.
"""

from __future__ import annotations

from db.models.character import Character

META_UNLOCKED = "global_passives_unlocked"

# Ключ → дельта к боевым пассивам (как path_passive)
GLOBAL_PASSIVE_LABELS_RU: dict[str, str] = {
    "gp_first_steps": "Первые шаги башни (+1 защита в бою)",
    "gp_bloodied": "Кровь полей (+1% крит)",
    "gp_depth5": "Глубина (+2% к магии)",
    "gp_tower_walker": "Ходок ярусов (+1 защита, +1% уклонение)",
    "gp_veteran_spirit": "Дух ветерана (+1 MP за ход)",
}

GLOBAL_PASSIVE_DELTAS: dict[str, dict[str, float | int]] = {
    "gp_first_steps": {"def_bonus": 1.0},
    "gp_bloodied": {"crit_bonus": 0.01},
    "gp_depth5": {"mag_bonus_percent": 2},
    "gp_tower_walker": {"dodge_bonus": 0.01, "def_bonus": 1.0},
    "gp_veteran_spirit": {"mp_regen_turn": 1},
}


def _list_unlocked(meta: dict) -> list[str]:
    raw = meta.get(META_UNLOCKED)
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw]


def refresh_global_passives(character: Character) -> list[str]:
    """
    Проверить условия и дописать ключи. Возвращает только что открытые.
    """
    meta = dict(character.meta_progress or {})
    have = set(_list_unlocked(meta))
    new: list[str] = []

    def add(key: str) -> None:
        nonlocal new
        if key not in have and key in GLOBAL_PASSIVE_DELTAS:
            have.add(key)
            new.append(key)

    if int(character.floor_number) >= 3:
        add("gp_first_steps")
    if int(character.total_kills) >= 8:
        add("gp_bloodied")
    if int(character.floor_number) >= 12:
        add("gp_depth5")
    if int(character.floor_number) >= 25:
        add("gp_tower_walker")
    if int(character.level) >= 12:
        add("gp_veteran_spirit")

    if new:
        meta[META_UNLOCKED] = sorted(have)
        character.meta_progress = meta
    return new


def format_unlocked_global_passives_ru(character: Character) -> str:
    keys = _list_unlocked(character.meta_progress or {})
    if not keys:
        return "—"
    parts = [GLOBAL_PASSIVE_LABELS_RU.get(k, k) for k in sorted(keys)]
    return "; ".join(parts)


def global_passive_delta(meta: dict | None) -> dict[str, float | int]:
    if not meta:
        return {}
    out: dict[str, float | int] = {}
    for k in _list_unlocked(meta):
        row = GLOBAL_PASSIVE_DELTAS.get(k)
        if not row:
            continue
        for pk, pv in row.items():
            if pk == "mp_regen_turn":
                out[pk] = int(out.get(pk, 0)) + int(pv)
            elif pk == "mag_bonus_percent":
                out[pk] = int(out.get(pk, 0)) + int(pv)
            else:
                out[pk] = float(out.get(pk, 0)) + float(pv)
    return out
