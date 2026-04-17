"""
Усиление экипировки по rarity при чтении из item_data (атака, защита, бонусы статов).
"""

from __future__ import annotations

from typing import Any

_VALID_RARITY = frozenset({"common", "uncommon", "rare", "epic", "legendary"})

_WEAPON_ATK_FLAT: dict[str, int] = {
    "common": 0,
    "uncommon": 3,
    "rare": 7,
    "epic": 11,
    "legendary": 16,
}

_WEAPON_ATK_MULT: dict[str, float] = {
    "common": 1.0,
    "uncommon": 1.07,
    "rare": 1.17,
    "epic": 1.25,
    "legendary": 1.37,
}

_ARMOR_DEF_FLAT: dict[str, int] = {
    "common": 0,
    "uncommon": 5,
    "rare": 12,
    "epic": 18,
    "legendary": 26,
}

_ARMOR_DEF_MULT: dict[str, float] = {
    "common": 1.0,
    "uncommon": 1.10,
    "rare": 1.24,
    "epic": 1.34,
    "legendary": 1.46,
}

# Уровень заточки (+0…+15): доп. защита на броне/бижутерии, сильнее на высокой редкости.
_ENCHANT_ARMOR_DEF_PER_LEVEL: dict[str, float] = {
    "common": 1.1,
    "uncommon": 1.45,
    "rare": 1.85,
    "epic": 2.25,
    "legendary": 2.75,
}

_ARMOR_KINDS: frozenset[str] = frozenset(
    {"armor", "pants", "helmet", "gloves", "ring", "amulet", "shield", "grimoire", "tome", "orb", "focus"},
)


def _norm_rarity(item_data: dict[str, Any] | None) -> str:
    if not item_data:
        return "common"
    r = str(item_data.get("rarity") or "common").lower().strip()
    return r if r in _VALID_RARITY else "common"


def scaled_weapon_attack_value(base_attack: int, item_data: dict[str, Any] | None) -> int:
    """Базовая атака с карточки × множитель редкости + небольшой плоский бонус."""
    if base_attack <= 0:
        return base_attack
    r = _norm_rarity(item_data)
    mul = float(_WEAPON_ATK_MULT.get(r, 1.0))
    flat = int(_WEAPON_ATK_FLAT.get(r, 0))
    return max(1, int(round(base_attack * mul)) + flat)


def scaled_armor_defense_value(base_defense: int, item_data: dict[str, Any] | None) -> int:
    """Защита с карточки × множитель редкости + плоский бонус."""
    if base_defense <= 0:
        return 0
    r = _norm_rarity(item_data)
    mul = float(_ARMOR_DEF_MULT.get(r, 1.0))
    flat = int(_ARMOR_DEF_FLAT.get(r, 0))
    return max(0, int(round(base_defense * mul)) + flat)


def armor_enchant_defensive_bonus(enchant_level: int, item_data: dict[str, Any] | None) -> int:
    """Защита от +заточки на не-оружии: растёт с редкостью и уровнем заточки (ранг +)."""
    e = max(0, min(15, int(enchant_level)))
    if e <= 0:
        return 0
    r = _norm_rarity(item_data)
    per = float(_ENCHANT_ARMOR_DEF_PER_LEVEL.get(r, 1.1))
    return max(0, int(round(e * per)))


def apply_stored_gear_balance_boost_v3(item_data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """
    Одноразовый bump полей в JSON предмета (сумка/экип/лот): защита и статы на броне.
    Возвращает (новый dict, изменился ли).
    """
    d = dict(item_data or {})
    if not d:
        return d, False
    kind = str(d.get("kind") or "").lower()
    if kind in ("consumable", "rune", "weapon"):
        return d, False
    atk = int(d.get("attack", d.get("atk", 0)) or 0)
    if atk > 0:
        return d, False
    bd0 = int(d.get("defense", d.get("armor", 0)) or 0)
    if kind not in _ARMOR_KINDS and bd0 <= 0:
        return d, False

    r = _norm_rarity(d)
    def_add = {"common": 1, "uncommon": 2, "rare": 4, "epic": 6, "legendary": 9}.get(r, 1)
    stat_add = {"common": 0, "uncommon": 0, "rare": 1, "epic": 2, "legendary": 3}.get(r, 0)

    changed = False
    for key in ("defense", "armor"):
        if key not in d:
            continue
        old = int(d[key] or 0)
        if old <= 0:
            continue
        nv = max(1, int(round(old * 1.07)) + def_add)
        if nv != old:
            d[key] = nv
            changed = True

    stat_keys = ("str", "dex", "int", "vit", "luck")
    if stat_add:
        for k in stat_keys:
            if int(d.get(k) or 0) > 0:
                d[k] = int(d[k]) + stat_add
                changed = True
        sb = d.get("stat_bonus")
        if isinstance(sb, dict):
            sb2 = dict(sb)
            touched = False
            for k in stat_keys:
                if int(sb2.get(k) or 0) > 0:
                    sb2[k] = int(sb2[k]) + stat_add
                    touched = True
            if touched:
                d["stat_bonus"] = sb2
                changed = True

    return d, changed


def extra_stat_points_for_rarity_on_item(item_data: dict[str, Any] | None) -> int:
    """Сколько очков добавить к каждому ненулевому стату (см. stat_bonuses_from_item_data)."""
    return int(
        {
            "common": 0,
            "uncommon": 3,
            "rare": 6,
            "epic": 9,
            "legendary": 12,
        }.get(_norm_rarity(item_data), 0),
    )
