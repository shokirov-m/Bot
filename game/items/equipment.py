"""
Слоты экипировки и стартовая экипировка по классу.
kind в item_data → equip_slot в БД.
"""

from __future__ import annotations

import copy
import random
from typing import Any

# Тайник: шанс экипировки после успешного «сундука» (бета: +30% к базовому 0.42).
SECRET_GEAR_MAX_FLOOR = 100
SECRET_GEAR_DROP_CHANCE = min(0.95, 0.55 * 1.2)
SECRET_GEAR_EARLY_MAX_FLOOR = 3

# Эмодзи редкости для UI (дублируется в utils.ui для карточек).
RARITY_EMOJI: dict[str, str] = {
    "common": "⚪",
    "uncommon": "🟢",
    "rare": "🔵",
    "epic": "🟣",
    "legendary": "🌟",
}

RARITY_NAME_RU: dict[str, str] = {
    "common": "Обычный",
    "uncommon": "Необычный",
    "rare": "Редкий",
    "epic": "Эпический",
    "legendary": "Легендарный",
}

# Ранний тайник: вес → предмет (русские описания, часть с бонусами к статам / наборам).
SECRET_GEAR_ITEMS: tuple[tuple[float, dict[str, Any]], ...] = (
    (1.0, {"name": "Потёртая кольчуга", "kind": "armor", "rarity": "common", "defense": 2, "vit": 1, "summary": "Кольца железа на коже — немного тяжелее шага, зато меньше синяков."}),
    (0.95, {"name": "Шлем странника", "kind": "helmet", "rarity": "common", "defense": 1, "str": 1, "summary": "Старый шлем из кладовой: видел десятки первых этажей."}),
    (1.0, {"name": "Кожаные перчатки", "kind": "gloves", "rarity": "common", "defense": 1, "dex": 1, "summary": "Удобны в пути; пальцы не скользят по рукояти."}),
    (0.85, {"name": "Обломок медальона", "kind": "amulet", "rarity": "common", "defense": 1, "int": 1, "summary": "Осколок амулета — слабый резонанс с маной башни."}),
    (0.8, {"name": "Кольцо из башни", "kind": "ring", "rarity": "common", "defense": 1, "luck": 1, "summary": "Простое кольцо из щели камня; мелкая удача на твоей стороне."}),
    (0.45, {"name": "Перстень посланника", "kind": "ring", "rarity": "uncommon", "defense": 1, "luck": 2, "set_key": "messenger", "set_piece": "ring", "summary": "Набор «Посланник башни»: удача кружит вокруг пальца (1/2)."}),
    (0.35, {"name": "Медальон посланника", "kind": "amulet", "rarity": "uncommon", "defense": 2, "int": 2, "set_key": "messenger", "set_piece": "amulet", "summary": "Набор «Посланник башни»: ясность мысли в дымке ярусов (2/2)."}),
    (0.4, {"name": "Кольцо зелёного света", "kind": "ring", "rarity": "uncommon", "defense": 1, "int": 2, "luck": 1, "summary": "Вставка мерцает — чуть яснее мысль в бою."}),
    (0.3, {"name": "Рунные перчатки", "kind": "gloves", "rarity": "rare", "defense": 2, "str": 2, "dex": 1, "summary": "Швы светятся слабым знаком — удар чувствуется острее."}),
    (0.22, {"name": "Шлем карателя этажа", "kind": "helmet", "rarity": "rare", "defense": 3, "str": 2, "vit": 1, "summary": "Снят с каменного стража; в нём пахнет громом."}),
    (0.12, {"name": "Амулет тьмы яруса", "kind": "amulet", "rarity": "epic", "defense": 2, "int": 3, "luck": 2, "summary": "Редкая находка: тьма башни собралась в камне."}),
    (0.06, {"name": "Корона первых сорока", "kind": "helmet", "rarity": "legendary", "defense": 4, "vit": 3, "luck": 2, "summary": "Легенда нижних колец — тем, кто рискнул заглянуть в тайник."}),
)

# Порядок отображения в UI
EQUIP_ORDER: tuple[str, ...] = ("weapon", "armor", "helmet", "gloves", "ring", "amulet")

SLOT_LABEL_RU: dict[str, str] = {
    "weapon": "🗡️ Оружие",
    "armor": "🛡️ Броня",
    "helmet": "⛑️ Шлем",
    "gloves": "🧤 Перчатки",
    "ring": "💍 Кольцо",
    "amulet": "📿 Амулет",
}

