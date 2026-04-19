"""
Legacy callbacks arc:b:* / arc:s:* — классовая ветка отключена (профессии).
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

router = Router(name="class_arc")

_DEPRECATED = (
    "Классовая ветка заменена профессиями: открой статус → «Профессии» или общее меню."
)


@router.callback_query(F.data.startswith("arc:b:"))
async def on_pick_base_class_deprecated(query: CallbackQuery) -> None:
    await query.answer(_DEPRECATED, show_alert=True)


@router.callback_query(F.data.startswith("arc:s:"))
async def on_pick_subclass_deprecated(query: CallbackQuery) -> None:
    await query.answer(_DEPRECATED, show_alert=True)
