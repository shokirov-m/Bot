"""One-off: dump monster HP/ATK/DEF for floors 1-20. Run: python tools/_dump_floors_1_20_stats.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.floors.long_floor import all_long_floor_spawns
from game.floors.monsters import build_spawns_for_floor
from services.combat_service import _monster_stat_bundle

EL_RU = {
    "earth": "земля",
    "fire": "огонь",
    "ice": "лёд",
    "lightning": "молния",
    "dark": "тьма",
    "light": "свет",
    "poison": "яд",
}


def label(spawn) -> str:
    if spawn.is_major_boss:
        return "сильный босс"
    if spawn.is_mini_boss:
        return "мини-босс"
    if spawn.is_elite:
        return "элита"
    return "обычный"


def main() -> None:
    # Сырой дамп — не затирает справочник МОНСТРЫ_И_БОССЫ_1-20_СТАТЫ.txt (там вручную шапка).
    out_path = ROOT.parent / "МОНСТРЫ_И_БОССЫ_1-20_СТАТЫ_RAW.txt"
    lines: list[str] = []
    for fl in range(1, 21):
        if fl == 3:
            lines.append(f"=== {fl} === МИРНЫЙ ГОРОД (Тихий Ручей), целей на карте нет\n")
            continue
        spawns = build_spawns_for_floor(fl)
        lines.append(f"=== ЭТАЖ {fl} ===")
        for s in spawns:
            b = _monster_stat_bundle(fl, s)
            ap = b.get("armor_penetration")
            extra = ""
            if ap:
                extra = f" | игнор брони монстром ~{int(float(ap) * 100)}%"
            if b.get("applies_poison_on_hit"):
                extra += " | накладывает яд ударами"
            el = EL_RU.get(str(b["element"]), str(b["element"]))
            lines.append(
                f"  [{label(s):14}] {b['emoji']} {b['name']:<22} "
                f"жизни {b['hp']:>5}  удар {b['atk']:>4}  защита {b['defense']:>4}  стихия: {el}{extra}",
            )
        if fl == 15:
            lines.append("  --- Длинный сценарий 15-го (пока не пройден — на карте эти три цели): ---")
            for s in all_long_floor_spawns():
                b = _monster_stat_bundle(fl, s)
                el = EL_RU.get(str(b["element"]), str(b["element"]))
                lines.append(
                    f"  [{label(s):14}] {b['emoji']} {b['name']:<22} "
                    f"жизни {b['hp']:>5}  удар {b['atk']:>4}  защита {b['defense']:>4}  стихия: {el}",
                )
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
