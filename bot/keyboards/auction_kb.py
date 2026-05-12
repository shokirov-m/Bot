"""Клавиатуры магазина (лоты игроков)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.auction_lot import AuctionLot
from db.models.character import Character
from game.items import item_categories
from game.items.equipment import RARITY_EMOJI, gear_icon_for_item_data
from utils.ui import LINE_SEP, format_number


def auction_vip_portraits_screen_html(character: Character) -> str:
    """VIP-экран обликов за Telegram Stars."""
    import html as _html

    from game.economy.shop import VIP_STAR_GOODS
    from services import shop_service
    from services.home_service import has_portrait_unlock

    lines = [
        "⭐ <b>VIP-магазин — Облики профиля</b>",
        "<i>Уникальные облики за Telegram Stars. После покупки — в <b>Дом → Гардероб</b>.</i>",
        "<i>Нажми на облик — превью и кнопка покупки.</i>",
        LINE_SEP,
    ]
    for g in VIP_STAR_GOODS:
        vs = str(g.item_data.get("virtual_shop") or "")
        if vs == "vip_star_bonus":
            bid = str(g.item_data.get("vip_bonus_id") or "").strip()
            owned = shop_service.vip_bonus_owned(character, bid) if bid else False
        else:
            pk = str(g.item_data.get("portrait_key", ""))
            owned = bool(pk and has_portrait_unlock(character, pk))
        status = " ✅ <i>уже куплен</i>" if owned else f" — <b>{g.stars_price} ⭐</b>"
        lines.append(f"{g.emoji} <b>{_html.escape(g.name)}</b>{status}\n<i>{_html.escape(g.blurb)}</i>")
    return "\n".join(lines)


# Оставляем для обратной совместимости
def auction_portraits_screen_html(character: Character) -> str:
    return auction_vip_portraits_screen_html(character)


def auction_vip_portrait_preview_keyboard(
    floor_number: int,
    good_key: str,
    *,
    stars_price: int,
    already_owned: bool,
    buy_origin: str = "a",
) -> InlineKeyboardMarkup:
    """Предпросмотр VIP-облика: купить за Stars (если ещё нет) и назад."""
    fl = int(floor_number)
    gk = good_key.strip()[:32]
    bo = (buy_origin or "a").strip().lower()[:2]
    if bo not in ("a", "c", "f", "m", "h", "u"):
        bo = "a"
    rows: list[list[InlineKeyboardButton]] = []
    if not already_owned:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"⭐ Купить · {stars_price} Telegram Stars"[:64],
                    callback_data=f"shp:vbuy:{fl}:{gk}:{bo}",
                ),
            ],
        )
    else:
        rows.append(
            [InlineKeyboardButton(text="✅ Уже куплено", callback_data="auc:prvown")],
        )
    if bo == "a":
        back_cd = "auc:prt"
    else:
        back_cd = f"shp:vip:{fl}:{bo}"
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data=back_cd)])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


# Обратная совместимость
def auction_portrait_preview_keyboard(
    floor_number: int,
    good_key: str,
    *,
    price: int,
    already_owned: bool,
) -> InlineKeyboardMarkup:
    return auction_vip_portrait_preview_keyboard(
        floor_number, good_key, stars_price=price, already_owned=already_owned
    )


def auction_vip_portraits_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    """Список VIP-обликов за Stars — каждая кнопка ведёт на превью."""
    from game.economy.shop import VIP_STAR_GOODS

    rows: list[list[InlineKeyboardButton]] = []
    fl = int(floor_number)
    for g in VIP_STAR_GOODS:
        label = f"{g.emoji} {g.name} · {g.stars_price} ⭐"
        if len(label) > 64:
            label = label[:61] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"auc:vpr:{fl}:{g.key}:a",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅ В магазин", callback_data="auc:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


# Обратная совместимость
def auction_portraits_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    return auction_vip_portraits_keyboard(floor_number)


def _rarity_emoji_from_item_data(item_data: dict | None) -> str:
    r = str((item_data or {}).get("rarity") or "common").lower()
    return RARITY_EMOJI.get(r, "⚪")


def auction_hub_keyboard(floor_number: int = 1) -> InlineKeyboardMarkup:
    fl = max(1, int(floor_number))
    return InlineKeyboardMarkup(
        inline_keyboard=[
            # ── Обычный магазин ──
            [InlineKeyboardButton(
                text="🛒 Обычный магазин (золото)",
                callback_data=f"shp:main:{fl}:u",
            )],
            # ── VIP-магазин ──
            [InlineKeyboardButton(
                text="⭐ VIP-магазин (Telegram Stars)",
                callback_data="auc:prt",
            )],
            # ── Торговля между игроками ──
            [InlineKeyboardButton(text="📤 Выставить лот", callback_data="auc:create")],
            [InlineKeyboardButton(text="🎯 Предложить игроку", callback_data="auc:direct")],
            [InlineKeyboardButton(text="🛍 Каталог лотов", callback_data="auc:browse:0")],
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
