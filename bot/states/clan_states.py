"""FSM: создание клана и объявление войны."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ClanCreateStates(StatesGroup):
    waiting_name = State()
    waiting_tag = State()


class ClanWarDeclareStates(StatesGroup):
    waiting_target_id = State()


class ClanDonateStates(StatesGroup):
    waiting_amount = State()
