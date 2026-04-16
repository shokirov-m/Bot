"""FSM: ввод ID соперника и пошаговая дуэль на арене."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ArenaChallengeStates(StatesGroup):
    waiting_opponent_token = State()


class ArenaTurnStates(StatesGroup):
    in_duel = State()