_KIND_TO_SLOT: dict[str, str] = {
    "weapon": "weapon",
    "armor": "armor",
    "helmet": "helmet",
    "gloves": "gloves",
    "ring": "ring",
    "amulet": "amulet",
}


def equip_slot_for_kind(kind: str | None) -> str | None:
    if not kind:
        return None
    return _KIND_TO_SLOT.get(str(kind).lower())


def slot_label_ru(slot: str) -> str:
    return SLOT_LABEL_RU.get(slot, slot)


def starter_bread_payload() -> dict[str, Any]:
    """Стартовый хлеб: передышка, HP вне и в бою."""
    return {
        "name": "Хлеб странника",
        "kind": "misc",
        "rarity": "common",
        "use_tag": "heal_hp_flat",
        "use_value": 42,
        "summary": "Передышка: восстанавливает HP. Можно съесть из сумки или в бою (предметы).",
    }


def _roll_early_secret_gear() -> dict[str, Any]:
    total_w = sum(w for w, _ in SECRET_GEAR_ITEMS)
    r = random.uniform(0.0, total_w)
    acc = 0.0
    for w, data in SECRET_GEAR_ITEMS:
        acc += w
        if r <= acc:
            return copy.deepcopy(data)
    return copy.deepcopy(SECRET_GEAR_ITEMS[-1][1])


_KINDS_HIGH: tuple[tuple[str, str, str], ...] = (
    ("armor", "Броня", "🛡️"),
    ("helmet", "Шлем", "⛑️"),
    ("gloves", "Перчатки", "🧤"),
    ("ring", "Кольцо", "💍"),
    ("amulet", "Амулет", "📿"),
)


def _pick_rarity_for_floor(floor_number: int, tier: int) -> str:
    r = random.random()
    if floor_number >= 75 and tier >= 6:
        return random.choices(
            ["rare", "epic", "legendary", "uncommon"],
            weights=[0.38, 0.28, 0.07, 0.27],
            k=1,
        )[0]
    if floor_number >= 40:
        return random.choices(
            ["uncommon", "rare", "epic", "common"],
            weights=[0.35, 0.38, 0.12, 0.15],
            k=1,
        )[0]
    return random.choices(
        ["common", "uncommon", "rare"],
        weights=[0.52, 0.35, 0.13],
        k=1,
    )[0]


def _stat_pack_for_kind(kind: str, rarity: str) -> dict[str, int]:
    mult = {"common": 1, "uncommon": 2, "rare": 3, "epic": 4, "legendary": 5}.get(rarity, 1)
    if kind == "armor":
        return {"vit": 1 * mult, "str": max(0, mult - 1)}
    if kind == "helmet":
        return {"str": 1 * mult, "vit": max(0, mult - 1)}
    if kind == "gloves":
        return {"dex": 1 * mult, "luck": max(0, mult - 1)}
    if kind == "ring":
        return {"luck": 1 * mult, "dex": max(0, mult - 1)}
    if kind == "amulet":
        return {"int": 1 * mult, "vit": max(0, mult - 1)}
    return {"vit": mult}


