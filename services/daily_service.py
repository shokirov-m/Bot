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


def describe_daily_html(character: Character, *, locale: str, title_html: str) -> str:
    """Текст экрана /daily (без награды). Заголовок и строки — по locale."""
    today = _utc_today_iso()
    _, st = _load_state(character)
    kc = st["kc"] if st["kd"] == today else 0
    claimed = st["lcd"] == today
    lines = [
        title_html,
        t(locale, "daily_today_kills", kc=kc, goal=KILLS_GOAL),
        t(locale, "daily_streak_line", streak=st["streak"]),
    ]
    if claimed:
        lines.append(t(locale, "daily_claimed_today"))
    elif kc >= KILLS_GOAL:
        lines.append(t(locale, "daily_can_claim_hint"))
    else:
        lines.append(t(locale, "daily_need_kills", need=KILLS_GOAL - kc))
    return "\n".join(lines)


@dataclass
class ClaimResult:
    ok: bool
    message_html: str


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
