"""Стартовые и промо-предметы."""

from __future__ import annotations

import copy
from typing import Any

from game.items.equipment.defaults import apply_item_payload_defaults
from utils.image_assets import item_gear_png


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


def hunter_set_uncommon_payloads() -> tuple[dict[str, Any], ...]:
    """Набор Охотника (9 предметов) — награда за промокод HUNTERSET."""
    items: list[dict[str, Any]] = [
        {
            "name": "Клинок Охотника",
            "kind": "weapon",
            "hand": "main",
            "rarity": "uncommon",
            "attack": 28,
            "dex": 6,
            "weapon_type": "blade",
            "summary": "Изогнутый клинок, отточенный для охоты на монстров Башни.",
            "image_url": item_gear_png("hunter_blade"),
        },
        {
            "name": "Кинжал Охотника",
            "kind": "weapon",
            "hand": "off",
            "rarity": "uncommon",
            "attack": 24,
            "dex": 4,
            "weapon_type": "dagger",
            "summary": "Лёгкий кинжал для левой руки — быстр и точен.",
            "image_url": item_gear_png("hunter_dagger"),
        },
        {
            "name": "Броня Охотника",
            "kind": "armor",
            "rarity": "uncommon",
            "defense": 30,
            "dex": 5,
            "vit": 3,
            "summary": "Кожаный доспех с металлическими вставками. Не сковывает движений.",
            "image_url": item_gear_png("hunter_armor"),
        },
        {
            "name": "Капюшон Охотника",
            "kind": "helmet",
            "rarity": "uncommon",
            "defense": 18,
            "dex": 8,
            "summary": "Скрывает лицо и заглушает шаги. Любимый выбор следопытов.",
            "image_url": item_gear_png("hunter_hood"),
        },
        {
            "name": "Поножи Охотника",
            "kind": "pants",
            "rarity": "uncommon",
            "defense": 22,
            "dex": 5,
            "summary": "Удобные поножи с кожаными ремешками. Идеальны для долгой погони.",
            "image_url": item_gear_png("hunter_legs"),
        },
        {
            "name": "Перчатки Охотника",
            "kind": "gloves",
            "rarity": "uncommon",
            "defense": 12,
            "dex": 6,
            "summary": "Тонкая кожа с обрезанными пальцами. Точный хват, быстрый выпад.",
            "image_url": item_gear_png("hunter_gloves"),
        },
        {
            "name": "Кольцо Охотника",
            "kind": "ring",
            "rarity": "uncommon",
            "defense": 8,
            "dex": 4,
            "luck": 2,
            "summary": "Простое кольцо с выгравированным следом зверя. Приносит удачу в охоте.",
            "image_url": item_gear_png("hunter_ring"),
        },
        {
            "name": "Кольцо Следопыта",
            "kind": "ring",
            "rarity": "uncommon",
            "defense": 6,
            "dex": 3,
            "ring_slot": 2,
            "summary": "Парное кольцо охотника — носится на второй руке.",
            "image_url": item_gear_png("tracker_ring"),
        },
        {
            "name": "Амулет Охотника",
            "kind": "amulet",
            "rarity": "uncommon",
            "defense": 10,
            "dex": 3,
            "vit": 2,
            "summary": "Клык зверя на кожаном шнурке. Охотник надевает его перед каждой вылазкой.",
            "image_url": item_gear_png("hunter_amulet"),
        },
    ]
    result = []
    for d in items:
        x = copy.deepcopy(d)
        apply_item_payload_defaults(x)
        result.append(x)
    return tuple(result)


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
