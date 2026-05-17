"""
Постоянные бонусы из VIP-магазина (Telegram Stars), не связанные с обликами профиля.
"""

from __future__ import annotations

from datetime import UTC, datetime

from db.models.character import Character

# Ключ в meta_progress после покупки «Владыка морозного трона»
VIP_FROST_LORD_THRONE_KEY = "vip_shop_frost_throne_art_v1"
VIP_BONUS_ID_FROST_THRONE = "frost_throne_v1"


def has_frost_throne_bundle(character: Character) -> bool:
    raw = (character.meta_progress or {}).get(VIP_FROST_LORD_THRONE_KEY)
    return raw is True or (isinstance(raw, dict) and bool(raw.get("owned")))


def unlock_frost_throne_bundle(character: Character) -> None:
    mp = dict(character.meta_progress or {})
    mp[VIP_FROST_LORD_THRONE_KEY] = {"owned": True, "purchased_at": datetime.now(UTC).isoformat()}
    character.meta_progress = mp


def gold_bonus_pct(character: Character) -> int:
    """+5% к золоту с победы (перемножается с титулами и др.)."""
    return 5 if has_frost_throne_bundle(character) else 0


def ice_elemental_bonus_percent(character: Character, runes_list: list) -> int:
    """
    +15% к элементальному множителю урона, если атака считается ледяной:
    на оружии есть руна льда ИЛИ стихия персонажа — лёд.
    """
    if not has_frost_throne_bundle(character):
        return 0
    for r in runes_list:
        el = str(getattr(r, "element", "") or "").strip().lower()
        if el == "ice":
            return 15
    ch = str(character.element or "").strip().lower()
    if ch == "ice":
        return 15
    return 0
