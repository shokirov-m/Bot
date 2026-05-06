"""
Ремесленные материалы (гача, крафт мастерской и мгновенная кузня).

Хранение в сумке: kind=\"craft_resource\", resource_id, count.
⭐1 … ⭐6 — редкость для UI.
"""

from __future__ import annotations

import random
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.repository import inventory_repo

PROF_SMITH = "blacksmith"
PROF_ALCHEMIST = "alchemist"
PROF_JEWELER = "jeweler"


def stars_display(n: int) -> str:
    k = max(1, min(6, int(n)))
    return "⭐" * k


def rarity_key_for_stars(stars: int) -> str:
    """
    Редкость материалов по ⭐:
    1 common, 2 uncommon, 3 rare, 4 epic, 5 legendary, 6 mythic.
    """
    s = max(1, min(6, int(stars)))
    return ("common", "uncommon", "rare", "epic", "legendary", "mythic")[s - 1]


# Кузнец: слитки и сплавы (12)
# Алхимик: травы и реагенты (12)
# Ювелир: крошка и самоцветы (12)
RESOURCE_DEFS: dict[str, dict[str, Any]] = {
    # -------- Кузнец --------
    "copper_ingot": {
        "name_ru": "Слиток меди",
        "emoji": "🟠",
        "stars": 1,
        "profession": PROF_SMITH,
        "summary": "Базовый металл для простых заготовок.",
    },
    "iron_ingot": {
        "name_ru": "Слиток железа",
        "emoji": "⚙️",
        "stars": 1,
        "profession": PROF_SMITH,
        "summary": "Прочное железо для оружия и брони.",
    },
    "steel_ingot": {
        "name_ru": "Слиток стали",
        "emoji": "🔩",
        "stars": 2,
        "profession": PROF_SMITH,
        "summary": "Качественная сталь.",
    },
    "silver_ingot": {
        "name_ru": "Серебряный слиток",
        "emoji": "⬜",
        "stars": 2,
        "profession": PROF_SMITH,
        "summary": "Серебро для инкрустаций и лёгкой брони.",
    },
    "hardened_steel": {
        "name_ru": "Закалённая сталь",
        "emoji": "🔶",
        "stars": 3,
        "profession": PROF_SMITH,
        "summary": "Усиленный сплав.",
    },
    "mithril_ingot": {
        "name_ru": "Мифриловый слиток",
        "emoji": "💠",
        "stars": 3,
        "profession": PROF_SMITH,
        "summary": "Лёгкий и прочный мифрил.",
    },
    "dark_steel": {
        "name_ru": "Тёмная сталь",
        "emoji": "⬛",
        "stars": 3,
        "profession": PROF_SMITH,
        "summary": "Сплав с магической устойчивостью.",
    },
    "dragon_bone": {
        "name_ru": "Кость дракона",
        "emoji": "🦴",
        "stars": 4,
        "profession": PROF_SMITH,
        "summary": "Редкая основа для элитного оружия.",
    },
    "obsidian": {
        "name_ru": "Обсидиан",
        "emoji": "🖤",
        "stars": 4,
        "profession": PROF_SMITH,
        "summary": "Вулканическое стекло для острых кромок.",
    },
    "skysteel": {
        "name_ru": "Небесное железо",
        "emoji": "☁️",
        "stars": 5,
        "profession": PROF_SMITH,
        "summary": "Редчайший металл с башенных вершин.",
    },
    "adamantite": {
        "name_ru": "Адамантий",
        "emoji": "💎",
        "stars": 6,
        "profession": PROF_SMITH,
        "summary": "Вершина кузнечного мастерства.",
    },
    "titan_blood": {
        "name_ru": "Кровь титана",
        "emoji": "🩸",
        "stars": 6,
        "profession": PROF_SMITH,
        "summary": "Жидкий металл легендарной закалки.",
    },
    # -------- Алхимик --------
    "meadow_herb": {
        "name_ru": "Луговая трава",
        "emoji": "🌿",
        "stars": 1,
        "profession": PROF_ALCHEMIST,
        "summary": "Базовое сырьё для настоев.",
    },
    "moss_fungus": {
        "name_ru": "Моховой гриб",
        "emoji": "🍄",
        "stars": 1,
        "profession": PROF_ALCHEMIST,
        "summary": "Грибы для простых смесей.",
    },
    "blue_berry": {
        "name_ru": "Синяя ягода",
        "emoji": "🫐",
        "stars": 2,
        "profession": PROF_ALCHEMIST,
        "summary": "Ягоды эфира для зелий.",
    },
    "mandrake_root": {
        "name_ru": "Корень мандрагоры",
        "emoji": "🌱",
        "stars": 2,
        "profession": PROF_ALCHEMIST,
        "summary": "Сильный алхимический корень.",
    },
    "spirit_pollen": {
        "name_ru": "Пыльца духов",
        "emoji": "✨",
        "stars": 2,
        "profession": PROF_ALCHEMIST,
        "summary": "Лёгкая пыльца для маны и зачарований.",
    },
    "void_rose_thorn": {
        "name_ru": "Шип розы пустоши",
        "emoji": "🥀",
        "stars": 3,
        "profession": PROF_ALCHEMIST,
        "summary": "Колючий реагент средней силы.",
    },
    "golem_tear": {
        "name_ru": "Слеза голема",
        "emoji": "💧",
        "stars": 3,
        "profession": PROF_ALCHEMIST,
        "summary": "Минеральная слеза для стабилизации смесей.",
    },
    "basilisk_scale": {
        "name_ru": "Чешуя василиска",
        "emoji": "🐍",
        "stars": 3,
        "profession": PROF_ALCHEMIST,
        "summary": "Яд и защита в одном компоненте.",
    },
    "moon_dust": {
        "name_ru": "Лунная пыль",
        "emoji": "🌙",
        "stars": 4,
        "profession": PROF_ALCHEMIST,
        "summary": "Редкая пыль для сильных эликсиров.",
    },
    "phoenix_flower": {
        "name_ru": "Цветок феникса",
        "emoji": "🔥",
        "stars": 4,
        "profession": PROF_ALCHEMIST,
        "summary": "Огненная сердцевина зелья.",
    },
    "void_essence": {
        "name_ru": "Эссенция бездны",
        "emoji": "🌀",
        "stars": 5,
        "profession": PROF_ALCHEMIST,
        "summary": "Концентрат высшей алхимии.",
    },
    "golden_apple": {
        "name_ru": "Золотое яблоко",
        "emoji": "🍎",
        "stars": 6,
        "profession": PROF_ALCHEMIST,
        "summary": "Мифический плод для легендарных эликсиров.",
    },
    # -------- Алхимик: реагенты зачарования (доп. линейка) --------
    "light_dust": {
        "name_ru": "Светопыль",
        "emoji": "✨",
        "stars": 1,
        "profession": PROF_ALCHEMIST,
        "summary": "Лёгкая пыль для простых свитков усиления.",
    },
    "raven_bone": {
        "name_ru": "Кость ворона",
        "emoji": "🪶",
        "stars": 1,
        "profession": PROF_ALCHEMIST,
        "summary": "Тёмная кость для знаков и смесей.",
    },
    "storm_spark": {
        "name_ru": "Искра грозы",
        "emoji": "⚡",
        "stars": 2,
        "profession": PROF_ALCHEMIST,
        "summary": "Заряд для ударных настоев.",
    },
    "phoenix_ash": {
        "name_ru": "Пепел феникса",
        "emoji": "🔥",
        "stars": 2,
        "profession": PROF_ALCHEMIST,
        "summary": "Тлеющий остаток возрождения.",
    },
    "frost_crystal": {
        "name_ru": "Кристалл мороза",
        "emoji": "❄️",
        "stars": 2,
        "profession": PROF_ALCHEMIST,
        "summary": "Холодная сердцевина для защиты.",
    },
    "harpy_feather": {
        "name_ru": "Перо гарпии",
        "emoji": "🪶",
        "stars": 3,
        "profession": PROF_ALCHEMIST,
        "summary": "Лёгкий компонент для воздушных эффектов.",
    },
    "earth_salt": {
        "name_ru": "Соль земли",
        "emoji": "🧂",
        "stars": 3,
        "profession": PROF_ALCHEMIST,
        "summary": "Минеральная стабильность для брони.",
    },
    "gargoyle_blood": {
        "name_ru": "Кровь горгульи",
        "emoji": "🩸",
        "stars": 3,
        "profession": PROF_ALCHEMIST,
        "summary": "Вязкая кровь каменных стражей.",
    },
    "hydra_scale": {
        "name_ru": "Чешуя гидры",
        "emoji": "🐉",
        "stars": 4,
        "profession": PROF_ALCHEMIST,
        "summary": "Многослойная защита от яда.",
    },
    "wind_spirit": {
        "name_ru": "Дух ветра",
        "emoji": "🌬️",
        "stars": 4,
        "profession": PROF_ALCHEMIST,
        "summary": "Нестабильная эссенция скорости.",
    },
    "dragon_flame": {
        "name_ru": "Пламя дракона",
        "emoji": "🐲",
        "stars": 5,
        "profession": PROF_ALCHEMIST,
        "summary": "Концентрированное пламя для высших свитков.",
    },
    "quintessence": {
        "name_ru": "Квинтэссенция",
        "emoji": "🌟",
        "stars": 6,
        "profession": PROF_ALCHEMIST,
        "summary": "Пятый элемент — вершина алхимии зачарования.",
    },
    # -------- Ювелир --------
    "copper_dust": {
        "name_ru": "Медная крошка",
        "emoji": "✴️",
        "stars": 1,
        "profession": PROF_JEWELER,
        "summary": "Крошка для пайки и оправ.",
    },
    "river_pearl": {
        "name_ru": "Речная жемчужина",
        "emoji": "⚪",
        "stars": 1,
        "profession": PROF_JEWELER,
        "summary": "Простая жемчужина.",
    },
    "tiger_eye": {
        "name_ru": "Тигровый глаз",
        "emoji": "🟤",
        "stars": 2,
        "profession": PROF_JEWELER,
        "summary": "Камень для простых украшений.",
    },
    "moonstone": {
        "name_ru": "Лунный камень",
        "emoji": "💠",
        "stars": 2,
        "profession": PROF_JEWELER,
        "summary": "Мягкое магическое свечение.",
    },
    "amber": {
        "name_ru": "Янтарь",
        "emoji": "🟡",
        "stars": 2,
        "profession": PROF_JEWELER,
        "summary": "Застывшая смола с включениями.",
    },
    "blood_ruby": {
        "name_ru": "Кровавый рубин",
        "emoji": "♦️",
        "stars": 3,
        "profession": PROF_JEWELER,
        "summary": "Насыщенный красный камень.",
    },
    "storm_sapphire": {
        "name_ru": "Сапфир бури",
        "emoji": "🔷",
        "stars": 3,
        "profession": PROF_JEWELER,
        "summary": "Синий камень с искрой молнии.",
    },
    "life_emerald": {
        "name_ru": "Изумруд жизни",
        "emoji": "💚",
        "stars": 3,
        "profession": PROF_JEWELER,
        "summary": "Зелёный камень для амулетов.",
    },
    "black_opal": {
        "name_ru": "Чёрный опал",
        "emoji": "⚫",
        "stars": 4,
        "profession": PROF_JEWELER,
        "summary": "Глубокий переливающийся камень.",
    },
    "void_diamond": {
        "name_ru": "Алмаз пустоты",
        "emoji": "💎",
        "stars": 4,
        "profession": PROF_JEWELER,
        "summary": "Прозрачный камень с тёмным ядром.",
    },
    "cyclops_eye": {
        "name_ru": "Глаз циклопа",
        "emoji": "👁️",
        "stars": 5,
        "profession": PROF_JEWELER,
        "summary": "Редкая сфера для фокусирующих украшений.",
    },
    "star_heart": {
        "name_ru": "Сердце звезды",
        "emoji": "🌟",
        "stars": 6,
        "profession": PROF_JEWELER,
        "summary": "Легендарное ядро для вершинных изделий.",
    },
}


