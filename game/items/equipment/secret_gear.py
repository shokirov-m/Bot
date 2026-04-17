"""Тайник: ранний пул и масштабируемая не-оружейная экипировка."""

from __future__ import annotations

import copy
import random
from typing import Any

from game.items.equipment.constants import (
    RARITY_NAME_RU,
    SECRET_GEAR_DROP_CHANCE,
    SECRET_GEAR_EARLY_MAX_FLOOR,
    SECRET_GEAR_MAX_FLOOR,
)
from game.items.equipment.defaults import apply_item_payload_defaults
from game.items.equipment.item_asset_paths import item_gear_png, procedural_secret_gear_image

SECRET_GEAR_ITEMS: tuple[tuple[float, dict[str, Any]], ...] = (
    (
        1.0,
        {
            "name": "Кольчуга",
            "kind": "armor",
            "rarity": "common",
            "defense": 2,
            "vit": 1,
            "hp_bonus": 5,
            "summary": "Кольца железа на коже — немного тяжелее шага, зато меньше синяков.",
            "image_url": item_gear_png("secret_armor_chain"),
        },
    ),
    (
        0.95,
        {
            "name": "Шлем странника",
            "kind": "helmet",
            "rarity": "common",
            "defense": 1,
            "str": 1,
            "summary": "Старый шлем из кладовой: видел десятки первых этажей.",
            "image_url": item_gear_png("secret_helm_wanderer"),
        },
    ),
    (
        1.0,
        {
            "name": "Кожаные перчатки",
            "kind": "gloves",
            "rarity": "common",
            "defense": 1,
            "dex": 1,
            "summary": "Удобны в пути; пальцы не скользят по рукояти.",
            "image_url": item_gear_png("secret_gloves_leather"),
        },
    ),
    (
        0.9,
        {
            "name": "Поножи странника",
            "kind": "pants",
            "rarity": "common",
            "defense": 1,
            "vit": 1,
            "summary": "Грубая кожа на коленях — меньше ссадин в лазутках.",
            "image_url": item_gear_png("secret_pants_wanderer"),
        },
    ),
    (
        0.85,
        {
            "name": "Обломок медальона",
            "kind": "amulet",
            "rarity": "common",
            "defense": 1,
            "int": 1,
            "summary": "Осколок амулета — слабый резонанс с маной башни.",
            "image_url": item_gear_png("secret_amulet_shard"),
        },
    ),
    (
        0.8,
        {
            "name": "Кольцо из башни",
            "kind": "ring",
            "rarity": "common",
            "defense": 1,
            "luck": 1,
            "summary": "Простое кольцо из щели камня; мелкая удача на твоей стороне.",
            "image_url": item_gear_png("secret_ring_tower"),
        },
    ),
    (
        0.45,
        {
            "name": "Перстень посланника",
            "kind": "ring",
            "rarity": "uncommon",
            "defense": 1,
            "luck": 2,
            "set_key": "messenger",
            "set_piece": "ring",
            "summary": "Набор «Посланник башни»: удача кружит вокруг пальца (1/2).",
            "image_url": item_gear_png("secret_ring_messenger"),
        },
    ),
    (
        0.35,
        {
            "name": "Медальон посланника",
            "kind": "amulet",
            "rarity": "uncommon",
            "defense": 2,
            "int": 2,
            "set_key": "messenger",
            "set_piece": "amulet",
            "summary": "Набор «Посланник башни»: ясность мысли в дымке ярусов (2/2).",
            "image_url": item_gear_png("secret_amulet_messenger"),
        },
    ),
    (
        0.4,
        {
            "name": "Кольцо зелёного света",
            "kind": "ring",
            "rarity": "uncommon",
            "defense": 1,
            "int": 2,
            "luck": 1,
            "summary": "Вставка мерцает — чуть яснее мысль в бою.",
            "image_url": item_gear_png("secret_ring_green"),
        },
    ),
    (
        0.3,
        {
            "name": "Рунные перчатки",
            "kind": "gloves",
            "rarity": "rare",
            "defense": 2,
            "str": 2,
            "dex": 1,
            "summary": "Швы светятся слабым знаком — удар чувствуется острее.",
            "image_url": item_gear_png("secret_gloves_runic"),
        },
    ),
    (
        0.22,
        {
            "name": "Шлем карателя этажа",
            "kind": "helmet",
            "rarity": "rare",
            "defense": 3,
            "str": 2,
            "vit": 1,
            "summary": "Снят с каменного стража; в нём пахнет громом.",
            "image_url": item_gear_png("secret_helm_slayer"),
        },
    ),
    (
        0.12,
        {
            "name": "Амулет тьмы яруса",
            "kind": "amulet",
            "rarity": "epic",
            "defense": 2,
            "int": 3,
            "luck": 2,
            "summary": "Редкая находка: тьма башни собралась в камне.",
            "image_url": item_gear_png("secret_amulet_darkness"),
        },
    ),
    (
        0.06,
        {
            "name": "Корона первых сорока",
            "kind": "helmet",
            "rarity": "legendary",
            "defense": 4,
            "vit": 3,
            "luck": 2,
            "summary": "Легенда нижних колец — тем, кто рискнул заглянуть в тайник.",
            "image_url": item_gear_png("secret_helm_crown_low"),
        },
    ),
)

_KINDS_HIGH: tuple[tuple[str, str, str], ...] = (
    ("armor", "Броня", "🛡️"),
    ("pants", "Поножи", "👖"),
    ("helmet", "Шлем", "⛑️"),
    ("gloves", "Перчатки", "🧤"),
    ("ring", "Кольцо", "💍"),
    ("amulet", "Амулет", "📿"),
)


def _roll_early_secret_gear() -> dict[str, Any]:
    total_w = sum(w for w, _ in SECRET_GEAR_ITEMS)
    r = random.uniform(0.0, total_w)
    acc = 0.0
    for w, data in SECRET_GEAR_ITEMS:
        acc += w
        if r <= acc:
            out = copy.deepcopy(data)
            apply_item_payload_defaults(out)
            return out
    out = copy.deepcopy(SECRET_GEAR_ITEMS[-1][1])
    apply_item_payload_defaults(out)
    return out


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
    if kind == "pants":
        return {"vit": 1 * mult, "dex": max(0, mult - 1)}
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
    payload["image_url"] = procedural_secret_gear_image(kind)
    apply_item_payload_defaults(payload)
    return payload


def try_roll_secret_gear_payload(floor_number: int) -> dict[str, Any] | None:
    if floor_number < 1 or floor_number > SECRET_GEAR_MAX_FLOOR:
        return None
    if random.random() >= SECRET_GEAR_DROP_CHANCE:
        return None
    if floor_number <= SECRET_GEAR_EARLY_MAX_FLOOR:
        return _roll_early_secret_gear()
    return copy.deepcopy(_scaled_secret_gear(floor_number))
