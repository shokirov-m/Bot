"""Таверна: меню покупок."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from game.locations.tavern import tavern_offers_for_floor
from game.tower.progression import floor_data


def _city_anchor(city_anchor: int) -> int:
    return floor_data.normalize_city_callback_key(city_anchor)


def tavern_menu_keyboard(city_anchor: int) -> InlineKeyboardMarkup:
    floor_number = _city_anchor(city_anchor)
    rows: list[list[InlineKeyboardButton]] = []
    for o in tavern_offers_for_floor(floor_number):
        label = f"{o.emoji} {o.name} — {o.price}💰"
        if len(label) > 64:
            label = label[:61] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"tvr:buy:{floor_number}:{o.key}",
                ),
            ],
        )
    rows.append(
        [InlineKeyboardButton(text="📜 Дневные предложения", callback_data=f"tvr:daily:{floor_number}")],
    )
    rows.append(
        [InlineKeyboardButton(text="🪙 Скупщик Орин", callback_data=f"tvr:buyer:{floor_number}")],
    )
    rows.append(
        [InlineKeyboardButton(text="⬅ В город", callback_data=f"frg:city:{floor_number}")],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tavern_daily_keyboard(
    city_anchor: int,
    offers: dict,
    bought_blueprints: set[str],
    bought_gears: set[str],
    known_recipes: set[str],
) -> InlineKeyboardMarkup:
    floor_number = _city_anchor(city_anchor)
    rows: list[list[InlineKeyboardButton]] = []
    for rid, name, price in offers.get("blueprints", []):
        if rid in known_recipes:
            text = f"📜 {name} — известен"
            cd = f"tvr:daily:{floor_number}:nop"
        elif rid in bought_blueprints:
            text = f"✅ {name} (куплен)"
            cd = f"tvr:daily:{floor_number}:nop"
        else:
            text = f"📜 {name} — {price}💰"
            cd = f"tvr:daily:bp:{floor_number}:{rid}"
        if len(text) > 64:
            text = text[:61] + "…"
        rows.append([InlineKeyboardButton(text=text, callback_data=cd)])
    for key, idata, price in offers.get("gears", []):
        nm = str(idata.get("name", key))
        if key in bought_gears:
            text = f"✅ {nm} (куплено)"
            cd = f"tvr:daily:{floor_number}:nop"
        else:
            text = f"🛒 {nm} — {price}💰"
            cd = f"tvr:daily:gr:{floor_number}:{key}"
        if len(text) > 64:
            text = text[:61] + "…"
        rows.append([InlineKeyboardButton(text=text, callback_data=cd)])
    rows.append([InlineKeyboardButton(text="⬅ Таверна", callback_data=f"tvr:open:{floor_number}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def buyer_quest_keyboard(city_anchor: int, state: dict) -> InlineKeyboardMarkup:
    """Клавиатура экрана скупщика."""
    floor_number = _city_anchor(city_anchor)
    rows: list[list[InlineKeyboardButton]] = []

    if not state:
        rows.append([InlineKeyboardButton(
            text="🪙 Взяться за поручения",
            callback_data=f"tvr:bq:start:{floor_number}",
        )])
    else:
        final_claimed = state.get("final_claimed", False)
        if not final_claimed:
            for s in (1, 2, 3):
                if state.get(f"{s}_done") and not state.get(f"{s}_claimed"):
                    rows.append([InlineKeyboardButton(
                        text=f"✅ Сдать шаг {s}",
                        callback_data=f"tvr:bq:claim:{floor_number}:{s}",
                    )])
                    break
            if all(state.get(f"{s}_claimed") for s in (1, 2, 3)) and not final_claimed:
                rows.append([InlineKeyboardButton(
                    text="🏆 Получить финальный товар",
                    callback_data=f"tvr:bq:final:{floor_number}",
                )])

    rows.append([InlineKeyboardButton(text="⬅ Таверна", callback_data=f"tvr:open:{floor_number}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
