from __future__ import annotations

from pathlib import Path


def _safe(s: str) -> str:
    return (s or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def main() -> int:
    from game.floors import floor_data
    from game.floors.monsters import build_spawns_for_floor

    lines: list[str] = []
    lines.append("## Справочник монстров этажей 21–40")
    lines.append("")
    lines.append(
        "Источник: `game/floors/monsters.py` (выбор врагов по зонам) + `game/data/monsters` (карточки шаблонов)."
    )
    lines.append("")
    lines.append("Рекомендуемое имя файла картинки для монстра:")
    lines.append("- `assets/game_art/monsters/<template_key>.png`")
    lines.append("- Для элиты `elite_<key>` можно использовать тот же арт, что и для `<key>`.")
    lines.append("")

    for fl in range(21, 41):
        zone = floor_data.get_zone_for_floor(fl)
        spawns = build_spawns_for_floor(fl)

        seen: set[str] = set()
        uniq: list[tuple[str, object]] = []
        for s in spawns:
            k = str(getattr(getattr(s, "template", None), "key", "") or "")
            base = k[6:] if k.startswith("elite_") else k
            if not base or base in seen:
                continue
            seen.add(base)
            uniq.append((base, s))

        lines.append(f"### Этаж {fl} — {zone.emoji} {zone.name}")
        lines.append("")
        for base, s in uniq:
            tpl = s.template
            art = f"assets/game_art/monsters/{base}.png"
            blurb = _safe(str(getattr(tpl, 'blurb', '') or '')).replace('\n', ' ')
            # Внешность мы не выводим из кода — используем blurb как основу.
            lines.append(f"- **{base}** — {tpl.emoji} {tpl.name}: {blurb}  | Картинка: `{art}`")
        lines.append("")

    root = Path(__file__).resolve().parent
    out_path = root / "docs" / "monster_reference_21_40.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

