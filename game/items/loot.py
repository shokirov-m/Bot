"""Таблицы дропа после победы (сумка)."""

from __future__ import annotations

import copy
import random
from typing import Any

from game.floors.monsters import FloorMonsterSpawn
from game.items import loot_scaling as ls
from game.items.equipment.item_asset_paths import item_gear_png

_WEAPON_TYPES = ("blade", "staff", "bow", "dagger", "axe", "polearm", "hammer")


def _clamp_floor(floor_number: int) -> int:
    return max(1, min(100, int(floor_number)))


def _weighted_payload(options: tuple[tuple[float, dict[str, Any]], ...]) -> dict[str, Any]:
    total = sum(w for w, _ in options)
    r = random.uniform(0.0, total)
    acc = 0.0
    for w, data in options:
        acc += w
        if r <= acc:
            return copy.deepcopy(data)
    return copy.deepcopy(options[-1][1])


def _rand_weapon_type() -> str:
    return random.choice(_WEAPON_TYPES)


def roll_victory_item_payload(floor_number: int, spawn: FloorMonsterSpawn) -> dict[str, Any]:
    """Предмет в сумку при успешном roll_item_drop и свободной ячейке."""
    fl = _clamp_floor(floor_number)
    if spawn.is_major_boss:
        return _major_boss_loot(fl, spawn)
    if spawn.is_mini_boss:
        return _mini_boss_loot(fl, spawn)
    if spawn.is_elite:
        return _elite_loot(fl, spawn)
    return _normal_loot(fl, spawn)


