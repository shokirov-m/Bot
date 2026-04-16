"""
Применение золотых sinks в городах (лотерея, ростовщик, пожертвования, банк).
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
    fee_bank = sink_rules.bank_custody_fee(int(city.floor))
    lines = [
        "💸 <b>Экономика города</b>",
        f"<i>Билет лотереи: <b>{ticket}</b> 💰 · Долг ростовщику: <b>{debt}</b> 💰</i>",
        f"<i>Опека сейфа (разово): <b>{fee_bank}</b> 💰</i>",
        LINE_SEP,
    ]
    if ext:
        lines.append(f"<i>{html.escape(ext.economy_blurb)}</i>")
        lines.append(LINE_SEP)
    lines.append("Выбери действие ниже. Золото уходит из экономики башни — так дольше держится баланс.")
    return "\n".join(lines)


def try_play_lottery(character: Character, *, floor_key: int) -> tuple[bool, str]:
    if int(character.floor_number) != int(floor_key):
        return False, "Ты не на этом этаже."
    if floor_data.get_city_for_floor(character.floor_number) is None:
        return False, "Лотерея только в городе-хабе."
    cost = sink_rules.lottery_ticket_cost_gold(int(floor_key))
    if int(character.gold) < cost:
        return False, f"Нужно {cost} золота для билета."
    dg, dr, code = sink_rules.run_lottery_draw(cost)
    character.gold = int(character.gold) + int(dg)
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
    character.gold = int(character.gold) + amt
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
    character.gold = int(character.gold) - pay
    sink_rules.set_moneylender_debt(character, d - pay)
    left = sink_rules.moneylender_debt(character)
    tail = " Долг закрыт." if left == 0 else f" Остаток долга: <b>{left}</b> 💰."
    return True, f"Внесено <b>{pay}</b> 💰.{tail}"


def try_tithe(character: Character, *, floor_key: int, tier: int) -> tuple[bool, str]:
    if int(character.floor_number) != int(floor_key):
        return False, "Ты не на этом этаже."
    if floor_data.get_city_for_floor(character.floor_number) is None:
        return False, "Пожертвования принимают только в хабе."
    if tier < 0 or tier >= len(sink_rules.TITHE_TIERS_GOLD):
        return False, "Неверный уровень пожертвования."
    g = int(sink_rules.TITHE_TIERS_GOLD[tier])
    if int(character.gold) < g:
        return False, f"Нужно {g} золота."
    character.gold = int(character.gold) - g
    mp = _mp(character)
    mp[sink_rules.META_TITHE_GOLD_TOTAL] = int(mp.get(sink_rules.META_TITHE_GOLD_TOTAL, 0)) + g
    _save_mp(character, mp)
    return True, (
        f"Благодарность принята: <b>−{g}</b> 💰 в фонд содержания стен и стражи. "
        "Башня помнит щедрых."
    )


def try_buy_bank_custody(character: Character, *, floor_key: int) -> tuple[bool, str]:
    if int(character.floor_number) != int(floor_key):
        return False, "Ты не на этом этаже."
    if floor_data.get_city_for_floor(character.floor_number) is None:
        return False, "Услуга только в городе."
    if sink_rules.bank_custody_paid(character):
        return False, "Опека сейфа уже оформлена навсегда для этого героя."
    fee = sink_rules.bank_custody_fee(int(floor_key))
    if int(character.gold) < fee:
        return False, f"Нужно {fee} золота."
    character.gold = int(character.gold) - fee
    sink_rules.set_bank_custody(character, True)
    return True, (
        f"Гильдия оформила опеку записей: <b>−{fee}</b> 💰. "
        "В будущих обновлениях это снизит комиссии обмена и даст метку доверенного клиента."
    )


async def flush(session: AsyncSession, character: Character) -> None:
    await session.flush()
