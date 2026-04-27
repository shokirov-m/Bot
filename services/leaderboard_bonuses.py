"""
Раздельные бонусы за каждый топ:
- топ 1 «золото» → +5% к получаемому золоту
- топ 1 «уровень» → +10% к опыту
- топ 1 «статы» → +1% ко всем характеристикам
- топ 1 «этаж (рекорд)» → +5% к шансу выпадения материалов
- топ 1 «клан» → +10% к очкам за босса для всех членов

Места 2–5 получают 50% / 30% / 20% / 10% от базового бонуса.
Если игрок в нескольких топах — бонусы складываются (по разным эффектам, не один на всё).
"""

from __future__ import annotations

from typing import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.repository import leaderboard_repo

# Сколько мест в каждом топе вознаграждаются.
RANKER_TOP_N = 5

# Доля от базового бонуса по местам (1-е → 100%, 2–5-е — убывание).
_TIER_FRACTION: dict[int, float] = {
    1: 1.0,
    2: 0.5,
    3: 0.3,
    4: 0.2,
    5: 0.1,
}

# Базовые величины бонусов за «1-е место» (фракция от 1.0 = 100%).
BASE_GOLD = 0.05
BASE_XP = 0.10
BASE_STATS = 0.01
BASE_MATERIAL_DROP = 0.05
BASE_CLAN_BOSS = 0.10


def _tier_fraction(rank: int | None) -> float:
    if rank is None:
        return 0.0
    return _TIER_FRACTION.get(int(rank), 0.0)


_PERSONAL_FETCHERS: dict[str, Callable[..., Awaitable[list[Character]]]] = {
    "lvl": leaderboard_repo.top_by_level,
    "flr": leaderboard_repo.top_by_floor,
    "pow": leaderboard_repo.top_by_stat_sum,
    "gld": leaderboard_repo.top_by_gold,
}


async def per_board_ranks(
    session: AsyncSession,
    character: Character,
) -> dict[str, int | None]:
    """
    Места персонажа в четырёх личных топах + позиция его клана в топе кланов.
    None — не в топ-5 этого рейтинга.
    """
    cid = int(character.id)
    out: dict[str, int | None] = {"lvl": None, "flr": None, "pow": None, "gld": None, "clan": None}
    for key, fetcher in _PERSONAL_FETCHERS.items():
        rows = await fetcher(session, limit=RANKER_TOP_N)
        for i, c in enumerate(rows, start=1):
            if int(c.id) == cid:
                out[key] = i
                break

    # Клан — место клана текущего персонажа в топе кланов.
    try:
        from db.repository import clan_repo  # локальный импорт чтобы не плодить циклы

        m = await clan_repo.get_membership(session, cid)
        if m is not None:
            top_clans = await leaderboard_repo.top_clans(session, limit=RANKER_TOP_N)
            for i, cl in enumerate(top_clans, start=1):
                if int(cl.id) == int(m.clan_id):
                    out["clan"] = i
                    break
    except Exception:
        # Если репозиторий клана/механика недоступны — просто None.
        pass

    return out


def gold_multiplier(ranks: dict[str, int | None]) -> float:
    """Множитель к получаемому золоту (1.0 = без бонуса)."""
    return 1.0 + BASE_GOLD * _tier_fraction(ranks.get("gld"))


def xp_multiplier(ranks: dict[str, int | None]) -> float:
    """Множитель к получаемому опыту (1.0 = без бонуса)."""
    return 1.0 + BASE_XP * _tier_fraction(ranks.get("lvl"))


def all_stats_multiplier(ranks: dict[str, int | None]) -> float:
    """Множитель ко всем основным характеристикам (1.0 = без бонуса)."""
    return 1.0 + BASE_STATS * _tier_fraction(ranks.get("pow"))


def material_drop_multiplier(ranks: dict[str, int | None]) -> float:
    """Множитель к шансу выпадения материалов (1.0 = без бонуса)."""
    return 1.0 + BASE_MATERIAL_DROP * _tier_fraction(ranks.get("flr"))


def clan_boss_score_multiplier(ranks: dict[str, int | None]) -> float:
    """Множитель к очкам клана за босса (1.0 = без бонуса)."""
    return 1.0 + BASE_CLAN_BOSS * _tier_fraction(ranks.get("clan"))


def best_overall_rank(ranks: dict[str, int | None]) -> int | None:
    """Лучшее место среди всех топов (для бейджа в профиле)."""
    best: int | None = None
    for v in ranks.values():
        if v is None:
            continue
        best = v if best is None else min(best, v)
    return best


def _fmt_pct(mult: float) -> str:
    pct = (mult - 1.0) * 100.0
    return f"{pct:+.1f}".rstrip("0").rstrip(".") + "%"


def format_active_bonuses_html(ranks: dict[str, int | None]) -> str:
    """Список активных бонусов для отображения в профиле/полных хар-ках."""
    lines: list[str] = []
    if ranks.get("gld") is not None:
        m = gold_multiplier(ranks)
        if m > 1.0:
            lines.append(f"💰 Топ {ranks['gld']} по золоту → {_fmt_pct(m)} к золоту")
    if ranks.get("lvl") is not None:
        m = xp_multiplier(ranks)
        if m > 1.0:
            lines.append(f"📈 Топ {ranks['lvl']} по уровню → {_fmt_pct(m)} к опыту")
    if ranks.get("pow") is not None:
        m = all_stats_multiplier(ranks)
        if m > 1.0:
            lines.append(f"💪 Топ {ranks['pow']} по статам → {_fmt_pct(m)} ко всем статам")
    if ranks.get("flr") is not None:
        m = material_drop_multiplier(ranks)
        if m > 1.0:
            lines.append(f"🗺️ Топ {ranks['flr']} по этажу → {_fmt_pct(m)} к шансу материалов")
    if ranks.get("clan") is not None:
        m = clan_boss_score_multiplier(ranks)
        if m > 1.0:
            lines.append(f"🏰 Клан в топ-{ranks['clan']} → {_fmt_pct(m)} к очкам клана за боссов")
    return "\n".join(lines)
