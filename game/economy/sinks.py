"""
Поглотители золота в городах-хабах: лотерея, ростовщик, сейф банка.

Баланс (подкрутка v2): лотерея слегка «жёстче», билет дороже на высоких хабах;
долг ростовщика забирает долю золота с победы в бою до погашения.

Ручной QA: города между ярусами (0↔1, 30↔31, 60↔61, 90↔91) — экономика, кузница, стражник.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime
from typing import Any

# --- Ключи meta_progress ---
META_ML_DEBT = "sink_moneylender_debt"
META_LOTTERY_SPENT = "sink_lottery_gold_spent"
META_BANK_SAFE_BALANCE = "bank_safe_balance"
META_BANK_SAFE_LEVEL = "bank_safe_capacity_level"
META_NEXT_WIN_XP_MULT = "next_win_xp_mult"  # после успешного побега: −10% к опыту со след. победы

# --- Банковские проценты и срочные вклады (BALANCE_V2) ---
META_BANK_INTEREST_AT = "bank_interest_at_iso"  # время последнего начисления
META_BANK_INTEREST_PENDING = "bank_interest_pending"  # накопленные, но ещё не зачисленные проценты
META_BANK_SEAL = "bank_seal_unlocked"  # апгрейд «Банковская печать»
META_BANK_TERM = "bank_term"  # {amount, started_at_iso, term_h, rate}

BANK_RATE_PER_HOUR_BASE = 0.02  # 2%/ч
BANK_RATE_PER_HOUR_SEAL = 0.04  # 4%/ч с апгрейдом
BANK_INTEREST_CAP_PCT_BASE = 0.20  # до 20% от тела в накопленных процентах
BANK_INTEREST_CAP_PCT_SEAL = 0.24
BANK_SEAL_UPGRADE_COST = 5000

BANK_TERM_OPTIONS: tuple[tuple[int, float], ...] = (
    (24, 0.01),   # 24 часа — 1%
    (72, 0.04),   # 72 часа — 4%
    (168, 0.12),  # 7 дней — 12%
)


def _meta(character: Any) -> dict[str, Any]:
    return dict(character.meta_progress or {})


def _set_meta(character: Any, mp: dict[str, Any]) -> None:
    character.meta_progress = mp


def moneylender_debt(character: Any) -> int:
    return max(0, int(_meta(character).get(META_ML_DEBT, 0)))


def set_moneylender_debt(character: Any, value: int) -> None:
    mp = _meta(character)
    mp[META_ML_DEBT] = max(0, int(value))
    _set_meta(character, mp)


def set_escape_success_xp_penalty(character: Any) -> None:
    """Успешный побег: следующая победа даёт меньше опыта (стек не копим — перезапись)."""
    mp = _meta(character)
    mp[META_NEXT_WIN_XP_MULT] = 0.9
    _set_meta(character, mp)


def pop_next_win_xp_multiplier(character: Any) -> float:
    """Снять и вернуть множитель опыта за победу (1.0 по умолчанию)."""
    mp = _meta(character)
    raw = mp.pop(META_NEXT_WIN_XP_MULT, None)
    if raw is not None:
        _set_meta(character, mp)
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return 1.0
    return max(0.1, min(1.0, v))


def lottery_ticket_cost_gold(floor_number: int) -> int:
    """Цена билета растёт с «весом» города (этаж хаба)."""
    f = max(3, min(99, int(floor_number)))
    base = 24 + (f // 2) + (f // 10) * 6
    return int(base * 1.06)


def run_lottery_draw(ticket_cost: int) -> tuple[int, int, str]:
    """
    Итог розыгрыша относительно уплаченной цены билета.
    Возвращает (изменение золота, изменение рунных камней, короткий код события для текста).
    """
    r = random.random()
    c = max(1, int(ticket_cost))
    if r < 0.42:
        return -c, 0, "blank"
    if r < 0.64:
        back = int(c * random.uniform(0.35, 0.75))
        return -c + max(1, back), 0, "small_win"
    if r < 0.78:
        mult = random.uniform(1.15, 1.85)
        return -c + max(c + 1, int(c * mult)), 0, "nice_win"
    if r < 0.92:
        return -c, 1, "rune_pair"
    jackpot = int(c * random.uniform(4.0, 7.5))
    return -c + max(jackpot, c + 50), 0, "jackpot"


def max_borrow_offer(character: Any) -> int:
    lv = max(1, int(character.level))
    fl = max(3, int(character.floor_number))
    return min(2800, 120 + lv * 48 + fl * 14)


def quick_borrow_amount(character: Any) -> int:
    """Разовая кнопка «взять займ» — доля от потолка."""
    cap = max_borrow_offer(character)
    return max(100, min(500, cap // 2))


def debt_for_borrow(principal: int) -> int:
    """Сколько всего нужно вернуть (тело + комиссия ростовщика)."""
    p = max(1, int(principal))
    return int(p * 1.30) + max(0, p // 55)


# Доля награды за бой, уходящая в погашение долга (не в кошелёк), пока долг > 0.
VICTORY_GOLD_DEBT_FRACTION = 0.18

def garnish_victory_gold_for_debt(character: Any, gross_gold: int) -> tuple[int, str]:
    """
    С победы в башне: часть золота автоматически гасит долг ростовщика.
    Возвращает (золото, которое реально прибавится игроку, суффикс HTML для лога победы).
    """
    gross = max(0, int(gross_gold))
    d = moneylender_debt(character)
    if d <= 0 or gross <= 0:
        return gross, ""
    chunk = max(1, int(gross * VICTORY_GOLD_DEBT_FRACTION))
    pay = min(d, chunk, gross)
    new_d = d - pay
    set_moneylender_debt(character, new_d)
    net = gross - pay
    left = moneylender_debt(character)
    tail = (
        f"\n📉 <b>Ростовщик:</b> с добычи удержано <b>{pay}</b> 💰 в счёт долга "
        f"(остаток долга: <b>{left}</b> 💰)."
    )
    return net, tail


def bank_safe_balance(character: Any) -> int:
    return max(0, int(_meta(character).get(META_BANK_SAFE_BALANCE, 0)))


def bank_safe_capacity_level(character: Any) -> int:
    return max(0, int(_meta(character).get(META_BANK_SAFE_LEVEL, 0)))


def bank_safe_capacity(character: Any) -> int:
    """Макс. золота в сейфе: база 500 + уровни улучшения."""
    lv = bank_safe_capacity_level(character)
    return 500 + lv * 500


def bank_safe_space_left(character: Any) -> int:
    return max(0, bank_safe_capacity(character) - bank_safe_balance(character))


def bank_safe_upgrade_cost_gold(character: Any) -> int:
    """Стоимость следующего уровня вместимости."""
    lv = bank_safe_capacity_level(character)
    return 320 + lv * 180


def try_bank_safe_deposit(character: Any, amount: int) -> tuple[bool, str]:
    """
    amount > 0 — внести столько, сколько есть и влезает;
    amount == 0 — внести максимум (всё влезшее из кошелька).
    """
    cap = bank_safe_capacity(character)
    bal = bank_safe_balance(character)
    space = cap - bal
    if space <= 0:
        return False, "Сейф полон. Улучши хранилище."
    g = max(0, int(character.gold))
    if g <= 0:
        return False, "Нет золота в кошельке."
    if amount == 0:
        move = min(g, space)
    else:
        move = min(g, space, max(1, int(amount)))
    if move <= 0:
        return False, "Нечего вносить."
    mp = _meta(character)
    mp[META_BANK_SAFE_BALANCE] = bal + move
    character.gold = g - move
    _set_meta(character, mp)
    return True, f"В сейф положено <b>{move}</b> 💰. В сейфе: <b>{bal + move}</b> / {cap}."


def try_bank_safe_withdraw(character: Any, amount: int) -> tuple[bool, str]:
    """amount == 0 — снять всё из сейфа."""
    bal = bank_safe_balance(character)
    if bal <= 0:
        return False, "В сейфе пусто."
    if amount == 0:
        move = bal
    else:
        move = min(bal, max(1, int(amount)))
    mp = _meta(character)
    mp[META_BANK_SAFE_BALANCE] = bal - move
    character.gold = int(character.gold) + move
    _set_meta(character, mp)
    cap = bank_safe_capacity(character)
    return True, f"Снято <b>{move}</b> 💰. В сейфе: <b>{bal - move}</b> / {cap}."


def try_bank_safe_upgrade(character: Any) -> tuple[bool, str]:
    """Платёж из кошелька; +500 к вместимости за уровень."""
    cost = bank_safe_upgrade_cost_gold(character)
    g = int(character.gold)
    if g < cost:
        return False, f"Нужно {cost} 💰 для улучшения."
    mp = _meta(character)
    lv = bank_safe_capacity_level(character)
    mp[META_BANK_SAFE_LEVEL] = lv + 1
    character.gold = g - cost
    _set_meta(character, mp)
    new_cap = bank_safe_capacity(character)
    return True, f"Хранилище <b>+1</b> уровень (−{cost} 💰). Вместимость: <b>{new_cap}</b> 💰."


def bank_seal_active(character: Any) -> bool:
    return bool(_meta(character).get(META_BANK_SEAL, False))


def bank_interest_rate_per_hour(character: Any) -> float:
    return BANK_RATE_PER_HOUR_SEAL if bank_seal_active(character) else BANK_RATE_PER_HOUR_BASE


def bank_interest_cap_pct(character: Any) -> float:
    return BANK_INTEREST_CAP_PCT_SEAL if bank_seal_active(character) else BANK_INTEREST_CAP_PCT_BASE


def bank_pending_interest(character: Any) -> int:
    return max(0, int(_meta(character).get(META_BANK_INTEREST_PENDING, 0) or 0))


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_iso(s: Any) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s))
    except (TypeError, ValueError):
        return None


def accrue_bank_interest(character: Any, *, now_dt: datetime | None = None) -> int:
    """Начислить накопленные проценты по обычному вкладу. Возвращает добавленное в pending."""
    bal = bank_safe_balance(character)
    if bal <= 0:
        mp = _meta(character)
        if META_BANK_INTEREST_AT in mp:
            mp[META_BANK_INTEREST_AT] = _now_iso()
            _set_meta(character, mp)
        return 0
    now = now_dt or datetime.now(UTC)
    mp = _meta(character)
    last = _parse_iso(mp.get(META_BANK_INTEREST_AT))
    if last is None:
        mp[META_BANK_INTEREST_AT] = now.isoformat()
        _set_meta(character, mp)
        return 0
    hours = max(0.0, (now - last).total_seconds() / 3600.0)
    if hours < 0.5:
        return 0
    rate = bank_interest_rate_per_hour(character)
    cap_pct = bank_interest_cap_pct(character)
    pending = float(mp.get(META_BANK_INTEREST_PENDING, 0) or 0)
    cap_gold = bal * cap_pct
    if pending >= cap_gold:
        mp[META_BANK_INTEREST_AT] = now.isoformat()
        _set_meta(character, mp)
        return 0
    add = bal * rate * hours
    new_pending = min(cap_gold, pending + add)
    delta = int(new_pending) - int(pending)
    mp[META_BANK_INTEREST_PENDING] = new_pending
    mp[META_BANK_INTEREST_AT] = now.isoformat()
    _set_meta(character, mp)
    return max(0, delta)


def claim_bank_interest_to_wallet(character: Any) -> tuple[bool, str]:
    """Забрать накопленные проценты в кошелёк. Возвращает результат."""
    accrue_bank_interest(character)
    p = bank_pending_interest(character)
    if p <= 0:
        return False, "Проценты ещё не накопились."
    mp = _meta(character)
    mp[META_BANK_INTEREST_PENDING] = 0
    _set_meta(character, mp)
    character.gold = int(character.gold) + p
    return True, f"Получено <b>{p}</b> 💰 процентами. Накопление сброшено."


def try_unlock_bank_seal(character: Any) -> tuple[bool, str]:
    if bank_seal_active(character):
        return False, "Банковская печать уже активна."
    cost = BANK_SEAL_UPGRADE_COST
    if int(character.gold) < cost:
        return False, f"Нужно {cost} 💰 для апгрейда."
    mp = _meta(character)
    mp[META_BANK_SEAL] = True
    _set_meta(character, mp)
    character.gold = int(character.gold) - cost
    return True, "Банковская печать активирована: ставка и шапка процентов выше."


# ---- Срочный вклад ----

def bank_term_state(character: Any) -> dict[str, Any] | None:
    raw = _meta(character).get(META_BANK_TERM)
    if not isinstance(raw, dict):
        return None
    return raw


def bank_term_matures_at(state: dict[str, Any]) -> datetime | None:
    started = _parse_iso(state.get("started_at_iso"))
    if started is None:
        return None
    try:
        h = int(state.get("term_h") or 0)
    except (TypeError, ValueError):
        return None
    if h <= 0:
        return None
    from datetime import timedelta

    return started + timedelta(hours=h)


def try_open_bank_term(character: Any, *, amount: int, term_h: int) -> tuple[bool, str]:
    if bank_term_state(character) is not None:
        return False, "У тебя уже есть срочный вклад. Сначала закрой его."
    rate = next((r for h, r in BANK_TERM_OPTIONS if int(h) == int(term_h)), None)
    if rate is None:
        return False, "Неизвестный срок вклада."
    amt = max(0, int(amount))
    if amt < 100:
        return False, "Минимальная сумма вклада — 100 💰."
    bal = bank_safe_balance(character)
    if bal < amt:
        return False, f"В сейфе только {bal} 💰 — недостаточно для вклада {amt}."
    mp = _meta(character)
    mp[META_BANK_SAFE_BALANCE] = bal - amt
    mp[META_BANK_TERM] = {
        "amount": amt,
        "started_at_iso": _now_iso(),
        "term_h": int(term_h),
        "rate": float(rate),
    }
    _set_meta(character, mp)
    left = bank_safe_balance(character)
    return True, (
        f"Открыт срочный вклад на <b>{amt}</b> 💰 ({term_h}ч, ставка {rate*100:.0f}%). "
        f"В сейфе осталось свободно: <b>{left}</b> 💰."
    )


def try_close_bank_term(character: Any, *, force_early: bool = False) -> tuple[bool, str]:
    st = bank_term_state(character)
    if st is None:
        return False, "Срочного вклада нет."
    matures = bank_term_matures_at(st)
    now = datetime.now(UTC)
    matured = matures is not None and now >= matures
    amt = max(0, int(st.get("amount") or 0))
    rate = float(st.get("rate") or 0.0)
    interest = int(amt * rate) if matured else 0
    payout = amt + interest
    cap = bank_safe_capacity(character)
    bal = bank_safe_balance(character)
    space = cap - bal
    if payout > space:
        # излишек уходит в кошелёк
        to_safe = max(0, space)
        to_wallet = payout - to_safe
    else:
        to_safe = payout
        to_wallet = 0
    mp = _meta(character)
    if to_safe > 0:
        mp[META_BANK_SAFE_BALANCE] = bal + to_safe
    if to_wallet > 0:
        character.gold = int(character.gold) + to_wallet
    mp.pop(META_BANK_TERM, None)
    _set_meta(character, mp)
    if matured:
        return True, (
            f"Срочный вклад закрыт: тело <b>{amt}</b> + проценты <b>{interest}</b> 💰. "
            f"В сейф: {to_safe}, в кошелёк: {to_wallet}."
        )
    if not force_early:
        return False, "Вклад ещё не созрел. Подтверди досрочное закрытие."
    return True, (
        f"Досрочное закрытие: возвращено только тело <b>{amt}</b> 💰 "
        f"(в сейф: {to_safe}, в кошелёк: {to_wallet})."
    )


def format_lottery_outcome_ru(code: str, ticket: int, gold_delta: int, rune_delta: int) -> str:
    """Текст исхода; gold_delta — уже с учётом оплаты билета."""
    if code == "blank":
        return f"Билет пустой. Потрачено <b>{ticket}</b> 💰."
    if code == "small_win":
        back = ticket + gold_delta
        return f"Скромный приз: из <b>{ticket}</b> 💰 возвращено <b>{back}</b> (итого <b>{gold_delta:+d}</b> 💰)."
    if code == "nice_win":
        return f"Удачный билет! К чистому балансу <b>{gold_delta:+d}</b> 💰 (билет {ticket})."
    if code == "rune_pair":
        return (
            f"Удача в камнях: <b>{gold_delta:+d}</b> 💰 и <b>+{rune_delta}</b> рунных камней "
            f"(билет {ticket})."
        )
    if code == "jackpot":
        return f"🎰 <b>Джекпот!</b> К кошельку <b>{gold_delta:+d}</b> 💰 после билета {ticket}."
    return "Розыгрыш завершён."
