"""FSM: ввод нового имени и промокода в настройках."""

from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    waiting_new_name = State()
    waiting_promo = State()
