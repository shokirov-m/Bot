"""Таблицы дропа после победы (сумка)."""

from __future__ import annotations

import copy
import random
from typing import Any

from game.floors.monsters import FloorMonsterSpawn
from game.items import catalog_loot
from utils.image_assets import item_gear_png


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
    elixir = {
        "name": "Настой странника",
        "kind": "consumable",
        "rarity": "common",
        "use_tag": "heal_hp_pct",
        "use_value": min(35, 18 + fl // 6),
        "summary": "В бою: восстанавливает % от макс. HP.",
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
    options: tuple[tuple[float, dict[str, Any]], ...] = (
        (1.15, elixir),
        (0.95, mp_vial),
        (0.62, pct_vial),
    )
    cat = catalog_loot.roll_catalog_item(fl)
    if cat is not None:
        options = options + ((1.2, cat),)
    return _weighted_payload(options)


def _elite_loot(fl: int, spawn: FloorMonsterSpawn) -> dict[str, Any]:
    elixir = {
        "name": "Флакон эликсира",
        "kind": "consumable",
        "rarity": "common",
        "use_tag": "heal_hp_pct",
        "use_value": min(50, 25 + fl // 5),
        "summary": "В бою: сильнее восстанавливает HP в процентах.",
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
    elite_options: tuple[tuple[float, dict[str, Any]], ...] = (
        (0.85, elixir),
        (0.55, ether),
    )
    cat = catalog_loot.roll_catalog_item(fl)
    if cat is not None:
        elite_options = elite_options + ((1.0, cat),)
    return _weighted_payload(elite_options)


def _mini_boss_loot(fl: int, spawn: FloorMonsterSpawn) -> dict[str, Any]:
    bundle = {
        "name": "Запас претендента",
        "kind": "consumable",
        "rarity": "uncommon",
        "use_tag": "heal_hp_pct",
        "use_value": min(60, 35 + fl // 4),
        "summary": "В бою: мощное восстановление HP в процентах.",
        "image_url": item_gear_png("mini_bundle"),
    }
    mini_options: tuple[tuple[float, dict[str, Any]], ...] = (
        (0.45, bundle),
    )
    cat = catalog_loot.roll_catalog_item(fl)
    if cat is not None:
        mini_options = mini_options + ((1.2, cat),)
    return _weighted_payload(mini_options)


def _major_boss_loot(fl: int, spawn: FloorMonsterSpawn) -> dict[str, Any]:
    chest = {
        "name": "Сосуд триумфа",
        "kind": "consumable",
        "rarity": "rare",
        "use_tag": "heal_hp_pct",
        "use_value": 55,
        "summary": "В бою: мощное восстановление HP.",
        "image_url": item_gear_png("major_chest"),
    }
    major_options: tuple[tuple[float, dict[str, Any]], ...] = (
        (0.56, chest),
    )
    cat = catalog_loot.roll_catalog_item(fl)
    if cat is not None:
        major_options = major_options + ((1.5, cat),)
    return _weighted_payload(major_options)
