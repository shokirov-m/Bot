"""Таблицы дропа после победы (сумка)."""

from __future__ import annotations

import copy
import random
from typing import Any

from game.floors.monsters import FloorMonsterSpawn

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
    }
    mp_vial = {
        "name": "Капля маны",
        "kind": "misc",
        "rarity": "common",
        "use_tag": "heal_mp_flat",
        "use_value": min(70, 14 + fl * 2),
        "summary": "В бою: немного MP.",
    }
    pct_vial = {
        "name": "Слабый эликсир (проба)",
        "kind": "consumable",
        "rarity": "common",
        "use_tag": "heal_hp_pct",
        "use_value": min(30, 18 + fl // 4),
        "summary": "В бою: процент от макс. HP.",
    }
    gloves = {
        "name": f"Перчатки с этажа {fl}",
        "kind": "gloves",
        "rarity": "common",
        "defense": max(1, 1 + fl // 15),
        "summary": "Простая защита рук с тела поверженного.",
    }
    ring = {
        "name": f"Кольцо-оберег ({fl})",
        "kind": "ring",
        "rarity": "uncommon",
        "defense": max(1, 1 + fl // 20),
        "summary": "Слабая магическая аура.",
    }
    trophy = {
        "name": "Трофей с этажа",
        "kind": "misc",
        "rarity": "common",
        "summary": f"Уцелевший фрагмент после боя с {spawn.template.name.lower()}.",
    }
    wt = _rand_weapon_type()
    atk_low = max(4, 4 + fl // 3 + (1 if wt in ("dagger", "bow") else 0))
    forest_blade = {
        "name": f"Ржавый клинок леса ({fl})",
        "kind": "weapon",
        "rarity": "common",
        "attack": atk_low,
        "enchant": 0,
        "weapon_type": wt,
        "summary": "Первые яруши — любое оружие лучше кулаков.",
    }
    forest_staff = {
        "name": f"Сук ведьмы ({fl})",
        "kind": "weapon",
        "rarity": "common",
        "attack": max(3, atk_low - 1),
        "enchant": 0,
        "weapon_type": "staff",
        "summary": "Грубая магическая направляющая из корня.",
    }
    moss_armor = {
        "name": f"Моховая накидка ({fl})",
        "kind": "armor",
        "rarity": "common",
        "defense": max(2, 2 + fl // 8),
        "summary": "Пахнет лесом и чуть отталкивает когти.",
    }
    cap = {
        "name": f"Капюшон тропы ({fl})",
        "kind": "helmet",
        "rarity": "uncommon",
        "defense": max(1, 1 + fl // 10),
        "summary": "Скрывает лицо от лишних глаз.",
    }
    charm = {
        "name": "Костяной оберег",
        "kind": "amulet",
        "rarity": "uncommon",
        "defense": max(1, 1 + fl // 12),
        "summary": "Слабый резонанс — чуть крепче дух.",
    }
    boots_like = {
        "name": f"Обмотки путника ({fl})",
        "kind": "gloves",
        "rarity": "common",
        "defense": max(1, 1 + fl // 14),
        "dex": 1,
        "summary": "Не броня для ног — но ловкость в пути заметна.",
    }
    rare_edge = {
        "name": f"Клинок росы ({fl})",
        "kind": "weapon",
        "rarity": "uncommon",
        "attack": max(7, 6 + fl // 2),
        "enchant": 0,
        "weapon_type": random.choice(("blade", "polearm")),
        "summary": "Редкая удача на ранних этажах.",
    }
    options: tuple[tuple[float, dict[str, Any]], ...] = (
        (1.15, elixir),
        (0.95, mp_vial),
        (0.62, pct_vial),
        (0.52, gloves),
        (0.26, ring),
        (0.11, trophy),
    )
    if fl <= 12:
        options = options + (
            (0.42, forest_blade),
            (0.32, forest_staff),
            (0.38, moss_armor),
            (0.22, cap),
            (0.2, charm),
            (0.28, boots_like),
            (0.06, rare_edge),
        )
    return _weighted_payload(options)


def _elite_loot(fl: int, spawn: FloorMonsterSpawn) -> dict[str, Any]:
    wtype = _rand_weapon_type()
    atk = max(6, 7 + fl // 2 + (3 if wtype in ("staff", "dagger") else 0))
    defense = max(2, 3 + fl // 5)
    weapon = {
        "name": f"Добыча элиты ({fl})",
        "kind": "weapon",
        "rarity": "uncommon",
        "attack": atk,
        "enchant": 0,
        "weapon_type": wtype,
        "summary": f"Вытянут у {spawn.template.name.lower()}.",
    }
    armor = {
        "name": f"Накидка охотника ({fl})",
        "kind": "armor",
        "rarity": "uncommon",
        "defense": defense,
        "summary": "Крепче обычного лута.",
    }
    helm = {
        "name": f"Шлем из засады ({fl})",
        "kind": "helmet",
        "rarity": "common",
        "defense": max(1, defense // 2 + 1),
        "summary": "Спас от удара элиты.",
    }
    elixir = {
        "name": "Флакон эликсира",
        "kind": "misc",
        "rarity": "common",
        "use_tag": "heal_hp_flat",
        "use_value": min(140, 35 + fl * 3),
        "summary": "Сильнее добычи с обычных целей.",
    }
    ether = {
        "name": "Эфирный отвар",
        "kind": "consumable",
        "rarity": "common",
        "use_tag": "heal_mp_pct",
        "use_value": min(45, 22 + fl // 5),
        "summary": "В бою: восстановление MP в процентах.",
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
    atk = max(8, 10 + fl // 2)
    defense = max(4, 4 + fl // 4)
    weapon = {
        "name": f"Клык претендента ({fl})",
        "kind": "weapon",
        "rarity": "rare",
        "attack": atk,
        "enchant": max(1, fl // 40),
        "weapon_type": wtype,
        "summary": "Трофей мини-босса.",
    }
    armor = {
        "name": f"Латы претендента ({fl})",
        "kind": "armor",
        "rarity": "rare",
        "defense": defense,
        "summary": "Выдержали удар сильного врага.",
    }
    helm = {
        "name": "Шлем претендента",
        "kind": "helmet",
        "rarity": "uncommon",
        "defense": max(2, defense // 2),
        "summary": "Снят с поверженного стража этажа.",
    }
    gloves = {
        "name": "Рукавицы претендента",
        "kind": "gloves",
        "rarity": "uncommon",
        "defense": max(1, defense // 3),
        "summary": "Удобны в бою.",
    }
    bundle = {
        "name": "Запас претендента",
        "kind": "misc",
        "rarity": "uncommon",
        "use_tag": "heal_hp_flat",
        "use_value": min(200, 55 + fl * 4),
        "summary": "Мощное восстановление HP.",
    }
    return _weighted_payload(
        (
            (1.0, weapon),
            (0.92, armor),
            (0.65, helm),
            (0.5, gloves),
            (0.45, bundle),
        ),
    )


def _major_boss_loot(fl: int, spawn: FloorMonsterSpawn) -> dict[str, Any]:
    wtype = _rand_weapon_type()
    atk = max(12, 12 + (fl * 3) // 4)
    defense = max(5, 5 + fl // 3)
    ench = max(1, fl // 22)
    weapon = {
        "name": f"Коронный клинок ({fl})",
        "kind": "weapon",
        "rarity": "rare",
        "attack": atk,
        "enchant": ench,
        "weapon_type": wtype,
        "summary": f"Добыча с {spawn.template.name.lower()} — редкая находка.",
    }
    armor = {
        "name": f"Броня стража этажа ({fl})",
        "kind": "armor",
        "rarity": "rare",
        "defense": defense + 2,
        "summary": "Тяжёлая, но надёжная.",
    }
    amulet = {
        "name": "Печать этажа",
        "kind": "amulet",
        "rarity": "uncommon",
        "defense": max(2, defense // 3 + 1),
        "summary": "Символ победы над боссом.",
    }
    ring = {
        "name": f"Кольцо победителя ({fl})",
        "kind": "ring",
        "rarity": "rare",
        "defense": max(2, defense // 4 + 2),
        "summary": "Пульсирует остаточной силой босса.",
    }
    chest = {
        "name": "Сосуд триумфа",
        "kind": "consumable",
        "rarity": "rare",
        "use_tag": "heal_hp_pct",
        "use_value": 55,
        "summary": "В бою: мощное восстановление HP.",
    }
    return _weighted_payload(
        (
            (1.0, weapon),
            (0.95, armor),
            (0.55, amulet),
            (0.42, ring),
            (0.38, chest),
        ),
    )
