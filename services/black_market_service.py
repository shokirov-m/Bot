"""Глобальная витрина чёрного рынка и оплата входа."""

from __future__ import annotations

import random
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.app_global import AppGlobal
from db.models.character import Character
from game.mercenaries.constants import MARKET_ENTRY_COST_GOLD, MARKET_FLOOR, MARKET_MIN_LEVEL
from game.mercenaries.mercenary_data import random_black_market_lot_payload
from game.mercenaries.shadow_market_meta import (
    close_market_hub_session as _close_market_hub_session,
    first_market_entry_free_used,
    mark_first_market_entry_used,
    market_hub_session_open,
    open_market_hub_session,
)


PAYLOAD_KEY = "black_market_showcase_v2"


async def _ensure_app_row(session: AsyncSession) -> AppGlobal:
    row = await session.get(AppGlobal, 1)
    if row is None:
        row = AppGlobal(id=1, payload={})
        session.add(row)
        await session.flush()
    return row


def _iso_week_id(d: datetime | None = None) -> str:
    dt = d or datetime.now(tz=UTC)
    y, w, _ = dt.isocalendar()
    return f"{y}-W{w:02d}"


async def get_or_roll_showcase(session: AsyncSession) -> dict[str, Any]:
    row = await _ensure_app_row(session)
    payload = dict(row.payload or {})
    raw = payload.get(PAYLOAD_KEY)
    sm: dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}
    week = _iso_week_id()
    if sm.get("week_id") != week or not sm.get("lots"):
        rng = random.Random(sum(ord(c) for c in week))
        lots = []
        for i in range(6):
            lots.append(
                random_black_market_lot_payload(seed=rng.randint(1, 10_000_000), slot_index=i),
            )
        sm = {"week_id": week, "lots": lots}
        payload[PAYLOAD_KEY] = sm
        row.payload = payload
        flag_modified(row, "payload")
        await session.flush()
    return sm


def can_enter_market(character: Character) -> tuple[bool, str | None]:
    if int(character.level) < MARKET_MIN_LEVEL:
        return False, f"Нужен уровень {MARKET_MIN_LEVEL}+."
    if int(character.floor_number) != MARKET_FLOOR:
        return False, f"Рынок доступен только на {MARKET_FLOOR} этаже (после зачистки)."
    return True, None


async def try_pay_entry(session: AsyncSession, character: Character) -> tuple[bool, str]:
    ok, err = can_enter_market(character)
    if not ok:
        return False, err or "Нельзя."

    # Уже оплатил/вошёл в этой «сессии» — не списывать повторно при втором нажатии прохода
    if market_hub_session_open(character):
        return True, "Ты уже внутри рынка — пользуйся кнопками ниже или «К этажу», когда уйдёшь."

    if not first_market_entry_free_used(character):
        mark_first_market_entry_used(character)
        open_market_hub_session(character)
        await session.flush()
        return True, "Первый вход бесплатный. Жабс пропускает тебя с ухмылкой."

    cost = int(MARKET_ENTRY_COST_GOLD)
    if int(character.gold) < cost:
        return False, f"Нужно {cost} 💰 за вход."

    character.gold = int(character.gold) - cost
    open_market_hub_session(character)
    await session.flush()
    return True, f"−{cost} 💰 за вход. Ты проходишь под сводами рынка."


def close_market_hub_session(character: Character) -> None:
    _close_market_hub_session(character)


def format_hub_intro_html() -> str:
    return (
        "🌑 <b>Тени Башни — чёрный рынок</b>\n"
        "Здесь торгуют надеждами и клинками. Выбери место — или загляни к Жабсу за «лотами»."
    )
