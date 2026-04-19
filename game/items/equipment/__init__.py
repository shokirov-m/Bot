"""
Экипировка: слоты, стартовые предметы, тайник, примеры контента.
Пакет заменяет прежний модуль `game/items/equipment.py`.
"""

from __future__ import annotations

from typing import Any

from game.items.equipment.constants import (
    ITEM_IMAGE_PLACEHOLDER_URL,
    RARITY_EMOJI,
    RARITY_NAME_RU,
    SECRET_GEAR_DROP_CHANCE,
    SECRET_GEAR_EARLY_MAX_FLOOR,
    SECRET_GEAR_MAX_FLOOR,
    UI_PLACEHOLDER_IMAGE_URL,
)
from game.items.equipment.defaults import apply_item_payload_defaults
from game.items.equipment.secret_gear import SECRET_GEAR_ITEMS, try_roll_secret_gear_payload
from game.items.equipment.slots import (
    EQUIP_ORDER,
    SLOT_LABEL_RU,
    equip_slot_for_kind,
    gear_icon_for_item_data,
    item_is_two_handed,
    resolve_equip_slot_for_item_data,
    ring_slot_is_explicit,
    slot_label_ru,
)
from game.items.equipment.starters import (
    promo_starter_armor_amulet_payloads,
    referral_inviter_epic_necklace_payload,
    referral_inviter_gear_payloads,
    starter_bread_payload,
    starter_offhand_dagger_payload,
    starter_pants_payload,
    starter_weapon_payload,
)


def __getattr__(name: str) -> Any:
    if name == "all_example_groups":
        from game.items.equipment.catalog_generated import all_example_groups as fn

        return fn
    raise AttributeError(name)


__all__ = [
    "ITEM_IMAGE_PLACEHOLDER_URL",
    "UI_PLACEHOLDER_IMAGE_URL",
    "RARITY_EMOJI",
    "RARITY_NAME_RU",
    "SECRET_GEAR_MAX_FLOOR",
    "SECRET_GEAR_DROP_CHANCE",
    "SECRET_GEAR_EARLY_MAX_FLOOR",
    "SECRET_GEAR_ITEMS",
    "EQUIP_ORDER",
    "SLOT_LABEL_RU",
    "equip_slot_for_kind",
    "slot_label_ru",
    "resolve_equip_slot_for_item_data",
    "ring_slot_is_explicit",
    "gear_icon_for_item_data",
    "item_is_two_handed",
    "apply_item_payload_defaults",
    "starter_bread_payload",
    "starter_weapon_payload",
    "starter_pants_payload",
    "starter_offhand_dagger_payload",
    "promo_starter_armor_amulet_payloads",
    "referral_inviter_gear_payloads",
    "referral_inviter_epic_necklace_payload",
    "try_roll_secret_gear_payload",
    "all_example_groups",
]
