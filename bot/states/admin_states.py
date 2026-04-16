"""FSM админ-панели: ожидание текста после нажатия кнопки."""

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_input = State()
