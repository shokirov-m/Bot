"""FSM: ввод стартовой цены лота."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AuctionCreateStates(StatesGroup):
    waiting_price = State()
    waiting_reprice = State()