def _normal_loot(fl: int, spawn: FloorMonsterSpawn) -> dict[str, Any]:
    heal = min(120, 22 + fl * 3)
    elixir = {
        "name": "Настой странника",
        "kind": "misc",
        "rarity": "common",
        "use_tag": "heal_hp_flat",
        "use_value": heal,
        "summary": "Восстанавливает HP после боя; можно применить в бою.",
        "image_url": item_gear_png("loot_elixir_flat"),
    }
    mp_vial = {
        "name": "Капля маны",
        "kind": "misc",
        "rarity": "common",
        "use_tag": "heal_mp_flat",
        "use_value": min(70, 14 + fl * 2),
        "summary": "В бою: немного MP.",
        "image_url": item_gear_png("loot_mp_flat"),
    }
    pct_vial = {
        "name": "Слабый эликсир (проба)",
        "kind": "consumable",
        "rarity": "common",
        "use_tag": "heal_hp_pct",
        "use_value": min(30, 18 + fl // 4),
        "summary": "В бою: процент от макс. HP.",
        "image_url": item_gear_png("loot_pct_hp"),
    }
    gloves = {
        "name": f"Перчатки {fl}",
        "kind": "gloves",
        "rarity": "common",
        "defense": ls.normal_gloves_defense(fl),
        "summary": "Простая защита рук с тела поверженного.",
        "image_url": item_gear_png("loot_gloves"),
    }
    ring = {
        "name": f"Кольцо {fl}",
        "kind": "ring",
        "rarity": "uncommon",
        "defense": ls.normal_ring_defense(fl),
        "summary": "Слабая магическая аура.",
        "image_url": item_gear_png("loot_ring"),
    }
    trophy = {
        "name": "Трофей с этажа",
        "kind": "misc",
        "rarity": "common",
        "summary": f"Уцелевший фрагмент после боя с {spawn.template.name.lower()}.",
        "image_url": item_gear_png("loot_trophy"),
    }
    wt = _rand_weapon_type()
    atk_low = ls.normal_weapon_attack_low(fl, dagger_or_bow=(wt in ("dagger", "bow")))
    forest_blade = {
        "name": f"Клинок {fl}",
        "kind": "weapon",
        "rarity": "common",
        "attack": atk_low,
        "enchant": 0,
        "weapon_type": wt,
        "summary": "Первые яруши — любое оружие лучше кулаков.",
        "image_url": item_gear_png("loot_weapon_blade"),
    }
    forest_staff = {
        "name": f"Сук {fl}",
        "kind": "weapon",
        "rarity": "common",
        "attack": max(3, atk_low - 1),
        "enchant": 0,
        "weapon_type": "staff",
        "summary": "Грубая магическая направляющая из корня.",
        "image_url": item_gear_png("loot_weapon_staff"),
    }
    moss_armor = {
        "name": f"Мох. накидка {fl}",
        "kind": "armor",
        "rarity": "common",
        "defense": ls.moss_armor_defense(fl),
        "hp_bonus": ls.moss_armor_hp_bonus(fl),
        "summary": "Пахнет лесом и чуть отталкивает когти.",
        "image_url": item_gear_png("loot_moss_armor"),
    }
    cap = {
        "name": f"Капюшон {fl}",
        "kind": "helmet",
        "rarity": "uncommon",
        "defense": ls.cap_defense(fl),
        "summary": "Скрывает лицо от лишних глаз.",
        "image_url": item_gear_png("loot_cap"),
    }
    charm = {
        "name": "Оберег",
        "kind": "amulet",
        "rarity": "uncommon",
        "defense": ls.charm_defense(fl),
        "summary": "Слабый резонанс — чуть крепче дух.",
        "image_url": item_gear_png("loot_charm_amulet"),
    }
    boots_like = {
        "name": f"Сапоги {fl}",
        "kind": "boots",
        "rarity": "common",
        "defense": ls.boots_defense(fl),
        "dex": 1,
        "summary": "Шаги по лестнице башни чуть увереннее.",
        "image_url": item_gear_png("loot_boots_wraps"),
    }
    rare_edge = {
        "name": f"Роса {fl}",
        "kind": "weapon",
        "rarity": "uncommon",
        "attack": ls.rare_edge_attack(fl),
        "enchant": 0,
        "weapon_type": random.choice(("blade", "polearm")),
        "summary": "Редкая удача на ранних этажах.",
        "image_url": item_gear_png("loot_rare_edge"),
    }
    atk_dex_pair = ls.normal_weapon_attack_low(fl, dagger_or_bow=True)
    twin_main = {
        "name": f"Кинжал пары {fl}",
        "kind": "weapon",
        "rarity": "uncommon",
        "attack": atk_dex_pair,
        "enchant": 0,
        "weapon_type": "dagger",
        "dex": 1,
        "luck": 1,
        "summary": "Лёгкий клинок для ловкого стиля — ищи второй во вторую руку.",
        "image_url": item_gear_png("loot_weapon_blade"),
    }
    twin_off = {
        "name": f"Боковик пары {fl}",
        "kind": "weapon",
        "rarity": "uncommon",
        "attack": max(3, atk_dex_pair - 2),
        "enchant": 0,
        "weapon_type": "dagger",
        "hand": "off",
        "dex": 1,
        "luck": 1,
        "summary": "Вторая половина пары — надевается во вторую руку.",
        "image_url": item_gear_png("loot_weapon_blade"),
    }
    greatsword = {
        "name": f"Клеймор уступа {fl}",
        "kind": "weapon",
        "rarity": "uncommon",
        "attack": ls.greatsword_attack(fl),
        "enchant": 0,
        "weapon_type": "blade",
        "two_handed": True,
        "str": 1,
        "summary": "Тяжёлый двуручник — для тех, кто качает силу.",
        "image_url": item_gear_png("loot_weapon_blade"),
    }
    balanced_blade = {
        "name": f"Меч равновесия {fl}",
        "kind": "weapon",
        "rarity": "uncommon",
        "attack": ls.normal_weapon_attack_low(fl, dagger_or_bow=False),
        "enchant": 0,
        "weapon_type": "blade",
        "vit": 1,
        "summary": "Универсальный клинок в паре со щитом.",
        "image_url": item_gear_png("loot_weapon_blade"),
    }
    balanced_buckler = {
        "name": f"Щит равновесия {fl}",
        "kind": "shield",
        "rarity": "uncommon",
        "defense": ls.balanced_shield_defense(fl),
        "vit": 1,
        "summary": "Лёгкий щит под меч равновесия.",
        "image_url": item_gear_png("catalog_shield_01"),
    }
    arcane_staff = {
        "name": f"Посох дуги {fl}",
        "kind": "weapon",
        "rarity": "uncommon",
        "attack": max(4, ls.normal_weapon_attack_low(fl, dagger_or_bow=False) - 1),
        "enchant": 0,
        "weapon_type": "staff",
        "int": 2,
        "summary": "Основной фокус мага — длинная дуга маны.",
        "image_url": item_gear_png("loot_weapon_staff"),
    }
    focus_wand = {
        "name": f"Палочка фокуса {fl}",
        "kind": "weapon",
        "rarity": "common",
        "attack": max(3, ls.normal_weapon_attack_low(fl, dagger_or_bow=False) - 3),
        "enchant": 0,
        "weapon_type": "staff",
        "int": 1,
        "luck": 1,
        "summary": "Короткий жезл для точечных заклинаний.",
        "image_url": item_gear_png("loot_weapon_staff"),
    }
    apprentice_grimoire = {
        "name": f"Гримуар заметок {fl}",
        "kind": "grimoire",
        "rarity": "common",
        "defense": 1,
        "int": 2,
        "summary": "Вторая рука мага — формулы и чары.",
        "image_url": item_gear_png("catalog_grimoire_01"),
    }
    options: tuple[tuple[float, dict[str, Any]], ...] = (
        (1.15, elixir),
        (0.95, mp_vial),
        (0.62, pct_vial),
        (0.52, gloves),
        (0.26, ring),
        (0.22, boots_like),
        (0.11, trophy),
    )
    if fl <= 12:
        options = options + (
            (0.34, forest_blade),
            (0.26, forest_staff),
            (0.38, moss_armor),
            (0.22, cap),
            (0.2, charm),
            (0.06, rare_edge),
            (0.1, twin_main),
            (0.09, twin_off),
            (0.08, greatsword),
            (0.07, balanced_blade),
            (0.07, balanced_buckler),
            (0.08, arcane_staff),
            (0.07, focus_wand),
            (0.07, apprentice_grimoire),
        )
    return _weighted_payload(options)


def _elite_loot(fl: int, spawn: FloorMonsterSpawn) -> dict[str, Any]:
    wtype = _rand_weapon_type()
    atk = ls.elite_weapon_attack(fl, staff_or_dagger=(wtype in ("staff", "dagger")))
    defense = ls.elite_armor_defense_base(fl)
    weapon = {
        "name": f"Элита {fl}",
        "kind": "weapon",
        "rarity": "uncommon",
        "attack": atk,
        "enchant": 0,
        "weapon_type": wtype,
        "summary": f"Вытянут у {spawn.template.name.lower()}.",
        "image_url": item_gear_png("elite_weapon"),
    }
    armor = {
        "name": f"Накидка {fl}",
        "kind": "armor",
        "rarity": "uncommon",
        "defense": defense,
        "hp_bonus": ls.elite_armor_hp_bonus(fl),
        "summary": "Крепче обычного лута.",
        "image_url": item_gear_png("elite_armor"),
    }
    helm = {
        "name": f"Шлем {fl}",
        "kind": "helmet",
        "rarity": "common",
        "defense": ls.elite_helm_defense(fl, defense),
        "summary": "Спас от удара элиты.",
        "image_url": item_gear_png("elite_helm"),
    }
    elixir = {
        "name": "Флакон эликсира",
        "kind": "misc",
        "rarity": "common",
        "use_tag": "heal_hp_flat",
        "use_value": min(140, 35 + fl * 3),
        "summary": "Сильнее добычи с обычных целей.",
        "image_url": item_gear_png("elite_elixir"),
    }
    ether = {
        "name": "Эфирный отвар",
        "kind": "consumable",
        "rarity": "common",
        "use_tag": "heal_mp_pct",
        "use_value": min(45, 22 + fl // 5),
        "summary": "В бою: восстановление MP в процентах.",
        "image_url": item_gear_png("elite_ether"),
    }
    return _weighted_payload(
        (
            (1.0, weapon),
            (0.95, armor),
            (0.7, helm),
            (0.85, elixir),
            (0.55, ether),
        ),
    )


def _mini_boss_loot(fl: int, spawn: FloorMonsterSpawn) -> dict[str, Any]:
    wtype = _rand_weapon_type()
    atk = ls.mini_weapon_attack(fl)
    defense = ls.mini_armor_defense(fl)
    weapon = {
        "name": f"Клык {fl}",
        "kind": "weapon",
        "rarity": "rare",
        "attack": atk,
        "enchant": ls.mini_weapon_enchant(fl),
        "weapon_type": wtype,
        "summary": "Трофей мини-босса.",
        "image_url": item_gear_png("mini_weapon"),
    }
    armor = {
        "name": f"Латы {fl}",
        "kind": "armor",
        "rarity": "rare",
        "defense": defense,
        "hp_bonus": ls.mini_armor_hp_bonus(fl),
        "summary": "Выдержали удар сильного врага.",
        "image_url": item_gear_png("mini_armor"),
    }
    helm = {
        "name": "Шлем претендента",
        "kind": "helmet",
        "rarity": "uncommon",
        "defense": ls.mini_helm_defense(fl, defense),
        "summary": "Снят с поверженного стража этажа.",
        "image_url": item_gear_png("mini_helm"),
    }
    gloves = {
        "name": "Рукавицы претендента",
        "kind": "gloves",
        "rarity": "uncommon",
        "defense": ls.mini_gloves_defense(fl, defense),
        "summary": "Удобны в бою.",
        "image_url": item_gear_png("mini_gloves"),
    }
    boots_mini = {
        "name": f"Сапоги претендента {fl}",
        "kind": "boots",
        "rarity": "uncommon",
        "defense": max(2, ls.boots_defense(fl) + max(1, defense // 12)),
        "dex": 1,
        "summary": "Трофей с телохранителя этажа.",
        "image_url": item_gear_png("loot_boots_wraps"),
    }
    bundle = {
        "name": "Запас претендента",
        "kind": "misc",
        "rarity": "uncommon",
        "use_tag": "heal_hp_flat",
        "use_value": min(200, 55 + fl * 4),
        "summary": "Мощное восстановление HP.",
        "image_url": item_gear_png("mini_bundle"),
    }
    return _weighted_payload(
        (
            (1.0, weapon),
            (0.92, armor),
            (0.65, helm),
            (0.5, gloves),
            (0.42, boots_mini),
            (0.45, bundle),
        ),
    )


def _major_boss_loot(fl: int, spawn: FloorMonsterSpawn) -> dict[str, Any]:
    wtype = _rand_weapon_type()
    atk = ls.major_weapon_attack(fl)
    defense = ls.major_armor_defense(fl)
    ench = ls.major_weapon_enchant(fl)
    weapon = {
        "name": f"Корона {fl}",
        "kind": "weapon",
        "rarity": "rare",
        "attack": atk,
        "enchant": ench,
        "weapon_type": wtype,
        "summary": f"Добыча с {spawn.template.name.lower()} — редкая находка.",
        "image_url": item_gear_png("major_weapon"),
    }
    armor = {
        "name": f"Страж {fl}",
        "kind": "armor",
        "rarity": "rare",
        "defense": defense + 2,
        "hp_bonus": ls.major_armor_hp_bonus(fl),
        "summary": "Тяжёлая, но надёжная.",
        "image_url": item_gear_png("major_armor"),
    }
    amulet = {
        "name": "Печать этажа",
        "kind": "amulet",
        "rarity": "uncommon",
        "defense": ls.major_amulet_defense(fl, defense),
        "summary": "Символ победы над боссом.",
        "image_url": item_gear_png("major_amulet"),
    }
    ring = {
        "name": f"Победа {fl}",
        "kind": "ring",
        "rarity": "rare",
        "defense": ls.major_ring_defense(fl, defense),
        "summary": "Пульсирует остаточной силой босса.",
        "image_url": item_gear_png("major_ring"),
    }
    boots_major = {
        "name": f"Сапоги триумфа {fl}",
        "kind": "boots",
        "rarity": "rare",
        "defense": max(3, ls.boots_defense(fl) + max(2, defense // 10)),
        "dex": 1,
        "vit": 1,
        "summary": "Шаг победителя по пеплу этажа.",
        "image_url": item_gear_png("loot_boots_wraps"),
    }
    chest = {
        "name": "Сосуд триумфа",
        "kind": "consumable",
        "rarity": "rare",
        "use_tag": "heal_hp_pct",
        "use_value": 55,
        "summary": "В бою: мощное восстановление HP.",
        "image_url": item_gear_png("major_chest"),
    }
    return _weighted_payload(
        (
            (1.0, weapon),
            (0.95, armor),
            (0.55, amulet),
            (0.42, ring),
            (0.36, boots_major),
            (0.38, chest),
        ),
    )
