"""
Мастерство типа оружия: удары в бою (атака и урон навыком) → пороги 50/150/500/1000.
Бонус только к урону с этим типом оружия (множитель).
"""

from __future__ import annotations

import re
from typing import Any

from db.models.character import Character

META_KEY = "weapon_mastery_v1"
THRESHOLDS: tuple[int, ...] = (50, 150, 500, 1000)

# Родительный падеж для строки «Мастерство …» (как в UI полных характеристик).
WEAPON_MASTERY_NAME_RU: dict[str, str] = {
    "blade": "меча",
    "staff": "посоха",
    "bow": "лука",
    "dagger": "кинжала",
    "axe": "топора",
    "polearm": "древкового",
    "hammer": "молота",
    "unarmed": "рукопаша",
}
# множитель урона по уровню мастерства 0..4
MULT_BY_TIER: tuple[float, ...] = (1.0, 1.02, 1.04, 1.07, 1.11)


def infer_weapon_type_from_name(name: str | None) -> str:
    if not name:
        return "blade"
    n = name.lower()
    if re.search(r"лук|bow", n):
        return "bow"
    if re.search(r"посох|staff|жезл|wand|кристалл", n):
        return "staff"
    if re.search(r"коса|косы|косой|polearm|глеф|секир", n):
        return "polearm"
    if re.search(r"топор|axe", n):
        return "axe"
    if re.search(r"кинжал|dagger|парные", n):
        return "dagger"
    if re.search(r"молот|hammer", n):
        return "hammer"
    if re.search(r"нож|клинок|меч|sword|клинок|клинка", n):
        return "blade"
    return "blade"


def weapon_type_from_item_data(data: dict[str, Any] | None) -> str:
    if not data:
        return "blade"
    wt = data.get("weapon_type")
    if isinstance(wt, str) and wt.strip():
        return wt.strip().lower()
    return infer_weapon_type_from_name(str(data.get("name") or ""))


def _load_mastery(meta: dict[str, Any]) -> dict[str, dict[str, int]]:
    raw = meta.get(META_KEY)
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, int]] = {}
    for k, v in raw.items():
        if isinstance(v, dict) and "hits" in v:
            out[str(k)] = {"hits": max(0, int(v.get("hits", 0)))}
    return out


def _save_mastery(character: Character, data: dict[str, dict[str, int]]) -> None:
    mp = dict(character.meta_progress or {})
    mp[META_KEY] = {k: {"hits": int(v.get("hits", 0))} for k, v in data.items()}
    character.meta_progress = mp


def tier_for_hits(hits: int) -> int:
    t = 0
    for th in THRESHOLDS:
        if hits >= th:
            t += 1
        else:
            break
    return min(t, len(MULT_BY_TIER) - 1)


def damage_multiplier_for_type(character: Character, weapon_type: str) -> float:
    data = _load_mastery(character.meta_progress or {})
    row = data.get(weapon_type, {"hits": 0})
    hits = int(row.get("hits", 0))
    return MULT_BY_TIER[tier_for_hits(hits)]


def tier_for_character_weapon(character: Character, weapon_type: str) -> int:
    data = _load_mastery(character.meta_progress or {})
    row = data.get(weapon_type, {"hits": 0})
    return tier_for_hits(int(row.get("hits", 0)))


def record_strike(character: Character, weapon_type: str) -> tuple[int, int]:
    """
    +1 удар для типа. Возвращает (hits_после, tier).
    """
    mp = dict(character.meta_progress or {})
    data = _load_mastery(mp)
    cur = data.get(weapon_type, {"hits": 0})
    hits = int(cur.get("hits", 0)) + 1
    data[weapon_type] = {"hits": hits}
    _save_mastery(character, data)
    return hits, tier_for_hits(hits)


