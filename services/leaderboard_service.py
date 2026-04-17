"""Текст экрана топа игроков и бонусы за место в рейтинге."""

from __future__ import annotations

import html

from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import t
from db.models.character import Character
from db.repository import leaderboard_repo

RANKER_TOP_N = 5

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


async def best_leaderboard_rank(session: AsyncSession, character: Character) -> int | None:
    """
    Лучшее место (1 = лучший) среди четырёх топов по текущему снимку.
    None — ни в одном топе из первых пяти.
    """
    cid = int(character.id)
    best: int | None = None
    for fetcher in _FETCHERS_FOR_RANKER:
        rows = await fetcher(session, limit=RANKER_TOP_N)
        for i, c in enumerate(rows, start=1):
            if int(c.id) == cid:
                best = i if best is None else min(best, i)
                break
    return best


def rank_victory_gold_xp_multipliers(rank: int | None) -> tuple[float, float]:
    """Множители (золото, опыт) за победу над монстром по лучшему месту в топах."""
    if rank is None:
        return 1.0, 1.0
    if rank == 1:
        return 1.10, 1.05
    if rank == 2:
        return 1.08, 1.03
    if rank == 3:
        return 1.06, 1.01
    if rank <= RANKER_TOP_N:
        return 1.05, 1.0
    return 1.0, 1.0


async def victory_rank_reward_multipliers(
    session: AsyncSession,
    character: Character,
    *,
    locale: str,
) -> tuple[float, float, str]:
    """
    (gold_mult, xp_mult, html_note) для экрана победы.
    """
    rank = await best_leaderboard_rank(session, character)
    gm, xm = rank_victory_gold_xp_multipliers(rank)
    if rank is None:
        return 1.0, 1.0, ""
    note_key = f"combat_leader_tier_{rank}_note" if rank <= 3 else "combat_leader_tier_mid_note"
    note = t(locale, note_key)
    return gm, xm, note


async def profile_ranker_status_line(session: AsyncSession, character: Character, *, locale: str) -> str:
    """Строка для профиля; пусто если нет бонуса."""
    rank = await best_leaderboard_rank(session, character)
    if rank is None:
        return ""
    if rank <= 3:
        return t(locale, f"profile_ranker_tier_{rank}_line")
    return t(locale, "profile_ranker_tier_45_line")


async def profile_ranker_status_parts(
    session: AsyncSession,
    character: Character,
    *,
    locale: str,
) -> tuple[str, str]:
    """(короткий бейдж для строки «Звание», строка эффекта); обе пустые, если не ранкер."""
    rank = await best_leaderboard_rank(session, character)
    if rank is None:
        return "", ""
    if rank <= 3:
        return t(locale, f"profile_ranker_badge_tier_{rank}"), t(locale, f"profile_ranker_effect_tier_{rank}")
    return t(locale, "profile_ranker_badge_tier_45"), t(locale, "profile_ranker_effect_tier_45")


async def character_has_ranker_gold_bonus(session: AsyncSession, character: Character) -> bool:
    """Совместимость: True если персонаж в топ-5 хотя бы в одной категории."""
    r = await best_leaderboard_rank(session, character)
    return r is not None and r <= RANKER_TOP_N


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
            extra = (
                f"Lv.{c.level} · XP {int(c.experience):,}"
                if locale == "en"
                else f"Ур.{c.level} · опыт {int(c.experience):,}"
            )
        elif category == "flr":
            extra = f"этаж {c.floor_number} · Ур.{c.level}"
        elif category == "pow":
            s = leaderboard_repo.character_total_stats(c)
            extra = f"сумма статов {s} · Ур.{c.level} · этаж {c.floor_number}"
        else:
            extra = f"{int(c.gold):,} 💰 · Ур.{c.level}"
        lines.append(f"{med} <b>{name}</b>{ranker_suffix}\n   <i>{extra}</i>")
        if i < len(rows):
            lines.append("")
    lines.append("")
    lines.append(
        "<i>Забаненные не учитываются. Нажми категорию снизу, чтобы переключить.</i>\n"
        f"{t(locale, 'top_ranker_rule_hint')}",
    )
    return "\n".join(lines)
