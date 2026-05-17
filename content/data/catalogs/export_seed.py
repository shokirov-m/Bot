"""Запуск: python -m game.data.catalogs.export_seed — заполняет JSON из текущего кода."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent


def w(name: str, data: dict) -> None:
    path = OUT / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("wrote", path.name, path.stat().st_size)


def main() -> None:
    from game.enemies.coliseum import fighters as cd
    from game.enemies.coliseum import rewards as cr
    from game.tower.progression import floor_data
    from game.locations import cities as loc_cities
    from game.locations import tavern as loc_tavern
    from game.archetypes import data as ad
    from game.archetypes import trees as tr
    from game.tower.progression.wandering_npcs import wn
    from game.tower.quests import npc_quests as nq

    fighters = [
        {
            "id": f.id,
            "name": f.name,
            "phrase": f.phrase,
            "victory_quote": f.victory_quote,
            "hp": f.hp,
            "atk": f.atk,
            "defense": f.defense,
            "exp_reward": f.exp_reward,
            "gold_reward": f.gold_reward,
            "required_level": f.required_level,
            "element_tz": f.element_tz,
            "is_champion": f.is_champion,
            "special": f.special,
            "loot_id": f.loot_id,
            "portrait": f"coliseum/fighters/{f.id}.png",
        }
        for f in cd.COLISEUM_FIGHTERS
    ]
    loot = {str(k): (dict(v) if isinstance(v, dict) else str(v)) for k, v in cr.COLISEUM_LOOT.items()}
    w(
        "coliseum_fighters.json",
        {
            "_readme": "Бойцы колизея 1–50.",
            "version": 1,
            "template_key": cd.COLISEUM_TEMPLATE_KEY,
            "enemy_atk_mult": cd.COLISEUM_ENEMY_ATK_MULT,
            "element_map": dict(cd.ELEMENT_TO_ENGINE),
            "fighters": fighters,
            "loot": loot,
        },
    )

    hubs = []
    for fl, hub in loc_cities._CITY_HUBS.items():
        ci = floor_data.get_city_for_floor(int(fl))
        hubs.append(
            {
                "floor": int(fl),
                "key": hub.key,
                "name": ci.name if ci else hub.key,
                "emoji": ci.emoji if ci else "🏘️",
                "theme_ru": ci.theme_ru if ci else "",
                "tagline": hub.tagline,
                "welcome_html": hub.welcome_html,
                "retention_note": hub.retention_note,
                "npc_guard_title": hub.npc_guard_title,
                "economy_blurb": hub.economy_blurb,
                "tavern_extras": [
                    {
                        "key": o.key,
                        "name": o.name,
                        "emoji": o.emoji,
                        "price": o.price,
                        "blurb": o.blurb,
                    }
                    for o in loc_tavern.TAVERN_EXTRAS_BY_CITY.get(int(fl), ())
                ],
                "art": {"hub_menu": "menus/city.png"},
            },
        )
    w(
        "cities_hubs.json",
        {
            "_readme": "Города-хабы.",
            "version": 1,
            "hub_key_by_floor": {str(k): v for k, v in loc_cities.HUB_KEY_BY_FLOOR.items()},
            "hubs": hubs,
            "all_city_floors": [
                {
                    "floor": int(fl),
                    "name": ci.name,
                    "emoji": ci.emoji,
                    "theme_ru": ci.theme_ru,
                    "hub_key": loc_cities.HUB_KEY_BY_FLOOR.get(int(fl)),
                }
                for fl, ci in sorted(floor_data.CITIES.items())
            ],
        },
    )

    w("archetypes_skills.json", {
        "version": 1,
        "entries": {
            k: {
                "name_ru": s.name_ru,
                "description_ru": s.description_ru,
                "mp_cost": s.mp_cost,
                "cooldown": s.cooldown,
                "power_mult": s.power_mult,
                "kind": s.kind,
                "effect_key": s.effect_key,
                "effect_chance": s.effect_chance,
                "required_level": s.required_level,
            }
            for k, s in ad.SKILLS.items()
        },
    })
    w("archetypes_passives.json", {
        "version": 1,
        "entries": {
            k: {"name_ru": p.name_ru, "description_ru": p.description_ru, "modifiers": dict(p.modifiers)}
            for k, p in ad.PASSIVES.items()
        },
    })
    w("archetypes_classes.json", {
        "version": 1,
        "entries": {
            k: {
                "name_ru": a.name_ru,
                "emoji": a.emoji,
                "tier": a.tier,
                "description_ru": a.description_ru,
                "base_stats": dict(a.base_stats),
                "skills": list(a.skills),
                "passives": [p.key for p in a.passives],
                "hp_multiplier": a.hp_multiplier,
                "mp_multiplier": a.mp_multiplier,
                "requirements": dict(a.requirements),
            }
            for k, a in ad.ARCHETYPES.items()
        },
    })
    trees_out: dict = {}
    for arch, nodes in tr.TREES.items():
        trees_out[arch] = {}
        for nk, n in nodes.items():
            val = dict(n.value) if isinstance(n.value, dict) else str(n.value)
            trees_out[arch][nk] = {
                "name_ru": n.name_ru,
                "description_ru": n.description_ru,
                "node_type": n.node_type,
                "value": val,
                "cost_sp": n.cost_sp,
                "parent_keys": list(n.parent_keys),
                "required_tier": n.required_tier,
            }
    w("archetypes_skill_trees.json", {"version": 1, "trees": trees_out})

    w(
        "npcs_index.json",
        {
            "version": 1,
            "wandering_roll_threshold": wn.WANDERING_NPC_ROLL_THRESHOLD,
            "wanderers": [{"index": i, **dict(row)} for i, row in enumerate(wn._POOL)],
            "zone_quest_givers": {k: {"name": v[0], "emoji": v[1]} for k, v in nq._ZONE_NPC.items()},
        },
    )
    qr = []
    pool = nq.quest_pool()
    for fl, templates in sorted(pool.items()):
        for t in templates:
            qr.append(
                {
                    "key": t.key,
                    "floor": t.floor,
                    "npc_name": t.npc_name,
                    "npc_emoji": t.npc_emoji,
                    "title": t.title,
                    "description": t.description,
                    "quest_type": t.quest_type,
                    "target_key": t.target_key,
                    "target_count": t.target_count,
                    "reward_gold": t.reward_gold,
                    "reward_exp": t.reward_exp,
                    "reward_item_chance": t.reward_item_chance,
                    "reward_rune_chance": t.reward_rune_chance,
                },
            )
    w(
        "quests_registry.json",
        {
            "_readme": "Квесты NPC на этажах ×3. Логика выдачи — game/quests/npc_quests.py.",
            "version": 1,
            "floor_x3_npc_quests": qr,
        },
    )


if __name__ == "__main__":
    main()
