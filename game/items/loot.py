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
    return _weighted_payload(
        (
            (1.2, elixir),
            (1.0, mp_vial),
            (0.65, pct_vial),
            (0.55, gloves),
            (0.28, ring),
            (0.12, trophy),
        ),
    )


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
