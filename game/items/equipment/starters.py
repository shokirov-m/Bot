"""Стартовые и промо-предметы."""

from __future__ import annotations

import copy
from typing import Any

from game.items.equipment.defaults import apply_item_payload_defaults
from game.items.equipment.item_asset_paths import item_gear_png


def starter_bread_payload() -> dict[str, Any]:
    d: dict[str, Any] = {
        "name": "Хлеб странника",
        "kind": "misc",
        "rarity": "common",
        "use_tag": "heal_hp_flat",
        "use_value": 42,
        "summary": "Передышка: восстанавливает HP. Можно съесть из сумки или в бою (предметы).",
        "image_url": item_gear_png("starter_bread"),
    }
    return copy.deepcopy(d)


def starter_pants_payload() -> dict[str, Any]:
    d: dict[str, Any] = {
        "name": "Поножи новичка",
        "kind": "pants",
        "rarity": "common",
        "defense": 1,
        "vit": 1,
        "summary": "Грубая стёжка — чуть меньше ушибов о перила.",
        "image_url": item_gear_png("starter_pants"),
    }
    apply_item_payload_defaults(d)
    return d


def starter_boots_payload() -> dict[str, Any]:
    d: dict[str, Any] = {
        "name": "Сапоги",
        "kind": "boots",
        "rarity": "common",
        "defense": 1,
        "dex": 1,
        "summary": "Против скользких ступеней башни.",
        "image_url": item_gear_png("starter_boots"),
    }
    apply_item_payload_defaults(d)
    return d


def starter_cloak_payload() -> dict[str, Any]:
    d: dict[str, Any] = {
        "name": "Плащ",
        "kind": "cloak",
        "rarity": "common",
        "defense": 1,
        "summary": "Лёгкий слой от сквозняков на этаже.",
        "image_url": item_gear_png("starter_cloak"),
    }
    apply_item_payload_defaults(d)
    return d


def starter_offhand_dagger_payload() -> dict[str, Any]:
    """Второй кинжал для левой руки (assassin и др.)."""
    d: dict[str, Any] = {
        "name": "Кинжал 2 руки",
        "kind": "weapon",
        "hand": "off",
        "rarity": "common",
        "attack": 5,
        "enchant": 0,
        "weapon_type": "dagger",
        "summary": "Лёгкий боковик — надевается во вторую руку.",
        "image_url": item_gear_png("starter_offhand_dagger"),
    }
    apply_item_payload_defaults(d)
    return d


_STARTER_WEAPON_STEM: dict[str, str] = {
    "wanderer": "starter_wpn_wanderer",
    "star_touched": "starter_wpn_star_touched",
    "tower_reaper": "starter_wpn_tower_reaper",
    "warrior": "starter_wpn_warrior",
    "mage": "starter_wpn_mage",
    "archer": "starter_wpn_archer",
    "priest": "starter_wpn_priest",
    "assassin": "starter_wpn_assassin",
    "berserker": "starter_wpn_berserker",
    "necromancer": "starter_wpn_necromancer",
    "warden": "starter_wpn_warden",
    "shaman": "starter_wpn_shaman",
    "hunter": "starter_wpn_hunter",
}


def starter_weapon_payload(class_key: str) -> dict[str, Any]:
    table_full: dict[str, tuple[str, int, str, str, bool]] = {
        "wanderer": ("Дорожный нож", 6, "Всё, что нужно страннику до перекрёстка.", "blade", False),
        "star_touched": ("Кристалл утренней звезды", 7, "Откликается на удачу.", "staff", False),
        "tower_reaper": ("Коса посвящения", 9, "Каждая победа делает лезвие острее.", "polearm", True),
        "warrior": ("Тренировочный меч", 9, "Надёжный клинок новобранца.", "blade", False),
        "mage": ("Учебный посох", 7, "Фокусирует ману ученика.", "staff", False),
        "archer": ("Простой лук", 8, "Для первых выстрелов в Башне.", "bow", True),
        "priest": ("Посох наставника", 6, "Благословлён для странников.", "staff", False),
        "assassin": ("Парный кинжал (правая рука)", 8, "Основа тихого стиля.", "dagger", False),
        "berserker": ("Топор новобранца", 10, "Тяжёлый, как обещание крови.", "axe", False),
        "necromancer": ("Костяной жезл", 7, "Шепчет с мёртвыми.", "staff", False),
        "warden": ("Боевой молот стража", 8, "Щит держишь ты — удар несёт молот.", "hammer", False),
        "shaman": ("Тотемный клинок", 7, "Резонанс с духами.", "blade", False),
        "hunter": ("Охотничий нож", 8, "Для зверей и монстров.", "blade", False),
    }
    name, atk, summary, wtype, two_handed = table_full.get(
        class_key,
        ("Путевой клинок", 7, "Начало пути в Башне.", "blade", False),
    )
    d: dict[str, Any] = {
        "name": name,
        "kind": "weapon",
        "rarity": "common",
        "attack": atk,
        "enchant": 0,
        "weapon_type": wtype,
        "summary": summary,
        "hand": "main",
        "image_url": item_gear_png(_STARTER_WEAPON_STEM.get(class_key, "starter_wpn_default")),
    }
    if two_handed:
        d["two_handed"] = True
    apply_item_payload_defaults(d)
    return d


def promo_starter_armor_amulet_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    a = copy.deepcopy(
        {
            "name": "Кольчуга дарства",
            "kind": "armor",
            "rarity": "common",
            "defense": 2,
            "vit": 1,
            "hp_bonus": 6,
            "summary": "Простая кольчуга из набора для нового восходителя — чуть крепче кожи.",
            "image_url": item_gear_png("promo_armor_gift"),
        },
    )
    b = copy.deepcopy(
        {
            "name": "Медальон яруса",
            "kind": "amulet",
            "rarity": "common",
            "defense": 1,
            "int": 1,
            "summary": "Слабый резонанс с маной башни — заметен только на нижних этажах.",
            "image_url": item_gear_png("promo_amulet_first"),
        },
    )
    apply_item_payload_defaults(a)
    apply_item_payload_defaults(b)
    return a, b


def referral_inviter_gear_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    a = copy.deepcopy(
        {
            "name": "Перчатки друга",
            "kind": "gloves",
            "rarity": "rare",
            "defense": 2,
            "str": 1,
            "dex": 2,
            "summary": "Редкий дар за приведённого друга — крепче и точнее удар.",
            "image_url": item_gear_png("referral_gloves"),
        },
    )
    b = copy.deepcopy(
        {
            "name": "Кольцо приглашения",
            "kind": "ring",
            "rarity": "rare",
            "defense": 2,
            "luck": 2,
            "summary": "Редкий талисман удачи за верного реферала.",
            "image_url": item_gear_png("referral_ring"),
        },
    )
    apply_item_payload_defaults(a)
    apply_item_payload_defaults(b)
    return a, b


def referral_inviter_epic_necklace_payload() -> dict[str, Any]:
    d = copy.deepcopy(
        {
            "name": "Ожерелье пяти верных",
            "kind": "amulet",
            "rarity": "epic",
            "defense": 3,
            "vit": 2,
            "int": 3,
            "luck": 1,
            "summary": "Эпический дар башни: пять героев по твоей ссылке достигли 3 уровня.",
            "image_url": item_gear_png("referral_epic_necklace"),
        },
    )
    apply_item_payload_defaults(d)
    return d