def _scaled_secret_gear(floor_number: int) -> dict[str, Any]:
    """Случайная не-оружейная вещь: русское имя, редкость, статы по типу и этажу."""
    tier = min(8, 1 + floor_number // 12)
    defense = 2 + tier + (1 if floor_number >= 50 else 0)
    kind, base, emo = random.choice(_KINDS_HIGH)
    rarity = _pick_rarity_for_floor(floor_number, tier)
    defense += {"common": 0, "uncommon": 1, "rare": 2, "epic": 3, "legendary": 5}.get(rarity, 0)
    stats = _stat_pack_for_kind(kind, rarity)
    rarity_ru = RARITY_NAME_RU.get(rarity, rarity)
    name = f"{emo} {base} «{rarity_ru}» — ярус {floor_number}"
    parts = [f"{base} из тайника; яркость яруса {tier}."]
    if random.random() < 0.12 and rarity in ("rare", "epic", "legendary"):
        parts.append("Часть легендарного стиля охотников на тайники.")
    payload: dict[str, Any] = {
        "name": name,
        "kind": kind,
        "rarity": rarity,
        "defense": defense,
        "summary": " ".join(parts),
    }
    for k, v in stats.items():
        if v:
            payload[k] = int(v)
    return payload


def promo_starter_armor_amulet_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    """Промокод: броня и амулет уровня первых этажей (в сумку, common)."""
    return (
        copy.deepcopy(
            {
                "name": "Кольчуга дарственника",
                "kind": "armor",
                "rarity": "common",
                "defense": 2,
                "vit": 1,
                "summary": "Простая кольчуга из набора для нового восходителя — чуть крепче кожи.",
            },
        ),
        copy.deepcopy(
            {
                "name": "Медальон первого яруса",
                "kind": "amulet",
                "rarity": "common",
                "defense": 1,
                "int": 1,
                "summary": "Слабый резонанс с маной башни — заметен только на нижних этажах.",
            },
        ),
    )


def referral_inviter_gear_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    """Две вещи редкой редкости пригласившему, когда приглашённый достигает 2 уровня."""
    return (
        copy.deepcopy(
            {
                "name": "Перчатки благодарности башни",
                "kind": "gloves",
                "rarity": "rare",
                "defense": 2,
                "str": 1,
                "dex": 2,
                "summary": "Редкий дар за приведённого друга — крепче и точнее удар.",
            },
        ),
        copy.deepcopy(
            {
                "name": "Кольцо приглашения",
                "kind": "ring",
                "rarity": "rare",
                "defense": 2,
                "luck": 2,
                "summary": "Редкий талисман удачи за верного реферала.",
            },
        ),
    )


def referral_inviter_epic_necklace_payload() -> dict[str, Any]:
    """Эпический амулет (ожерелье) пригласившему, когда пять друзей по ссылке достигли 3 уровня."""
    return copy.deepcopy(
        {
            "name": "Ожерелье пяти верных",
            "kind": "amulet",
            "rarity": "epic",
            "defense": 3,
            "vit": 2,
            "int": 3,
            "luck": 1,
            "summary": "Эпический дар башни: пять героев по твоей ссылке достигли 3 уровня.",
        },
    )


def try_roll_secret_gear_payload(floor_number: int) -> dict[str, Any] | None:
    """
    При успешной находке тайника — бросок на экипировку (ранние этажи: прежний пул; дальше — масштаб).
    """
    if floor_number < 1 or floor_number > SECRET_GEAR_MAX_FLOOR:
        return None
    if random.random() >= SECRET_GEAR_DROP_CHANCE:
        return None
    if floor_number <= SECRET_GEAR_EARLY_MAX_FLOOR:
        return _roll_early_secret_gear()
    return copy.deepcopy(_scaled_secret_gear(floor_number))


def starter_weapon_payload(class_key: str) -> dict[str, Any]:
    """Стартовое оружие в сумке данных предмета (надевается при создании героя)."""
    table_full: dict[str, tuple[str, int, str, str]] = {
        "wanderer": ("Дорожный нож", 6, "Всё, что нужно страннику до перекрёстка.", "blade"),
        "star_touched": ("Кристалл утренней звезды", 7, "Откликается на удачу.", "staff"),
        "tower_reaper": ("Коса посвящения", 9, "Каждая победа делает лезвие острее.", "polearm"),
        "warrior": ("Тренировочный меч", 9, "Надёжный клинок новобранца.", "blade"),
        "mage": ("Учебный посох", 7, "Фокусирует ману ученика.", "staff"),
        "archer": ("Простой лук", 8, "Для первых выстрелов в Башне.", "bow"),
        "priest": ("Посох наставника", 6, "Благословлён для странников.", "staff"),
        "assassin": ("Парные кинжалы", 8, "Тихие и острые.", "dagger"),
        "berserker": ("Топор новобранца", 10, "Тяжёлый, как обещание крови.", "axe"),
        "necromancer": ("Костяной жезл", 7, "Шепчет с мёртвыми.", "staff"),
        "warden": ("Боевой молот стража", 8, "Щит держишь ты — удар несёт молот.", "hammer"),
        "shaman": ("Тотемный клинок", 7, "Резонанс с духами.", "blade"),
        "hunter": ("Охотничий нож", 8, "Для зверей и монстров.", "blade"),
    }
    name, atk, summary, wtype = table_full.get(
        class_key,
        ("Путевой клинок", 7, "Начало пути в Башне.", "blade"),
    )
    return {
        "name": name,
        "kind": "weapon",
        "rarity": "common",
        "attack": atk,
        "enchant": 0,
        "weapon_type": wtype,
        "summary": summary,
    }
