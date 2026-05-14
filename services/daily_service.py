"""
Ежедневка: 3 победы за день (UTC) → награда, стрик по дням с наградой подряд.
Состояние в character.meta_progress['daily_v1'].
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from aiogram import Bot
from bot.i18n import t
from db.models.character import Character
from db.repository import character_repo
from sqlalchemy.ext.asyncio import AsyncSession
from services import character_service
from services.subscription_service import channel_public_url, subscription_check

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
        st["kc"] = min(KILLS_GOAL, int(st["kc"]) + 1)
    _save_state(character, meta, st)


def format_daily_box_html(character: Character, *, locale: str, subscribed: bool) -> str:
    """Текст блока ежедневки (HTML)."""
    _ = locale
    today = _utc_today_iso()
    _, st = _load_state(character)
    kc = st["kc"] if st["kd"] == today else 0
    claimed = st["lcd"] == today
    streak = int(st["streak"])
    battles_ok = kc >= KILLS_GOAL
    sub_ok = subscribed
    battle_suffix = " ✅" if battles_ok else ""
    bline = f"⚔️ Бои: [ {kc} / {KILLS_GOAL} ]{battle_suffix}"
    ch_lbl = "Подписан" if sub_ok else "Не подписан"
    ch_suffix = " ✅" if sub_ok else " ❌"
    ch_line = f"📢 Канал: [ {ch_lbl} ]{ch_suffix}"
    if claimed:
        rew = "Получена ✅"
    elif battles_ok and sub_ok:
        rew = "Можно забрать"
    elif not battles_ok:
        rew = "В процессе"
    else:
        rew = "Нужна подписка"
    streak_lbl = f"{streak} дн."
    lines = [
        "<b>📅 ЕЖЕДНЕВКА</b>",
        "",
        "Цели:",
        bline,
        ch_line,
        "",
        "Статус:",
        f"🔥 Серия побед: {streak_lbl}",
        f"🎁 Награда: {rew}",
        "⏳ Обновление в 00:00 UTC",
    ]
    return "\n".join(lines)


def describe_daily_html(character: Character, *, locale: str, title_html: str) -> str:
    """Совместимость: без флага подписки — только блок (канал как не подписан)."""
    del title_html
    return format_daily_box_html(character, locale=locale, subscribed=False)


@dataclass
class ClaimResult:
    ok: bool
    message_html: str


# Вехи стрика дают одноразовый множитель к ежедневной награде в день, когда стрик достиг цифры.
STREAK_MILESTONE_MULTIPLIERS: dict[int, int] = {15: 2, 30: 3, 50: 5, 100: 10}


def streak_milestone_multiplier(streak: int) -> int:
    """1 — обычный день; 2/3/5/10 — на вехах стрика."""
    return STREAK_MILESTONE_MULTIPLIERS.get(int(streak), 1)


def _calculate_rewards_and_streak(st: dict, today: str) -> tuple[int, int, int, int]:
    """Внутренняя логика: (золото, опыт, новый_стрик, множитель_вехи)."""
    prev_lcd = st["lcd"]
    if prev_lcd is None:
        new_streak = 1
    else:
        try:
            prev_day = date.fromisoformat(str(prev_lcd))
            today_day = date.fromisoformat(today)
            if (today_day - prev_day).days == 1:
                new_streak = int(st["streak"]) + 1
            else:
                new_streak = 1
        except ValueError:
            new_streak = 1
    base_gold = 35 + new_streak * 8
    base_xp = 15 + new_streak * 4
    multiplier = streak_milestone_multiplier(new_streak)
    gold = base_gold * multiplier
    xp = base_xp * multiplier
    return gold, xp, new_streak, multiplier


def compute_next_daily_claim_rewards(character: Character) -> tuple[int, int, int, int] | None:
    """
    Если сегодня награду ещё не забирали — (gold, xp, streak_после_получения, множитель).
    Если уже забрали — None.
    """
    today = _utc_today_iso()
    _, st = _load_state(character)
    if st["lcd"] == today:
        return None
    return _calculate_rewards_and_streak(st, today)


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
    telegram_id: int | None = None,
) -> ClaimResult:
    await character_repo.lock_character_row(session, character.id)
    today = _utc_today_iso()
    meta, st = _load_state(character)
    if st["lcd"] == today:
        return ClaimResult(False, "")
    if st["kd"] != today or st["kc"] < KILLS_GOAL:
        need = max(0, KILLS_GOAL - (st["kc"] if st["kd"] == today else 0))
        return ClaimResult(False, t(locale, "daily_claim_need", goal=KILLS_GOAL, need=need))

    gold, xp, new_streak, multiplier = _calculate_rewards_and_streak(st, today)
    await character_service.add_gold_async(
        session,
        character,
        gold,
        source="daily_reward",
        bot=bot,
        telegram_id=telegram_id,
    )
    lv = await character_service.add_experience_async(session, character, xp, bot=bot)

    st["streak"] = new_streak
    st["lcd"] = today
    st["kc"] = 0
    _save_state(character, meta, st)

    bonus = character_service.level_up_notice_html(character, lv)
    if multiplier > 1:
        bonus = (
            f"\n🎉 <b>Веха стрика {new_streak}!</b> Награда увеличена ×{multiplier}."
            + (bonus or "")
        )
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


async def build_daily_body_html(
    bot: Bot,
    telegram_user_id: int,
    character: Character,
    *,
    locale: str,
    title_html: str | None = None,
) -> tuple[str, bool]:
    """
    Полный HTML текста ежедневки и флаг «подписан на канал».
    """
    del title_html
    subscribed, api_hint = await subscription_check(bot, telegram_user_id, locale=locale)
    box = format_daily_box_html(character, locale=locale, subscribed=subscribed)
    name = t(locale, "channel_display_name")
    url = channel_public_url()
    link = f'<a href="{html.escape(url)}">{html.escape(name)}</a>'
    if api_hint:
        extra = "\n" + api_hint
    elif not subscribed:
        extra = "\n" + t(locale, "daily_sub_required", channel=html.escape(name), link=link)
    else:
        extra = "\n" + t(locale, "daily_sub_ok")
    return box + extra, subscribed
