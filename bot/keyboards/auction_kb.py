"""Клавиатуры магазина (лоты игроков)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.auction_lot import AuctionLot
from db.models.character import Character
from game.items import item_categories
from game.items.equipment import RARITY_EMOJI, gear_icon_for_item_data
from utils.ui import LINE_SEP, format_number


def auction_portraits_screen_html(character: Character) -> str:
    """Экран покупки обликов профиля (раздел «Магазин» главного меню)."""
    import html

    from game.economy.shop import SHOP_PORTRAITS, effective_good_price

    fl = int(character.floor_number)
    lines = [
        "🖼 <b>Облики для профиля</b>",
        "<i>Покупка разблокирует портрет в <b>Дом → Гардероб</b>. PNG — в каталоге assets/images/profile.</i>",
        LINE_SEP,
        f"💰 Золото: <b>{int(character.gold):,}</b>",
        LINE_SEP,
        "<b>Товары:</b>",
    ]
    for g in SHOP_PORTRAITS:
        p = effective_good_price(g.price, fl)
        lines.append(
            f"{g.emoji} <b>{html.escape(g.name)}</b> — {p} 💰"
            f"{f' <i>(база {g.price})</i>' if p != g.price else ''}\n<i>{g.blurb}</i>",
        )
    return "\n".join(lines)


def auction_portraits_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    from game.economy.shop import SHOP_PORTRAITS, effective_good_price

    rows: list[list[InlineKeyboardButton]] = []
    fl = int(floor_number)
    for g in SHOP_PORTRAITS:
        price = effective_good_price(g.price, fl)
        label = f"{g.emoji} {g.name} — {price}💰"
        if len(label) > 64:
            label = label[:61] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"shp:buy:{fl}:{g.key}:a",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅ В магазин", callback_data="auc:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _rarity_emoji_from_item_data(item_data: dict | None) -> str:
    r = str((item_data or {}).get("rarity") or "common").lower()
    return RARITY_EMOJI.get(r, "⚪")


def auction_hub_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🖼 Облики профиля", callback_data="auc:prt")],
            [InlineKeyboardButton(text="📤 Выставить", callback_data="auc:create")],
            [
                InlineKeyboardButton(
                    text="🎯 Игроку по ID",
                    callback_data="auc:direct",
                ),
            ],
            [InlineKeyboardButton(text="🛒 Каталог", callback_data="auc:browse:0")],
            [InlineKeyboardButton(text="📋 Мои лоты", callback_data="auc:my")],
            menu_nav_button_row(),
        ],
    )


def auction_cancel_create_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="auc:hub")],
        ],
    )


def direct_offer_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Купить", callback_data=f"auc:dacc:{lot_id}"),
                InlineKeyboardButton(text="❌ Отказ", callback_data=f"auc:ddec:{lot_id}"),
            ],
            [InlineKeyboardButton(text="🛒 Магазин", callback_data="auc:hub")],
            menu_nav_button_row(),
        ],
    )


def viewer_lot_keyboard(
    lot: AuctionLot,
    viewer_char_id: int,
    *,
    browse_page: int = 0,
    browse_cat: str = item_categories.BAG_CAT_ALL,
) -> InlineKeyboardMarkup:
    if int(lot.seller_char_id) == int(viewer_char_id):
        return lot_seller_keyboard(lot.id)
    if lot.target_char_id is not None:
        if int(lot.target_char_id) == int(viewer_char_id):
            return direct_offer_keyboard(lot.id)
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ В магазин", callback_data="auc:hub")],
                menu_nav_button_row(),
            ],
        )
    return lot_buy_keyboard(lot, browse_page=browse_page, browse_cat=browse_cat)


def auction_direct_bag_category_row(*, selected: str) -> list[InlineKeyboardButton]:
    """Категории сумки при личном предложении."""
    opts = [
        (item_categories.BAG_CAT_ALL, "Все"),
        (item_categories.BAG_CAT_EQUIP, "⚔️ Экип"),
        (item_categories.BAG_CAT_USE, "🧪 Расх."),
        (item_categories.BAG_CAT_OTHER, "📦 Прочее"),
    ]
    row: list[InlineKeyboardButton] = []
    for code, label in opts:
        mark = f"·{label}" if code == selected else label
        row.append(InlineKeyboardButton(text=mark[:12], callback_data=f"auc:directbag:{code}"))
    return row


def bag_slots_for_direct_offer_keyboard(
    slots_with_items: list[tuple[int, str]],
    *,
    bag_cat: str = item_categories.BAG_CAT_ALL,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    rows.append(auction_direct_bag_category_row(selected=bag_cat))
    row: list[InlineKeyboardButton] = []
    for slot, label in slots_with_items:
        row.append(InlineKeyboardButton(text=label[:40], callback_data=f"auc:dpick:{slot}"))
        if len(row) >= 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Отмена", callback_data="auc:hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def auction_bag_category_row(*, selected: str) -> list[InlineKeyboardButton]:
    """Фильтр предметов при выставлении (короткие callback_data)."""
    opts = [
        (item_categories.BAG_CAT_ALL, "Все"),
        (item_categories.BAG_CAT_EQUIP, "⚔️ Экип"),
        (item_categories.BAG_CAT_USE, "🧪 Расх."),
        (item_categories.BAG_CAT_OTHER, "📦 Прочее"),
    ]
    row: list[InlineKeyboardButton] = []
    for code, label in opts:
        mark = f"·{label}" if code == selected else label
        row.append(InlineKeyboardButton(text=mark[:12], callback_data=f"auc:create:{code}"))
    return row


def bag_slots_for_auction_keyboard(
    slots_with_items: list[tuple[int, str]],
    *,
    bag_cat: str = item_categories.BAG_CAT_ALL,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    rows.append(auction_bag_category_row(selected=bag_cat))
    row: list[InlineKeyboardButton] = []
    for slot, label in slots_with_items:
        row.append(InlineKeyboardButton(text=label[:40], callback_data=f"auc:pick:{slot}"))
        if len(row) >= 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="auc:hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def auction_browse_category_keyboard(*, page: int, selected: str) -> list[InlineKeyboardButton]:
    opts = [
        (item_categories.BAG_CAT_ALL, "Все"),
        (item_categories.BAG_CAT_EQUIP, "⚔️"),
        (item_categories.BAG_CAT_USE, "🧪"),
        (item_categories.BAG_CAT_OTHER, "📦"),
    ]
    return [
        InlineKeyboardButton(
            text=("·" + label) if code == selected else label,
            callback_data=f"auc:browse:{page}:{code}",
        )
        for code, label in opts
    ]


def auction_lots_page_keyboard(
    lots: list[AuctionLot],
    *,
    page: int,
    total: int,
    page_size: int,
    category: str = item_categories.BAG_CAT_ALL,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    rows.append(auction_browse_category_keyboard(page=page, selected=category))
    for lot in lots:
        idata = lot.item_data if isinstance(lot.item_data, dict) else None
        gi = gear_icon_for_item_data(idata)
        em = _rarity_emoji_from_item_data(idata)
        name = str((idata or {}).get("name", f"Лот #{lot.id}"))[:9]
        p = format_number(int(lot.start_price))
        btn = f"#{lot.id} {gi}{em} {name} · {p}💰"
        rows.append(
            [
                InlineKeyboardButton(
                    text=btn[:64],
                    callback_data=f"auc:lot:{lot.id}:{page}:{category}",
                ),
            ],
        )
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"auc:browse:{page - 1}:{category}"))
    max_page = max(0, (total - 1) // page_size)
    if page < max_page:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"auc:browse:{page + 1}:{category}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅️ В магазин", callback_data="auc:hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def lot_buy_keyboard(
    lot: AuctionLot,
    *,
    browse_page: int = 0,
    browse_cat: str = item_categories.BAG_CAT_ALL,
) -> InlineKeyboardMarkup:
    p = int(lot.start_price)
    ptxt = format_number(p)
    em = _rarity_emoji_from_item_data(lot.item_data if isinstance(lot.item_data, dict) else None)
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=f"{em} 🛒 Купить {ptxt}💰"[:64],
                callback_data=f"auc:buy:{lot.id}:{browse_page}:{browse_cat}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="⬅️ К каталогу",
                callback_data=f"auc:browse:{browse_page}:{browse_cat}",
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def lot_seller_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛑 Снять лот", callback_data=f"auc:cnl:{lot_id}"),
                InlineKeyboardButton(text="💠 Новая цена", callback_data=f"auc:repr:{lot_id}"),
            ],
            [InlineKeyboardButton(text="⬅️ Мои лоты", callback_data="auc:my")],
            menu_nav_button_row(),
        ],
    )


def auction_reprice_cancel_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data=f"auc:lot:{lot_id}:0:{item_categories.BAG_CAT_ALL}")],
        ],
    )


def auction_my_lots_keyboard(active_lots: list[tuple[int, int, str]] | None = None) -> InlineKeyboardMarkup:
    """active_lots: (lot_id, start_price, rarity_emoji) для активных лотов."""
    rows: list[list[InlineKeyboardButton]] = []
    if active_lots:
        for row in active_lots[:8]:
            lid = int(row[0])
            price = int(row[1])
            em = str(row[2]) if len(row) >= 3 else "⚪"
            ptxt = format_number(price)
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"⚙️#{lid} {em} · {ptxt}💰"[:64],
                        callback_data=f"auc:lot:{lid}:0:{item_categories.BAG_CAT_ALL}",
                    ),
                ],
            )
    rows.append([InlineKeyboardButton(text="⬅️ В магазин", callback_data="auc:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
