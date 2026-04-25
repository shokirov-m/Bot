"""
Применение золотых sinks в городах (лотерея, ростовщик, сейф банка).
"""

from __future__ import annotations

import html

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from game.economy import sinks as sink_rules
from game.floors import floor_data
from game.locations import cities as city_locations
from utils.ui import LINE_SEP


def _mp(c: Character) -> dict:
    return dict(c.meta_progress or {})


def _save_mp(c: Character, mp: dict) -> None:
    c.meta_progress = mp


def economy_hub_intro_html(character: Character) -> str:
    city = floor_data.get_city_for_floor(character.floor_number)
    if city is None:
        return ""
    ext = city_locations.get_city_hub_def(int(city.floor))
    ticket = sink_rules.lottery_ticket_cost_gold(int(city.floor))
    debt = sink_rules.moneylender_debt(character)
    bal = sink_rules.bank_safe_balance(character)
    cap = sink_rules.bank_safe_capacity(character)
    lines = [
        "💸 <b>Экономика города</b>",
        f"<i>Билет лотереи: <b>{ticket}</b> 💰 · Долг ростовщику: <b>{debt}</b> 💰</i>",
        f"<i>Сейф банка: <b>{bal}</b> / <b>{cap}</b> 💰 (при смерти не сгорает).</i>",
        LINE_SEP,
    ]
    if ext:
        lines.append(f"<i>{html.escape(ext.economy_blurb)}</i>")
        lines.append(LINE_SEP)
    lines.append("Выбери действие ниже. Золото уходит из экономики башни — так дольше держится баланс.")
    return "\n".join(lines)


def bank_safe_intro_html(character: Character) -> str:
    bal = sink_rules.bank_safe_balance(character)
    cap = sink_rules.bank_safe_capacity(character)
    lvl = sink_rules.bank_safe_capacity_level(character)
    next_cost = sink_rules.bank_safe_upgrade_cost_gold(character)
    return "\n".join(
        [
            "🏦 <b>Сейф гильдии</b>",
            f"В сейфе: <b>{bal}</b> / <b>{cap}</b> 💰",
            "<i>Золото в сейфе не списывается при поражении в башне.</i>",
            LINE_SEP,
            f"Уровень хранилища: <b>{lvl}</b>. Следующее улучшение: <b>{next_cost}</b> 💰 (+500 к лимиту).",
            LINE_SEP,
            "Вноси и снимай кнопками. «Всё влезет» — переносит из кошелька столько, сколько помещается.",
        ],
    )


def _in_city_hub(character: Character, floor_key: int) -> bool:
    return int(character.floor_number) == int(floor_key) and floor_data.get_city_for_floor(
        character.floor_number,
    ) is not None


def try_play_lottery(character: Character, *, floor_key: int) -> tuple[bool, str]:
    if int(character.floor_number) != int(floor_key):
        return False, "Ты не на этом этаже."
    if floor_data.get_city_for_floor(character.floor_number) is None:
        return False, "Лотерея только в городе-хабе."
    cost = sink_rules.lottery_ticket_cost_gold(int(floor_key))
    if int(character.gold) < cost:
        return False, f"Нужно {cost} золота для билета."
    dg, dr, code = sink_rules.run_lottery_draw(cost)
    character_service.add_gold(character, dg)
    character.rune_stones = int(character.rune_stones) + int(dr)
    mp = _mp(character)
    mp[sink_rules.META_LOTTERY_SPENT] = int(mp.get(sink_rules.META_LOTTERY_SPENT, 0)) + cost
    _save_mp(character, mp)
    msg = sink_rules.format_lottery_outcome_ru(code, cost, int(dg), int(dr))
    return True, msg


def try_borrow_moneylender(character: Character, *, floor_key: int) -> tuple[bool, str]:
    if int(character.floor_number) != int(floor_key):
        return False, "Ты не на этом этаже."
    if floor_data.get_city_for_floor(character.floor_number) is None:
        return False, "Ростовщик только в городе."
    if sink_rules.moneylender_debt(character) > 0:
        return False, "Сначала погаси текущий долг."
    amt = sink_rules.quick_borrow_amount(character)
    if amt < 50:
        return False, "Слишком низкий потолок займа."
    debt_total = sink_rules.debt_for_borrow(amt)
    character_service.add_gold(character, amt)
    sink_rules.set_moneylender_debt(character, debt_total)
    return True, (
        f"Ростовщик выдаёт <b>{amt}</b> 💰 под запись. "
        f"К возврату <b>{debt_total}</b> 💰 (комиссия заложена). Погашай кнопкой «Внести платёж»."
    )


def try_repay_moneylender(character: Character, *, floor_key: int) -> tuple[bool, str]:
    if int(character.floor_number) != int(floor_key):
        return False, "Ты не на этом этаже."
    d = sink_rules.moneylender_debt(character)
    if d <= 0:
        return False, "Долга нет."
    pay = min(d, int(character.gold), max(50, d // 4))
    if int(character.gold) < pay:
        return False, "Недостаточно золота для минимального платежа."
    character_service.add_gold(character, -pay)
    sink_rules.set_moneylender_debt(character, d - pay)
    left = sink_rules.moneylender_debt(character)
    tail = " Долг закрыт." if left == 0 else f" Остаток долга: <b>{left}</b> 💰."
    return True, f"Внесено <b>{pay}</b> 💰.{tail}"


def try_bank_safe_deposit(character: Character, *, floor_key: int, amount: int) -> tuple[bool, str]:
    if not _in_city_hub(character, floor_key):
        return False, "Сейф только в городе-хабе."
    return sink_rules.try_bank_safe_deposit(character, amount)


def try_bank_safe_withdraw(character: Character, *, floor_key: int, amount: int) -> tuple[bool, str]:
    if not _in_city_hub(character, floor_key):
        return False, "Сейф только в городе-хабе."
    return sink_rules.try_bank_safe_withdraw(character, amount)


def try_bank_safe_upgrade(character: Character, *, floor_key: int) -> tuple[bool, str]:
    if not _in_city_hub(character, floor_key):
        return False, "Сейф только в городе-хабе."
    return sink_rules.try_bank_safe_upgrade(character)


async def flush(session: AsyncSession, character: Character) -> None:
    await session.flush()


BANK_BACK_UI_KEY = "_econ_bank_back_v1"


def set_bank_ui_back(character: Character, mode: str) -> None:
    mp = _mp(character)
    mp[BANK_BACK_UI_KEY] = mode if mode in ("hub", "mkt") else "hub"
    _save_mp(character, mp)


def bank_ui_back(character: Character) -> str:
    v = str(_mp(character).get(BANK_BACK_UI_KEY) or "hub")
    return v if v in ("hub", "mkt") else "hub"


def clear_bank_ui_back(character: Character) -> None:
    mp = _mp(character)
    mp.pop(BANK_BACK_UI_KEY, None)
    _save_mp(character, mp)
