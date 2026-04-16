"""
Кланы: заглушка. Полный цикл (создание, чат, уровень, захват этажей) — отдельная задача.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="clans")

CLAN_STUB = (
    "⚔️ <b>Кланы</b>\n\n"
    "Скоро: создание клана, общий чат, клановый уровень и совместные цели на этажах башни.\n"
    "Следи за обновлениями бота."
)


@router.message(Command("clan", "клан"))
async def cmd_clan_stub(message: Message) -> None:
    await message.answer(CLAN_STUB, parse_mode=ParseMode.HTML)
