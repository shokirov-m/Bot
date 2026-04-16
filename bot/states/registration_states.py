"""FSM: пол → ник → портрет перед созданием персонажа."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_gender = State()
    waiting_nickname = State()
    waiting_portrait = State()