def resource_ids_for_profession(profession: str) -> list[str]:
    p = str(profession).strip().lower()
    return [rid for rid, d in RESOURCE_DEFS.items() if str(d.get("profession")) == p]


def craft_resource_payload(resource_id: str, count: int = 1) -> dict[str, Any]:
    rid = str(resource_id).strip()
    d = RESOURCE_DEFS.get(rid)
    if d is None:
        return {
            "kind": "craft_resource",
            "resource_id": rid,
            "name": f"📦 Ресурс ({rid})",
            "count": max(1, int(count)),
            "stars": 1,
            "rarity": "common",
            "summary": "Неизвестный ремесленный ресурс.",
        }
    stars = int(d.get("stars") or 1)
    emoji = str(d.get("emoji") or "📦")
    name_ru = str(d.get("name_ru") or rid)
    label = f"{stars_display(stars)} {emoji} {name_ru}"
    return {
        "kind": "craft_resource",
        "resource_id": rid,
        "name": label,
        "count": max(1, int(count)),
        "stars": stars,
        "rarity": rarity_key_for_stars(stars),
        "summary": str(d.get("summary") or ""),
    }


def total_craft_resource_in_bag(bag_items: list[Any], resource_id: str) -> int:
    rid = str(resource_id).strip()
    total = 0
    for it in bag_items:
        d = it.item_data or {}
        if str(d.get("kind")) != "craft_resource":
            continue
        if str(d.get("resource_id")) != rid:
            continue
        total += max(1, int(d.get("count") or 1))
    return total


