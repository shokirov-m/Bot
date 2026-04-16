"""Текст экрана топа игроков."""

from __future__ import annotations

import html

from db.models.character import Character
from db.repository import leaderboard_repo


def _short_display(name: str, max_len: int = 22) -> str:
    n = (name or "").strip()
    if len(n) <= max_len:
        return n
    return n[: max_len - 1] + "…"


def format_leaderboard_html(category: str, rows: list[Character]) -> str:
    titles = {
        "lvl": "📈 <b>Топ по уровню</b>",
        "flr": "🗺️ <b>Топ по этажу</b>",
        "pow": "💪 <b>Топ по сумме статов</b> <i>(СИЛ+ЛОВ+ИНТ+ВЫН+УДА)</i>",
        "gld": "💰 <b>Топ по золоту</b>",
    }
    head = titles.get(category, "📊 <b>Топ</b>")
    if not rows:
        return f"{head}\n\n<i>Пока никого в рейтинге.</i>"

    lines = [head, ""]
    for i, c in enumerate(rows, start=1):
        med = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        name = html.escape(_short_display(c.display_name))
        if category == "lvl":
            extra = f"Ур.{c.level} · этаж {c.floor_number} · опыт {int(c.experience):,}"
        elif category == "flr":
            extra = f"этаж {c.floor_number} · Ур.{c.level}"
        elif category == "pow":
            s = leaderboard_repo.character_total_stats(c)
            extra = f"сумма статов {s} · Ур.{c.level} · этаж {c.floor_number}"
        else:
            extra = f"{int(c.gold):,} 💰 · Ур.{c.level}"
        lines.append(f"{med} <b>{name}</b>\n   <i>{extra}</i>")
    lines.append("")
    lines.append("<i>Забаненные не учитываются. Нажми категорию снизу, чтобы переключить.</i>")
    return "\n".join(lines)
