"""FSM состояний боя."""

from aiogram.fsm.state import State, StatesGroup


class CombatStates(StatesGroup):
    """Игрок в активном бою."""

    in_battle = State()
