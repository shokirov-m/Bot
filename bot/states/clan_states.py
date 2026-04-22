"""FSM: создание клана, объявление войны, редактирование профиля."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ClanCreateStates(StatesGroup):
    waiting_name = State()
    waiting_tag = State()


class ClanWarDeclareStates(StatesGroup):
    waiting_target_id = State()


class ClanDonateStates(StatesGroup):
    waiting_amount = State()


class ClanSettingsStates(StatesGroup):
    waiting_description = State()
    waiting_tag = State()
    waiting_name = State()
    waiting_chat_url = State()
    waiting_join_id = State()   # ввод ID вручную при вступлении
