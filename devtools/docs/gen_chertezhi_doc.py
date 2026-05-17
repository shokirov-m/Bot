#!/usr/bin/env python3
"""docs/novye_chertezhi_45.txt из recipes_data + RESOURCE_DEFS."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.crafting.recipes_data import RECIPES
from game.items.craft_resources import RESOURCE_DEFS

ADDED = {
    "bp_sk_chain_hauberk",
    "bp_sk_iron_gladius",
    "bp_sk_silver_kite",
    "bp_sk_dark_longsword",
    "bp_sk_dragon_gorget",
    "bp_sk_obsidian_greaves",
    "bp_sk_skysteel_spear",
    "bp_sk_adamant_helm",
    "bp_sk_titan_greataxe",
    "bp_sk_mithril_fullplate",
    "bp_sk_flame_core_blade",
    "bp_sk_storm_breaker",
    "bp_sk_void_edge",
    "bp_sk_warden_gauntlets",
    "bp_sk_starfall_blade",
    "bp_al_healing_draught",
    "bp_al_mana_star",
    "bp_al_mandrake_tonic",
    "bp_al_golem_elixir",
    "bp_al_moon_veil",
    "bp_al_phoenix_breath",
    "bp_al_void_philter",
    "bp_al_basilisk_brew",
    "bp_al_starlight_serum",
    "bp_al_golden_dawn",
    "bp_al_nether_sips",
    "bp_al_abyss_ink",
    "bp_al_sun_tears",
    "bp_al_witch_honey",
    "bp_al_oracle_tea",
    "bp_jw_pearl_ring",
    "bp_jw_tiger_amulet",
    "bp_jw_moon_band",
    "bp_jw_ruby_signet",
    "bp_jw_storm_pendant",
    "bp_jw_life_circle",
    "bp_jw_black_opal_orb",
    "bp_jw_void_diadem",
    "bp_jw_cyclops_band",
    "bp_jw_starheart_locket",
    "bp_jw_amber_weave",
    "bp_jw_crimson_loop",
    "bp_jw_emerald_gaze",
    "bp_jw_copper_coronet",
    "bp_jw_opal_chain",
}


def mat_line(cc: dict[str, int]) -> str:
    if not cc:
        return "—"
    parts: list[str] = []
    for k in sorted(cc.keys()):
        d = RESOURCE_DEFS.get(k) or {}
        label = str(d.get("name_ru") or k)
        parts.append(f"{label} (id: {k}) ×{int(cc[k])}")
    return "; ".join(parts)


def effect_lines(res: dict) -> list[str]:
    lines: list[str] = []
    lines.append(f"тип предмета: {res.get('kind')}")
    lines.append(f"редкость результата: {res.get('rarity', '')}")
    if res.get("attack") is not None:
        lines.append(f"атака: {res.get('attack')}")
    if res.get("defense") is not None:
        lines.append(f"защита: {res.get('defense')}")
    for stat in ("str", "dex", "int", "vit"):
        if res.get(stat) is not None:
            lines.append(f"{stat}: {res.get(stat)}")
    ut = res.get("use_tag")
    if ut:
        lines.append(f"тег использования: {ut}")
        if res.get("use_value") is not None:
            lines.append(f"значение эффекта: {res.get('use_value')}")
    if str(ut or "") == "workshop_alchemy_enchant":
        p = res.get("add_fire_resist_pct")
        if p:
            lines.append(
                f"зачарование брони (алхимия): +{p}% огненный резист, метка: {res.get('enchant_label_ru', '')}"
            )
    lines.append(f"кратко (summary): {res.get('summary', '')}")
    return lines


def main() -> None:
    by_prof: dict[str, list] = {"blacksmith": [], "alchemist": [], "jeweler": []}
    for r in RECIPES:
        rid = str(r.get("id", ""))
        if rid not in ADDED:
            continue
        prof = str(r.get("profession", ""))
        by_prof.setdefault(prof, []).append(r)

    out: list[str] = []
    out.append("НОВЫЕ ЧЕРТЕЖИ (45) — материалы и эффекты результатов")
    out.append("Источник: game/crafting/recipes_data.py, имена материалов — craft_resources.RESOURCE_DEFS")
    out.append("")
    out.append("Примечание: при сборе крафта кузнеца на предмет накладывается звёздное качество (forge_stars);")
    out.append("алхимик и ювелир получают предмет как в таблице ниже (без доп. рандома качества).")
    out.append("")

    sections = [
        ("КУЗНЕЦ — 15 чертежей", "blacksmith"),
        ("АЛХИМИК — 15 чертежей", "alchemist"),
        ("ЮВЕЛИР — 15 чертежей", "jeweler"),
    ]
    for sec_title, pkey in sections:
        out.append("=" * 72)
        out.append(sec_title)
        out.append("=" * 72)
        for r in sorted(by_prof.get(pkey, []), key=lambda x: str(x.get("id"))):
            res = dict(r.get("result") or {})
            out.append("")
            out.append(f"ID: {r.get('id')}")
            nm = str(r.get("name_ru") or "")
            if nm.startswith("Чертёж: "):
                nm = nm[len("Чертёж: ") :]
            out.append(f"Название чертежа: {nm}")
            out.append(f"Описание: {r.get('description')}")
            out.append(
                f"Требования: уровень профессии {r.get('min_profession_level')}+, "
                f"станок {r.get('min_station_level')}+, герой {r.get('min_character_level')}+"
            )
            out.append(
                f"Время: {r.get('craft_seconds')} с | опыт при сборе: {r.get('xp_reward')}"
            )
            out.append("Материалы (craft_cost):")
            out.append("  " + mat_line(dict(r.get("craft_cost") or {})))
            out.append(f"Результат: {res.get('name')}")
            for line in effect_lines(res):
                out.append("  • " + line)
            out.append("-" * 56)
        out.append("")

    out.append("")
    out.append("=" * 72)
    out.append("См. также: docs/professii_audit.txt — проверка профессий и мастерской.")
    out.append("=" * 72)

    dest = ROOT / "docs" / "novye_chertezhi_45.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {dest} ({len(out)} lines)")


if __name__ == "__main__":
    main()
