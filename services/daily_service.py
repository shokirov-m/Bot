"""
Ежедневка: 3 победы за день (UTC) → награда, стрик по дням с наградой подряд.
Состояние в character.meta_progress['daily_v1'].
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from bot.i18n import t
from db.models.character import Character
from sqlalchemy.ext.asyncio import AsyncSession
from services import character_service

META_KEY = "daily_v1"
KILLS_GOAL = 3


def _utc_today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


def _load_state(character: Character) -> dict:
    meta = dict(character.meta_progress or {})
    raw = meta.get(META_KEY)
    if not isinstance(raw, dict):
        raw = {}
    return meta, {
        "kd": raw.get("kd"),  # дата (ISO), за которую считаем убийства
        "kc": int(raw.get("kc", 0)),
        "lcd": raw.get("lcd"),  # последний день, когда забрали награду
        "streak": int(raw.get("streak", 0)),
    }


def _save_state(character: Character, meta: dict, st: dict) -> None:
    meta[META_KEY] = {
        "kd": st["kd"],
        "kc": st["kc"],
        "lcd": st["lcd"],
        "streak": st["streak"],
    }
    character.meta_progress = meta


def record_kill(character: Character) -> None:
    """Вызывать после засчитанной победы в бою."""
    today = _utc_today_iso()
    meta, st = _load_state(character)
    if st["kd"] != today:
        st["kd"] = today
        st["kc"] = 1
    else:
        st["kc"] = st["kc"] + 1
    _save_state(character, meta, st)


def format_daily_box_html(character: Character, *, locale: str, subscribed: bool) -> str:
    """Блок ежедневки в рамке (моноширинный через &lt;pre&gt;)."""
    today = _utc_today_iso()
    _, st = _load_state(character)
    kc = st["kc"] if st["kd"] == today else 0
    claimed = st["lcd"] == today
    streak = int(st["streak"])
    battles_ok = kc >= KILLS_GOAL
    sub_ok = subscribed
    if str(locale).lower().startswith("en"):
        bline = f"        ⚔️ Battles: [ {kc} / {KILLS_GOAL} ] {'✅' if battles_ok else ''}"
        ch_lbl = "Subscribed" if sub_ok else "Not subscribed"
        ch_line = f"        📢 Channel: [ {ch_lbl} ] {'✅' if sub_ok else '❌'}"
        if claimed:
            rew = "Claimed ✅"
        elif battles_ok and sub_ok:
            rew = "Ready — tap Claim"
        elif not battles_ok:
            rew = "In progress"
        else:
            rew = "Need channel sub"
        streak_lbl = f"{streak} day(s)"
        upd = "Resets at 00:00 UTC"
        title = "📅 DAILY"
    else:
        bline = f"        ⚔️ Бои: [ {kc} / {KILLS_GOAL} ] {'✅' if battles_ok else ''}"
        ch_lbl = "Подписан" if sub_ok else "Не подписан"
        ch_line = f"        📢 Канал: [ {ch_lbl} ] {'✅' if sub_ok else '❌'}"
        if claimed:
            rew = "Получена ✅"
        elif battles_ok and sub_ok:
            rew = "Можно забрать"
        elif not battles_ok:
            rew = "В процессе"
        else:
            rew = "Нужна подписка"
        streak_lbl = f"{streak} дн."
        upd = "Обновление в 00:00 UTC"
        title = "📅 ЕЖЕДНЕВКА"
    inner = "\n".join(
        [
            f"╔══════ {title} ══════╗",
            "        Цели:",
            bline,
            ch_line,
            "",
            "         Статус:",
            f"         🔥 Серия побед: {streak_lbl}",
            f"         🎁 Награда: {rew}",
            f"         ⏳ {upd}",
            "╚═══════════════════════╝",
        ],
    )
    return f"<pre>{inner}</pre>"


def describe_daily_html(character: Character, *, locale: str, title_html: str) -> str:
    """Совместимость: без флага подписки — только блок (канал как не подписан)."""
    del title_html
    return format_daily_box_html(character, locale=locale, subscribed=False)


@dataclass
class ClaimResult:
    ok: bool
    message_html: str


def compute_next_daily_claim_rewards(character: Character) -> tuple[int, int, int] | None:
    """
    Если сегодня награду ещё не забирали — (gold, xp, streak_после_получения).
    Если уже забрали — None.
    """
    today = _utc_today_iso()
    _, st = _load_state(character)
    if st["lcd"] == today:
        return None
    prev_lcd = st["lcd"]
    if prev_lcd is None:
        new_streak = 1
    else:
        try:
            prev_day = date.fromisoformat(str(prev_lcd))
            today_day = date.fromisoformat(today)
            if (today_day - prev_day).days == 1:
                new_streak = st["streak"] + 1
            else:
                new_streak = 1
        except ValueError:
            new_streak = 1
    gold = 35 + new_streak * 8
    xp = 15 + new_streak * 4
    return gold, xp, new_streak


def can_claim_daily_today(character: Character) -> bool:
    """Подписка проверяется снаружи; здесь только прогресс убийств."""
    today = _utc_today_iso()
    _, st = _load_state(character)
    if st["lcd"] == today:
        return False
    return st["kd"] == today and st["kc"] >= KILLS_GOAL


async def try_claim_daily_reward(
    session: AsyncSession,
    character: Character,
    *,
    locale: str = "ru",
    bot: Any = None,
) -> ClaimResult:
    today = _utc_today_iso()
    meta, st = _load_state(character)
    if st["lcd"] == today:
        return ClaimResult(False, "")
    if st["kd"] != today or st["kc"] < KILLS_GOAL:
        need = max(0, KILLS_GOAL - (st["kc"] if st["kd"] == today else 0))
        return ClaimResult(False, t(locale, "daily_claim_need", goal=KILLS_GOAL, need=need))

    prev_lcd = st["lcd"]
    if prev_lcd is None:
        new_streak = 1
    else:
        try:
            prev_day = date.fromisoformat(str(prev_lcd))
            today_day = date.fromisoformat(today)
            if (today_day - prev_day).days == 1:
                new_streak = st["streak"] + 1
            else:
                new_streak = 1
        except ValueError:
            new_streak = 1

    gold = 35 + new_streak * 8
    xp = 15 + new_streak * 4
    character_service.add_gold(character, gold)
    lv = await character_service.add_experience_async(session, character, xp, bot=bot)

    st["streak"] = new_streak
    st["lcd"] = today
    st["kc"] = 0
    _save_state(character, meta, st)

    bonus = character_service.level_up_notice_html(character, lv)
    return ClaimResult(
        True,
        t(
            locale,
            "daily_claim_reward",
            gold=gold,
            xp=xp,
            bonus=bonus,
            streak=new_streak,
        ),
    )
