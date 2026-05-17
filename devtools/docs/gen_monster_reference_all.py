from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from game.tower.progression import floor_data
from game.enemies.appearances_ru import APPEARANCE_RU
from game.data.monsters import MONSTER_TEMPLATE_META, ZONE_POOL_KEYS

# Как в game/enemies/floors/spawns.py — мини-босс зоны
_MINI_BOSS_KEY: dict[str, str] = {
    "forest_beginnings": "mini_alpha_wolf",
    "rotten_swamps": "mini_bog_queen",
    "shadow_caves": "mini_shadow_weaver",
    "icy_peaks": "mini_frost_troll",
    "desert_oblivion": "mini_sand_titan",
    "volcanic_ruins": "mini_magma_lord",
    "sky_citadel": "mini_storm_herald",
    "chaos_abyss": "mini_chaos_knight",
    "eternity_hall": "mini_time_judge",
    floor_data.ZONE_FINAL_KEY: "tower_warden",
}

# Сильный босс каждого 10-го этажа (кроме финала 135+ — отдельно)
_MAJOR_BOSS_KEY: dict[str, str] = {
    "forest_beginnings": "boss_ancient_treant",
    "rotten_swamps": "boss_slime_king",
    "shadow_caves": "boss_night_stalker",
    "icy_peaks": "boss_glacier_king",
    "desert_oblivion": "boss_time_scarab",
    "volcanic_ruins": "boss_ember_dragon",
    "sky_citadel": "boss_sky_tyrant",
    "chaos_abyss": "boss_chaos_avatar",
    "eternity_hall": "boss_eternity_judge",
    "jade_labyrinth": "boss_eternity_judge",
    "frozen_wastes": "boss_chaos_avatar",
    "faction_war_plains": "boss_eternity_judge",
}


def _meta(key: str) -> dict:
    return dict(MONSTER_TEMPLATE_META.get(key) or {})


def _display_title(key: str) -> str:
    m = _meta(key)
    name = str(m.get("display_name") or key).strip()
    emoji = str(m.get("emoji") or "").strip()
    return f"{emoji} {name}".strip() if emoji else name


def _appearance(key: str) -> str:
    if key in APPEARANCE_RU:
        return APPEARANCE_RU[key]
    m = _meta(key)
    name = str(m.get("display_name") or key)
    el = str(m.get("element") or "")
    return (
        f"Внешность для «{name}» (стихия {el}) — задать художнику: силуэт, материал тела, палитра; без акцента на боевые приёмы."
    )


def _monster_block(key: str, *, role: str = "") -> list[str]:
    role_bit = f" — *{role}*" if role else ""
    lines = [
        f"#### `{key}`{role_bit}",
        "",
        f"- **Имя:** {_display_title(key)}",
        f"- **Внешность:** {_appearance(key)}",
        f"- **Картинка:** `assets/game_art/monsters/{key}.png`",
        "",
    ]
    return lines


def main() -> int:
    out: list[str] = []
    out.append("## Справочник монстров по локациям")
    out.append("")
    out.append(
        "Описания **внешности** — отдельно от боевых подсказок в игре (`blurb`). "
        "Источник ключей: `ZONE_POOL_KEYS`, боссы — как в `game/enemies/floors/spawns.py`."
    )
    out.append("")
    out.append("- Картинка: `assets/game_art/monsters/<ключ>.png`")
    out.append("- Элита `elite_<ключ>` — тот же арт, что у `<ключ>`.")
    out.append("")

    # Основные 10 зон (этажи 1–99)
    for zone in floor_data.ZONES:
        if zone.key in ("jade_labyrinth", "frozen_wastes", "faction_war_plains"):
            continue
        out.append(f"## {zone.emoji} {zone.name}")
        out.append("")
        out.append(f"*Этажи {zone.floor_from}–{zone.floor_to}*")
        out.append("")

        pool = list(ZONE_POOL_KEYS.get(zone.key, []))
        if pool:
            out.append("### Обычный пул")
            out.append("")
            for key in pool:
                out.extend(_monster_block(key))
        else:
            out.append("*Нет записи в `ZONE_POOL_KEYS` — см. особые сценарии этажей.*")
            out.append("")

        mk = _MINI_BOSS_KEY.get(zone.key)
        if mk and mk not in pool:
            out.append("### Мини-босс зоны")
            out.append("")
            out.extend(_monster_block(mk, role="мини-босс"))

        bk = _MAJOR_BOSS_KEY.get(zone.key)
        if bk:
            out.append("### Сильный босс (каждый 10-й этаж в зоне)")
            out.append("")
            out.extend(_monster_block(bk, role="босс"))

    # Зоны 101+ без общего пула в ZONE_POOL_KEYS
    out.append("## Дополнительные зоны башни")
    out.append("")
    for zone in floor_data.ZONES:
        if zone.key not in ("jade_labyrinth", "frozen_wastes", "faction_war_plains"):
            continue
        out.append(f"### {zone.emoji} {zone.name} (этажи {zone.floor_from}–{zone.floor_to})")
        out.append("")
        out.append(
            "*Обычные цели на этих этажах задаются отдельными сценариями; здесь — сильный босс десятка по правилам зоны.*"
        )
        out.append("")
        bk = _MAJOR_BOSS_KEY.get(zone.key)
        if bk:
            out.extend(_monster_block(bk, role="босс"))
        out.append("")

    # Финал башни
    zf = floor_data.ZONE_FINAL
    out.append(f"## {zf.emoji} {zf.name} (финал)")
    out.append("")
    out.append(f"*Этаж {zf.floor_from}+*")
    out.append("")
    pool = ZONE_POOL_KEYS.get(zf.key, [])
    if pool:
        out.append("### Пул шаблонов")
        out.append("")
        for key in pool:
            out.extend(_monster_block(key))
    mk = _MINI_BOSS_KEY.get(zf.key)
    if mk and mk not in pool:
        out.append("### Мини-босс (ключ зоны)")
        out.append("")
        out.extend(_monster_block(mk, role="мини-босс"))
    out.append("### Страж ядра (этаж 135+)")
    out.append("")
    out.extend(_monster_block("boss_tower_core", role="финальный босс"))

    # Длинный этаж — лабиринт
    out.append("## Особый этаж: длинный лабиринт")
    out.append("")
    out.append("*`game/tower/mechanics/long_floor.py` — цепочка целей.*")
    out.append("")
    for key in ("lf_swarm", "lf_guardian", "lf_bog_lord"):
        out.extend(_monster_block(key))

    # Событие
    out.append("## Мировое событие")
    out.append("")
    out.extend(_monster_block("golden_goblin"))

    out_path = ROOT / "docs" / "monster_reference.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
