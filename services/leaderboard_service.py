"""Текст экрана топа игроков."""

from __future__ import annotations

import html

from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import t
from db.models.character import Character
from db.repository import leaderboard_repo

RANKER_TOP_N = 5
RANKER_GOLD_MULT = 1.05

_FETCHERS_FOR_RANKER = (
    leaderboard_repo.top_by_level,
    leaderboard_repo.top_by_floor,
    leaderboard_repo.top_by_stat_sum,
    leaderboard_repo.top_by_gold,
)


def _short_display(name: str, max_len: int = 22) -> str:
    n = (name or "").strip()
    if len(n) <= max_len:
        return n
    return n[: max_len - 1] + "…"


async def character_has_ranker_gold_bonus(session: AsyncSession, character: Character) -> bool:
    """Топ-5 в любой из четырёх категорий — +5% золота с монстров (не титул)."""
    cid = int(character.id)
    for fetcher in _FETCHERS_FOR_RANKER:
        rows = await fetcher(session, limit=RANKER_TOP_N)
        if any(int(c.id) == cid for c in rows):
            return True
    return False


def format_leaderboard_html(category: str, rows: list[Character], *, locale: str = "ru") -> str:
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
        ranker_suffix = f" {t(locale, 'top_ranker_badge')}" if i <= RANKER_TOP_N else ""
        if category == "lvl":
            extra = f"Ур.{c.level} · этаж {c.floor_number} · опыт {int(c.experience):,}"
        elif category == "flr":
            extra = f"этаж {c.floor_number} · Ур.{c.level}"
        elif category == "pow":
            s = leaderboard_repo.character_total_stats(c)
            extra = f"сумма статов {s} · Ур.{c.level} · этаж {c.floor_number}"
        else:
            extra = f"{int(c.gold):,} 💰 · Ур.{c.level}"
        lines.append(f"{med} <b>{name}</b>{ranker_suffix}\n   <i>{extra}</i>")
    lines.append("")
    lines.append(
        "<i>Забаненные не учитываются. Нажми категорию снизу, чтобы переключить.</i>\n"
        f"{t(locale, 'top_ranker_rule_hint')}",
    )
    return "\n".join(lines)
