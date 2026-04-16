"""Обработка подкоманд /admin promo …"""

from __future__ import annotations

import html
import re

from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from db.repository import admin_log_repo, promo_offer_repo

_CODE_RE = re.compile(r"^[A-Z0-9_]{3,40}$")


def promo_help_html() -> str:
    """Текст справки по /admin promo (для кнопок)."""
    return _usage_html()


def _usage_html() -> str:
    return (
        "🎁 <b>Промокоды (БД)</b>\n"
        "<code>/admin promo add КОД ЗОЛОТО XP РУНЫ МАКС_АКТИВАЦИЙ ДНЕЙ</code>\n"
        "· <b>МАКС_АКТИВАЦИЙ</b> — 0 = без лимита (всего по коду)\n"
        "· <b>ДНЕЙ</b> — срок с момента создания; 0 = бессрочно\n"
        "Пример: <code>/admin promo add STREAM500 500 100 2 50 14</code>\n"
        "<code>/admin promo list</code> — последние коды\n"
        "<code>/admin promo on КОД</code> / <code>off КОД</code>\n"
        "<code>/admin promo del КОД</code> — удалить запись\n"
        "<i>Статические коды из кода бота (game/promos.py) работают, если в БД нет строки с тем же кодом.</i>"
    )


async def handle_admin_promo(
    message: Message,
    session: AsyncSession,
    parts: list[str],
    *,
    actor_telegram_id: int,
) -> None:
    """parts[0] == 'promo'."""
    if len(parts) < 2:
        await message.answer(_usage_html(), parse_mode="HTML")
        return

    action = parts[1].lower()

    if action == "list":
        rows = await promo_offer_repo.list_recent(session, limit=20)
        if not rows:
            await message.answer("В БД пока нет промокодов.")
            return
        lines: list[str] = ["🎁 <b>Промокоды в БД</b> (последние 20)"]
        for o in rows:
            lim = "∞" if o.max_uses is None else f"{o.uses_count}/{o.max_uses}"
            until = "∞" if o.valid_until is None else o.valid_until.strftime("%Y-%m-%d %H:%M UTC")
            act = "✅" if o.is_active else "⛔"
            lines.append(
                f"{act} <code>{html.escape(o.code_key)}</code> "
                f"💰{o.gold} 📈{o.xp} ⚗{o.rune_stones} · акт. {lim} · до {html.escape(until)}",
            )
        await message.answer("\n".join(lines), parse_mode="HTML")
        return

    if action == "add":
        if len(parts) < 8:
            await message.answer("Мало аргументов.\n" + _usage_html(), parse_mode="HTML")
            return
        raw_code = parts[2].strip().upper()
        if not _CODE_RE.match(raw_code):
            await message.answer("Код: 3–40 символов, латиница, цифры, подчёркивание.")
            return
        try:
            gold = int(parts[3])
            xp = int(parts[4])
            rune = int(parts[5])
            max_uses = int(parts[6])
            days = int(parts[7])
        except ValueError:
            await message.answer("ЗОЛОТО, XP, РУНЫ, МАКС и ДНЕЙ — целые числа.")
            return
        if gold < 0 or xp < 0 or rune < 0 or max_uses < 0 or days < 0:
            await message.answer("Отрицательные значения недопустимы.")
            return
        if gold == 0 and xp == 0 and rune == 0:
            await message.answer("Хотя бы одна награда (золото, XP или руны) должна быть больше нуля.")
            return

        if await promo_offer_repo.get_by_code(session, raw_code):
            await message.answer(f"Код <code>{html.escape(raw_code)}</code> уже есть в БД.", parse_mode="HTML")
            return

        try:
            await promo_offer_repo.create_offer(
                session,
                code_key=raw_code,
                gold=gold,
                xp=xp,
                rune_stones=rune,
                max_uses=None if max_uses == 0 else max_uses,
                valid_days=None if days == 0 else days,
                created_by_telegram_id=actor_telegram_id,
            )
            await admin_log_repo.save_log(
                session,
                actor_telegram_id=actor_telegram_id,
                target_user_id=None,
                action="admin_promo_add",
                severity="INFO",
                message=raw_code,
                payload={
                    "code": raw_code,
                    "gold": gold,
                    "xp": xp,
                    "rune_stones": rune,
                    "max_uses": max_uses,
                    "days": days,
                },
            )
            await session.commit()
        except Exception:
            logger.exception("admin promo add")
            await session.rollback()
            await message.answer("Ошибка БД (возможно, дубликат кода).")
            return

        lim_s = "без лимита" if max_uses == 0 else str(max_uses)
        days_s = "бессрочно" if days == 0 else f"{days} дн."
        await message.answer(
            f"✅ Промокод <code>{html.escape(raw_code)}</code> создан.\n"
            f"Награды: 💰{gold} 📈{xp} ⚗{rune}\n"
            f"Макс. активаций: {html.escape(lim_s)} · срок: {html.escape(days_s)}",
            parse_mode="HTML",
        )
        return

    if action in ("on", "off", "del", "delete"):
        if len(parts) < 3:
            await message.answer("Укажи код: <code>/admin promo off КОД</code>", parse_mode="HTML")
            return
        ck = parts[2].strip().upper()
        if action in ("del", "delete"):
            ok = await promo_offer_repo.delete_by_code(session, ck)
            if ok:
                await admin_log_repo.save_log(
                    session,
                    actor_telegram_id=actor_telegram_id,
                    target_user_id=None,
                    action="admin_promo_del",
                    severity="INFO",
                    message=ck,
                    payload={"code": ck},
                )
                await session.commit()
                await message.answer(f"Удалено: <code>{html.escape(ck)}</code>", parse_mode="HTML")
            else:
                await message.answer("Код в БД не найден.")
            return

        ok = await promo_offer_repo.set_active(session, ck, active=(action == "on"))
        if ok:
            await admin_log_repo.save_log(
                session,
                actor_telegram_id=actor_telegram_id,
                target_user_id=None,
                action=f"admin_promo_{action}",
                severity="INFO",
                message=ck,
                payload={"code": ck},
            )
            await session.commit()
            await message.answer(
                f"{'Включён' if action == 'on' else 'Выключен'}: <code>{html.escape(ck)}</code>",
                parse_mode="HTML",
            )
        else:
            await message.answer("Код в БД не найден.")
        return

    await message.answer(_usage_html(), parse_mode="HTML")
