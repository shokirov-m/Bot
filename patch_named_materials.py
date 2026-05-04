#!/usr/bin/env python3
"""Только замена cost/craft_cost на именованные материалы. Не трогает хвост файла."""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REC = ROOT / "game" / "crafting" / "recipes_data.py"

CRAFT_BY_ID = {
    "salve_basic": {"meadow_herb": 6, "moss_fungus": 2},
    "ring_siphon": {"copper_dust": 5, "tiger_eye": 3},
    "iron_charm_loop": {"copper_dust": 4, "river_pearl": 2},
    "weak_blade_blank": {"copper_ingot": 5, "iron_ingot": 3},
    "mana_drop_flask": {"meadow_herb": 3, "blue_berry": 2},
    "bp_tower_flame_blade": {"hardened_steel": 2, "mithril_ingot": 2, "dragon_bone": 1, "obsidian": 1},
    "gem_socket_amulet": {"moonstone": 3, "amber": 3, "tiger_eye": 2},
    "grand_elixir": {"mandrake_root": 4, "spirit_pollen": 2, "void_rose_thorn": 1},
    "jeweler_rune_fire_3": {"tiger_eye": 4, "amber": 2},
    "jeweler_rune_fire_4": {"blood_ruby": 2, "storm_sapphire": 2, "life_emerald": 1},
    "jeweler_rune_fire_5": {"black_opal": 2, "void_diamond": 1, "cyclops_eye": 1},
    "alchemy_scroll_fire_shell_i": {"meadow_herb": 4, "moss_fungus": 2},
    "alchemy_scroll_fire_shell_ii": {"blue_berry": 3, "mandrake_root": 2},
    "alchemy_scroll_fire_shell_iii": {"void_rose_thorn": 2, "golem_tear": 2, "basilisk_scale": 1},
    "alchemy_scroll_flame_edge_i": {"meadow_herb": 3, "spirit_pollen": 2},
    "alchemy_scroll_flame_edge_ii": {"mandrake_root": 3, "blue_berry": 2},
    "alchemy_scroll_flame_edge_iii": {"moon_dust": 2, "phoenix_flower": 1, "basilisk_scale": 1},
    "alchemy_sigil_ring_t1": {"mandrake_root": 4, "spirit_pollen": 2, "void_rose_thorn": 1},
    "alchemy_sigil_ring_t2": {"phoenix_flower": 2, "moon_dust": 2, "void_essence": 1},
    "alchemy_sigil_ring_t3": {"golden_apple": 1, "void_essence": 2, "phoenix_flower": 1},
    "legend_blade_forge": {"adamantite": 2, "titan_blood": 1, "skysteel": 2},
    "smith_steel_cuirass": {"steel_ingot": 5, "iron_ingot": 4},
    "smith_bronze_greaves": {"copper_ingot": 6, "iron_ingot": 4},
    "smith_silver_gauntlets": {"silver_ingot": 4, "hardened_steel": 2},
    "smith_mithril_helm": {"mithril_ingot": 3, "dark_steel": 2, "dragon_bone": 1},
    "bp_adamant_bracers": {"adamantite": 2, "titan_blood": 1, "obsidian": 2},
    "jeweler_quartz_band": {"copper_dust": 4, "tiger_eye": 2},
    "jeweler_sapphire_loop": {"storm_sapphire": 3, "moonstone": 2},
    "jeweler_ruby_pendant": {"blood_ruby": 3, "life_emerald": 2},
    "bp_void_wedding_band": {"star_heart": 1, "void_diamond": 2},
    "alchemy_swift_tonic": {"meadow_herb": 5, "moss_fungus": 2},
    "alchemy_arcane_philter": {"blue_berry": 4, "mandrake_root": 2, "spirit_pollen": 1},
    "alchemy_dragon_serum": {"moon_dust": 3, "phoenix_flower": 2, "void_essence": 1},
    "bp_alchemy_sun_elixir": {"golden_apple": 1, "phoenix_flower": 2, "void_essence": 1},
}


def fmt(d: dict) -> str:
    return "{" + ", ".join(f'"{k}": {v}' for k, v in sorted(d.items())) + "}"


def ph(header: str, craft: dict) -> str:
    h = re.sub(r'"cost":\s*\{[^}]+\}\s*,', '"cost": {},', header)
    h = re.sub(r'"craft_cost":\s*\{[^}]+\}\s*,', "", h)
    ins = f'"cost": {{}},\n            "craft_cost": {fmt(craft)},'
    return h.replace('"cost": {},', ins, 1)


def pr(text: str, rid: str, craft: dict) -> str:
    i0 = text.index(f'"id": "{rid}"')
    fi = text.index('"forge_instant":', i0)
    return text[:i0] + ph(text[i0:fi], craft) + text[fi:]


def main() -> None:
    t = REC.read_text(encoding="utf-8")
    for rid, c in CRAFT_BY_ID.items():
        t = pr(t, rid, c)
    REC.write_text(t, encoding="utf-8")
    print("patched", len(CRAFT_BY_ID), "recipes")


if __name__ == "__main__":
    main()
