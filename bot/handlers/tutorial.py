"""Колбэки tut:* — подсказки."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

import services.progression.tutorial_service as tutorial_service

router = Router(name="tutorial")


@router.callback_query(F.data == "tut:tip:flr")
async def tut_tip_floor(callback: CallbackQuery) -> None:
    await callback.answer(tutorial_service.tip_floor_ru(), show_alert=True)


@router.callback_query(F.data == "tut:tip:inv")
async def tut_tip_inv(callback: CallbackQuery) -> None:
    await callback.answer(tutorial_service.tip_inv_ru(), show_alert=True)


@router.callback_query(F.data == "tut:claim")
async def tut_claim_bonus(callback: CallbackQuery) -> None:
    await callback.answer("Этот бонус отключён — золото зарабатывается в боях и ежедневке.", show_alert=True)