def mastery_profile_lines(character: Character, weapon_type: str) -> tuple[str, str]:
    """
    Две строки для полных характеристик: множитель урона и прогресс ударов до следующего порога.
    """
    from utils.telegram.ui import _BAR_LEN, _mono_bar, format_number

    data = _load_mastery(character.meta_progress or {})
    h = int(data.get(weapon_type, {}).get("hits", 0))
    mult = damage_multiplier_for_type(character, weapon_type)
    nm = WEAPON_MASTERY_NAME_RU.get(weapon_type, weapon_type)
    nm_disp = (nm[0].upper() + nm[1:]) if nm else nm
    line1 = f"Мастерство {nm_disp}: урон ×{mult:.2f}"
    nxt = next((t for t in THRESHOLDS if h < t), None)
    if nxt is None:
        bar = "█" * _BAR_LEN
        line2 = f"✨ {bar}  {format_number(h)}уд. (макс.)"
    else:
        bar = _mono_bar(h, nxt, _BAR_LEN)
        line2 = f"✨ {bar}  {format_number(h)}/{format_number(nxt)}уд."
    return line1, line2


_WEAPON_EMOJI: dict[str, str] = {
    "blade": "🗡",
    "staff": "🪄",
    "bow": "🏹",
    "dagger": "🗡",
    "axe": "🪓",
    "polearm": "🛡️",
    "hammer": "🔨",
    "unarmed": "👊",
}

# Краткое обозначение в строке «Все типы» (только кириллица).
WEAPON_TYPE_SHORT_RU: dict[str, str] = {
    "blade": "меч",
    "staff": "посох",
    "bow": "лук",
    "dagger": "кинжал",
    "axe": "топор",
    "polearm": "древковое",
    "hammer": "молот",
    "unarmed": "без оружия",
}


def mastery_all_types_line(character: Character) -> str:
    """Все ненулевые мастерства: «🗡 меч ур.3 (1240) · …» — без латиницы в подписях."""
    data = _load_mastery(character.meta_progress or {})
    if not data:
        return ""
    parts: list[str] = []
    items = sorted(data.items(), key=lambda kv: int(kv[1].get("hits", 0)), reverse=True)
    for wtype, row in items:
        h = int(row.get("hits", 0))
        if h <= 0:
            continue
        emo = _WEAPON_EMOJI.get(wtype, "🗡")
        tier = tier_for_hits(h)
        name_ru = WEAPON_TYPE_SHORT_RU.get(wtype, wtype)
        parts.append(f"{emo} {name_ru} ур.{tier} ({h})")
    if not parts:
        return ""
    return " · ".join(parts)


# Боевые бонусы за тиры мастерства (применяются для текущего типа оружия).
# tier 0..4. Используем поверх crit_bonus / extra_miss_chance / stun_chance.
def mastery_combat_bonus(tier: int) -> dict[str, float]:
    t = max(0, min(int(tier), 4))
    return {
        # tier 2 → +2% крит, tier 3 → −1% промах, tier 4 → +5% оглушение.
        "crit_bonus": 0.02 if t >= 2 else 0.0,
        "miss_reduction": 0.01 if t >= 3 else 0.0,
        "stun_chance": 0.05 if t >= 4 else 0.0,
    }


def mastery_summary_line(character: Character, weapon_type: str) -> str:
    data = _load_mastery(character.meta_progress or {})
    h = int(data.get(weapon_type, {}).get("hits", 0))
    tier = tier_for_hits(h)
    mult = MULT_BY_TIER[tier]
    nxt = next((t for t in THRESHOLDS if h < t), None)
    nm = WEAPON_TYPE_SHORT_RU.get(weapon_type, weapon_type)
    if nxt is None:
        return f"Мастерство ({nm}): <b>{h}</b> уд. · макс. ярус · урон ×{mult:.2f}"
    return f"Мастерство ({nm}): <b>{h}</b> уд. · ярус {tier}/4 · урон ×{mult:.2f} · до след. {nxt - h} уд."