def roll_stack_count_for_stars(stars: int) -> int:
    """Сколько единиц выдать за один приз гачи (дешёвое — пачкой, объёмы ниже старых ×3–7)."""
    s = int(stars)
    if s >= 6:
        return 1
    if s >= 4:
        return random.randint(1, 2)
    if s >= 3:
        return random.randint(1, 2)
    return random.randint(1, 3)


async def consume_craft_resources(
    session: AsyncSession,
    character_id: int,
    craft_cost: dict[str, int],
) -> None:
    """Списать ремесленные ресурсы по resource_id."""
    if not craft_cost:
        return
    cid = int(character_id)
    for res_id, need in craft_cost.items():
        remaining = max(0, int(need))
        if remaining <= 0:
            continue
        target = str(res_id)
        while remaining > 0:
            bag = await inventory_repo.list_bag_items(session, cid)
            stacks = [
                it
                for it in bag
                if str((it.item_data or {}).get("kind")) == "craft_resource"
                and str((it.item_data or {}).get("resource_id")) == target
            ]
            if not stacks:
                break
            it = stacks[0]
            d = dict(it.item_data or {})
            cur = max(1, int(d.get("count") or 1))
            if cur <= remaining:
                remaining -= cur
                await inventory_repo.delete_inventory_item(session, it)
            else:
                d["count"] = cur - remaining
                it.item_data = d
                remaining = 0
            await session.flush()
    await session.flush()


def gacha_weights_for_profession(profession: str) -> dict[str, float]:
    """Веса по звёздам: чем выше ⭐, тем реже (чуть снижен шанс редкого к ×6)."""
    out: dict[str, float] = {}
    for rid in resource_ids_for_profession(profession):
        st = int(RESOURCE_DEFS[rid].get("stars") or 1)
        out[rid] = max(0.2, 140.0 / (2.15 ** (st - 1)))
    return out
