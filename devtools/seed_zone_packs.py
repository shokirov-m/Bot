"""
Создаёт/обновляет паки зон (кроме blood_spire): zone.json, npcs, materials, blueprints.
Запуск из tower_bot/: python devtools/seed_zone_packs.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "content" / "data" / "packs" / "zones"

ZONE_SPECS: list[dict] = [
    {
        "key": "forest_beginnings",
        "name": "Лес Начал",
        "emoji": "🌲",
        "from": 1,
        "to": 10,
        "hub": 5,
        "theme": "forest",
        "npcs": [
            ("elara_herb", "Элара", "🌿", "alchemy", [
                ("fb_herb_bundle", "Сбор трав", "forest_moss", 15, {"pine_resin": 6}),
                ("fb_resin_jar", "Смола для настоек", "pine_resin", 12, {"forest_moss": 8, "blueprint_potion_antibleed_2": 1}),
            ]),
            ("torin_hunt", "Торин", "🏹", "hunting", [
                ("fb_wolf_pelt", "Шкуры волков", "wolf_pelt", 20, {"owl_feather": 10}),
                ("fb_feather_lure", "Перья для приманки", "owl_feather", 18, {"wolf_pelt": 8}),
            ]),
        ],
        "mats": {
            "forest_moss": ("Мох леса", "common", "alchemy"),
            "pine_resin": ("Смола сосны", "common", "alchemy"),
            "wolf_pelt": ("Шкура волка", "uncommon", "hunting"),
            "owl_feather": ("Перо совы", "common", "hunting"),
        },
    },
    {
        "key": "rotten_swamps",
        "name": "Гнилые Болота",
        "emoji": "🌿",
        "from": 11,
        "to": 20,
        "hub": 15,
        "theme": "swamp",
        "npcs": [
            ("mire_witch", "Болотница", "🧪", "alchemy", [
                ("sw_mire_slime", "Слизь болота", "swamp_slime", 14, {"leech_sac": 5}),
                ("sw_toxin_vial", "Сосуды яда", "toxin_vial", 10, {"swamp_slime": 6, "blueprint_potion_bloodshield_3": 1}),
            ]),
            ("reed_trapper", "Кузьма", "🪤", "hunting", [
                ("sw_leech_sack", "Мешок пиявок", "leech_sac", 25, {"bog_fang": 4}),
                ("sw_bog_fang", "Клыки болотника", "bog_fang", 12, {"toxin_vial": 5}),
            ]),
        ],
        "mats": {
            "swamp_slime": ("Болотная слизь", "common", "alchemy"),
            "toxin_vial": ("Сосуд яда", "uncommon", "alchemy"),
            "leech_sac": ("Мешок пиявок", "common", "hunting"),
            "bog_fang": ("Клык болотника", "rare", "hunting"),
        },
    },
    {
        "key": "shadow_caves",
        "name": "Пещеры Теней",
        "emoji": "🕳️",
        "from": 21,
        "to": 30,
        "hub": 25,
        "theme": "shadow",
        "npcs": [
            ("shade_scribe", "Писарь тени", "📜", "jewelry", [
                ("sc_void_dust", "Пыль бездны", "void_dust", 16, {"bone_setting": 8}),
                ("sc_bone_set", "Костяные оправы", "bone_setting", 10, {"void_dust": 6, "blueprint_ring_crimson_2": 1}),
            ]),
            ("umbra_smith", "Умбра", "🔨", "smithing", [
                ("sc_dark_ingot", "Слитки тёмного металла", "dark_steel", 14, {"chain_fragment": 8}),
                ("sc_chain_bits", "Осколки цепей", "chain_fragment", 22, {"dark_steel": 10, "blueprint_armor_patch_dark_1": 1}),
            ]),
        ],
        "mats": {
            "void_dust": ("Пыль бездны", "uncommon", "jewelry"),
            "bone_setting": ("Костяная оправа", "common", "jewelry"),
            "dark_steel": ("Тёмная сталь", "uncommon", "smithing"),
            "chain_fragment": ("Осколок цепи", "common", "smithing"),
        },
    },
    {
        "key": "icy_peaks",
        "name": "Ледяные Пики",
        "emoji": "❄️",
        "from": 31,
        "to": 40,
        "hub": 35,
        "theme": "ice",
        "npcs": [
            ("frost_smith", "Хельга", "🔨", "smithing", [
                ("ip_ice_shard", "Осколки льда", "ice_shard", 20, {"beast_fur": 8}),
                ("ip_fur_lining", "Мех для доспехов", "beast_fur", 15, {"ice_shard": 12, "blueprint_armor_patch_dark_1": 1}),
            ]),
            ("peak_ranger", "Сигур", "🏹", "hunting", [
                ("ip_yeti_claw", "Когти йети", "yeti_claw", 12, {"frost_feather": 10}),
                ("ip_frost_feather", "Ледяные перья", "frost_feather", 18, {"yeti_claw": 6}),
            ]),
        ],
        "mats": {
            "ice_shard": ("Осколок льда", "common", "smithing"),
            "beast_fur": ("Звериный мех", "uncommon", "smithing"),
            "yeti_claw": ("Коготь йети", "rare", "hunting"),
            "frost_feather": ("Ледяное перо", "common", "hunting"),
        },
    },
    {
        "key": "desert_oblivion",
        "name": "Пустыня Забвения",
        "emoji": "🏜️",
        "from": 41,
        "to": 50,
        "hub": 45,
        "theme": "desert",
        "npcs": [
            ("nomad_alch", "Зафир", "⚗️", "alchemy", [
                ("do_sand_glass", "Песчаные реагенты", "sand_glass", 18, {"sun_herb": 6}),
                ("do_sun_herb", "Солнечные травы", "sun_herb", 14, {"sand_glass": 10, "blueprint_potion_antibleed_2": 1}),
            ]),
            ("dune_jewel", "Лейла", "💎", "jewelry", [
                ("do_amber_chip", "Янтарные осколки", "amber_chip", 10, {"scarab_shell": 5}),
                ("do_scarab_shell", "Панцири скарабеев", "scarab_shell", 16, {"amber_chip": 4}),
            ]),
        ],
        "mats": {
            "sand_glass": ("Песчаный реагент", "common", "alchemy"),
            "sun_herb": ("Солнечная трава", "uncommon", "alchemy"),
            "amber_chip": ("Янтарь", "rare", "jewelry"),
            "scarab_shell": ("Панцирь скарабея", "common", "jewelry"),
        },
    },
    {
        "key": "volcanic_ruins",
        "name": "Вулканические Руины",
        "emoji": "🌋",
        "from": 51,
        "to": 60,
        "hub": 55,
        "theme": "volcano",
        "npcs": [
            ("ember_forge", "Бранн", "🔨", "smithing", [
                ("vr_obsidian", "Обсидиан", "obsidian_shard", 16, {"slag_brick": 10}),
                ("vr_slag_brick", "Шлаковый кирпич", "slag_brick", 20, {"obsidian_shard": 12}),
            ]),
            ("ash_alchemist", "Пепель", "⚗️", "alchemy", [
                ("vr_ember_salt", "Соль пепла", "ember_salt", 14, {"magma_resin": 5}),
                ("vr_magma_resin", "Смола магмы", "magma_resin", 12, {"ember_salt": 8, "blueprint_potion_bloodshield_3": 1}),
            ]),
        ],
        "mats": {
            "obsidian_shard": ("Обсидиан", "uncommon", "smithing"),
            "slag_brick": ("Шлак", "common", "smithing"),
            "ember_salt": ("Соль пепла", "common", "alchemy"),
            "magma_resin": ("Смола магмы", "rare", "alchemy"),
        },
    },
    {
        "key": "chaos_abyss",
        "name": "Бездна Хаоса",
        "emoji": "🌀",
        "from": 71,
        "to": 80,
        "hub": 75,
        "theme": "chaos",
        "npcs": [
            ("chaos_sage", "Оракул разлома", "📜", "jewelry", [
                ("ca_rift_shard", "Осколки разлома", "rift_shard", 12, {"void_ink": 5}),
                ("ca_void_ink", "Чернила пустоты", "void_ink", 15, {"rift_shard": 6, "blueprint_ring_crimson_2": 1}),
            ]),
            ("demon_hunter", "Каз", "🏹", "hunting", [
                ("ca_demon_horn", "Рога демонов", "demon_horn", 10, {"chaos_hide": 6}),
                ("ca_chaos_hide", "Шкуры хаоса", "chaos_hide", 18, {"demon_horn": 8}),
            ]),
        ],
        "mats": {
            "rift_shard": ("Осколок разлома", "epic", "jewelry"),
            "void_ink": ("Чернила пустоты", "rare", "jewelry"),
            "demon_horn": ("Рог демона", "rare", "hunting"),
            "chaos_hide": ("Шкура хаоса", "uncommon", "hunting"),
        },
    },
    {
        "key": "eternity_hall",
        "name": "Зал Вечности",
        "emoji": "⚡",
        "from": 81,
        "to": 99,
        "hub": 90,
        "theme": "eternity",
        "npcs": [
            ("archivist", "Архивариус", "📚", "jewelry", [
                ("eh_star_dust", "Звёздная пыль", "star_dust", 10, {"light_chain": 8}),
                ("eh_eternal_gem", "Вечные кристаллы", "eternal_gem", 6, {"star_dust": 6, "blueprint_ring_crimson_2": 1}),
            ]),
            ("void_knight", "Сераф", "⚔️", "smithing", [
                ("eh_void_plate", "Листы пустоты", "void_plate", 14, {"light_chain": 10}),
                ("eh_light_chain", "Светлые звенья", "light_chain", 20, {"void_plate": 8}),
            ]),
        ],
        "mats": {
            "star_dust": ("Звёздная пыль", "epic", "jewelry"),
            "eternal_gem": ("Вечный кристалл", "legendary", "jewelry"),
            "void_plate": ("Лист пустоты", "epic", "smithing"),
            "light_chain": ("Светлое звено", "rare", "smithing"),
        },
    },
]


def _quest_row(qid: str, title: str, mat: str, qty: int, rewards: dict) -> dict:
    mats = [{"id": k, "qty": v} for k, v in rewards.items() if v > 0 and not k.startswith("blueprint_")]
    bps = [{"id": k.replace("blueprint_", ""), "qty": v} for k, v in rewards.items() if k.startswith("blueprint_") and v > 0]
    row: dict = {
        "id": qid,
        "title": title,
        "objective": "collect_material",
        "target": {"id": mat, "qty": qty},
        "rewards": {},
    }
    if mats:
        row["rewards"]["materials"] = mats
    if bps:
        row["rewards"]["blueprints"] = bps
    return row


def _write_zone(spec: dict) -> None:
    key = spec["key"]
    if key == "blood_spire":
        return
    zdir = PACKS / key
    zdir.mkdir(parents=True, exist_ok=True)
    fr, to = spec["from"], spec["to"]
    hub = spec["hub"]
    zone = {
        "key": key,
        "name": spec["name"],
        "emoji": spec["emoji"],
        "floor_from": fr,
        "floor_to": to,
        "description": f"Мастера зоны {spec['name']} — поручения и материалы для мастерской.",
        "floor_type": "normal",
        "theme": spec["theme"],
        "hub_floor": hub,
    }
    (zdir / "zone.json").write_text(json.dumps(zone, ensure_ascii=False, indent=2), encoding="utf-8")
    entries = []
    for npc_id, name, emoji, prof, quests in spec["npcs"]:
        qrows = []
        for i, (qid, title, mat, qty, rew) in enumerate(quests):
            floors = [fr + i * 2, min(to, fr + i * 2 + 1)]
            q = _quest_row(f"{npc_id}_{qid}", title, mat, qty, rew)
            q["floors"] = sorted(set(floors))
            if i == 1:
                q["profession_tier_min"] = 2
            qrows.append(q)
        entries.append({
            "id": npc_id,
            "name": name,
            "emoji": emoji,
            "profession": prof,
            "floor_from": fr,
            "floor_to": to,
            "floors_hub": [hub],
            "greeting_by_reputation": {
                "neutral": f"{{player_name}}, {name} ждёт материалы.",
                "honored": f"{{player_name}}, твои поставки не забыты.",
            },
            "quests": qrows,
        })
    (zdir / "npcs.json").write_text(
        json.dumps({"entries": entries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    mat_entries = {
        mid: {"name_ru": n, "rarity": r, "profession": p, "tags": [spec["theme"]]}
        for mid, (n, r, p) in spec["mats"].items()
    }
    (zdir / "materials.json").write_text(
        json.dumps({"entries": mat_entries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (zdir / "blueprints.json").write_text(
        json.dumps({"entries": {}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # monsters.json не создаём пустым — иначе затирает пул в monsters_catalog при merge


def main() -> None:
    for spec in ZONE_SPECS:
        _write_zone(spec)
    reg_path = ROOT / "content" / "data" / "packs" / "registry.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    zones = sorted({s["key"] for s in ZONE_SPECS} | {"blood_spire"})
    reg["zones"] = zones
    reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK zones:", ", ".join(zones))


if __name__ == "__main__":
    main()
