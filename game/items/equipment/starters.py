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


def starter_weapon_payload(class_key: str) -> dict[str, Any]:
    """Имена и ATK — баланс v2.0 (предмети 0,1.txt); картинка — общая заглушка."""
    table_full: dict[str, tuple[str, int, str, str, bool, dict[str, int]]] = {
        "wanderer": ("Клинок Пилигрима", 14, "Первый клинок странника у врат Башни.", "blade", False, {}),
        "star_touched": ("Осколок Утренней Звезды", 16, "Откликается на звёздную удачу.", "staff", False, {"int": 3}),
        "tower_reaper": ("Коса Посвящения", 22, "Каждая победа делает лезвие острее.", "polearm", True, {}),
        "warrior": ("Сталь Рекрута", 18, "Надёжный клинок новобранца.", "blade", False, {}),
        "mage": ("Посох Искр", 16, "Фокусирует ману ученика.", "staff", False, {"int": 5}),
        "archer": ("Лук Новичка", 18, "Для первых выстрелов в Башне.", "bow", True, {}),
        "priest": ("Посох Утешителя", 15, "Благословлён для странников.", "staff", False, {"vit": 5}),
        "assassin": ("Парный Кинжал", 17, "Основа тихого стиля.", "dagger", False, {}),
        "berserker": ("Топор Ярости", 22, "Тяжёлый, как обещание крови.", "axe", False, {}),
        "necromancer": ("Костяной Жезл", 16, "Шепчет с мёртвыми.", "staff", False, {"int": 4}),
        "warden": ("Молот Стража", 18, "Удар несёт страж.", "hammer", False, {"vit": 6}),
        "shaman": ("Тотемный Клык", 17, "Резонанс с духами.", "blade", False, {"int": 4}),
        "hunter": ("Нож Следопыта", 19, "Для зверей и монстров.", "blade", False, {"dex": 4}),
    }
    name, atk, summary, wtype, two_handed, extra_stats = table_full.get(
        class_key,
        ("Путевой клинок", 14, "Начало пути в Башне.", "blade", False, {}),
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
        "image_url": item_gear_png("placeholder_item"),
    }
    d.update(extra_stats)
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
