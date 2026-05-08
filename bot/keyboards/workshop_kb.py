"""Мастерская: inline-кнопки."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from game.items.equipment import RARITY_NAME_RU, item_kind_label_ru


def _wsp_dis_rarity_label(code: str) -> str:
    if code == "all":
        return "Все"
    return RARITY_NAME_RU.get(code, code)

if TYPE_CHECKING:
    from db.models.character import Character


def workshop_prof_hub_keyboard(profession: str) -> InlineKeyboardMarkup:
    """Хаб профессии: крафт + специализация (заточка / зачарование / руны)."""
    pk = str(profession).strip().lower()
    rows: list[list[InlineKeyboardButton]] = []
    if pk == "blacksmith":
        rows.append([InlineKeyboardButton(text="🔨 Крафт", callback_data=f"wsp:craft:{pk}")])
        rows.append([InlineKeyboardButton(text="✨ Заточка экипировки", callback_data="wsp:sharp:menu")])
        rows.append([InlineKeyboardButton(text="🔨 Разбор предметов", callback_data="wsp:brk:menu")])
    elif pk == "alchemist":
        rows.append([InlineKeyboardButton(text="🔨 Крафт", callback_data=f"wsp:craft:{pk}")])
        rows.append([InlineKeyboardButton(text="📜 Свитки зачарования", callback_data="wsp:ench:menu")])
    elif pk == "jeweler":
        rows.append([InlineKeyboardButton(text="🔨 Крафт", callback_data=f"wsp:craft:{pk}")])
        rows.append([InlineKeyboardButton(text="💎 Слияние рун", callback_data="wsp:rune:menu")])
        rows.append(
            [
                InlineKeyboardButton(text="⚔ Вставить руну (500💰)", callback_data="wsp:rsk"),
            ],
        )
        rows.append(
            [
                InlineKeyboardButton(text="🔓 Извлечь руну (500💰)", callback_data="wsp:rrx"),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅ Мастерская", callback_data="wsp:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workshop_main_keyboard(locale: str = "ru", *, character: "Character | None" = None) -> InlineKeyboardMarkup:
    _ = locale
    from services import home_service

    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="⚒️ Кузница", callback_data="wsp:prof:blacksmith"),
            InlineKeyboardButton(text="⚗️ Лаборатория", callback_data="wsp:prof:alchemist"),
        ],
        [
            InlineKeyboardButton(text="💎 Ювелирная", callback_data="wsp:prof:jeweler"),
        ],
    ]
    if character is not None and home_service.can_access_workbench(character):
        rows.append([InlineKeyboardButton(text="🎰 Гача ресурсов", callback_data="wsp:gacha")])
    rows.extend(
        [
            [
                InlineKeyboardButton(text="📜 Очередь / забрать", callback_data="wsp:queue"),
            ],
            [
                InlineKeyboardButton(text="🏆 Рейтинг мастеров", callback_data="wsp:lb"),
            ],
            [
                InlineKeyboardButton(text="📖 Справочник крафта", callback_data="wsp:cat:menu"),
            ],
            menu_nav_button_row(),
        ],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workshop_gacha_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="⚒ ×1", callback_data="wsp:gacha:pull:blacksmith"),
            InlineKeyboardButton(text="⚒ ×10", callback_data="wsp:gacha:pull10:blacksmith"),
        ],
        [
            InlineKeyboardButton(text="⚗ ×1", callback_data="wsp:gacha:pull:alchemist"),
            InlineKeyboardButton(text="⚗ ×10", callback_data="wsp:gacha:pull10:alchemist"),
        ],
        [
            InlineKeyboardButton(text="💎 ×1", callback_data="wsp:gacha:pull:jeweler"),
            InlineKeyboardButton(text="💎 ×10", callback_data="wsp:gacha:pull10:jeweler"),
        ],
        [InlineKeyboardButton(text="⬅ Мастерская", callback_data="wsp:hub")],
        menu_nav_button_row(),
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workshop_prof_keyboard(
    profession: str,
    *,
    page: int,
    recipe_rows: list[tuple[str, str]],
    total_count: int,
    per_page: int = 8,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for rid, label in recipe_rows[:per_page]:
        short = label if len(label) <= 40 else label[:37] + "…"
        rows.append([InlineKeyboardButton(text=short, callback_data=f"wsp:rcp:{profession}:{rid}")])
    max_page = max(0, (max(0, total_count) - 1) // per_page)
    p = max(0, min(int(page), max_page))
    nav: list[InlineKeyboardButton] = []
    if max_page > 0:
        if p > 0:
            nav.append(
                InlineKeyboardButton(text="◀", callback_data=f"wsp:craftpage:{profession}:{p - 1}"),
            )
        nav.append(InlineKeyboardButton(text=f"{p + 1}/{max_page + 1}", callback_data="wsp:noop"))
        if p < max_page:
            nav.append(
                InlineKeyboardButton(text="▶", callback_data=f"wsp:craftpage:{profession}:{p + 1}"),
            )
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅ К профессии", callback_data=f"wsp:prof:{profession}")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workshop_sharpen_slots_keyboard(rows_slots: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """rows_slots: (equip_slot, label)."""
    rows: list[list[InlineKeyboardButton]] = []
    for slot, lab in rows_slots[:12]:
        rows.append(
            [InlineKeyboardButton(text=lab[:58], callback_data=f"wsp:sharp:do:{slot}")],
        )
    rows.append([InlineKeyboardButton(text="⬅ К кузнице", callback_data="wsp:prof:blacksmith")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workshop_rune_tiers_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚗️ Две I → II (авто)",
                    callback_data="wsp:rune:auto12",
                ),
            ],
            [InlineKeyboardButton(text="↑ II (3× ранг I)", callback_data="wsp:rune:tier:2")],
            [InlineKeyboardButton(text="↑ III (4× ранг II)", callback_data="wsp:rune:tier:3")],
            [InlineKeyboardButton(text="↑ IV (5× ранг III)", callback_data="wsp:rune:tier:4")],
            [InlineKeyboardButton(text="↑ V (5× ранг IV)", callback_data="wsp:rune:tier:5")],
            [InlineKeyboardButton(text="⬅ К ювелиру", callback_data="wsp:prof:jeweler")],
            menu_nav_button_row(),
        ],
    )


def workshop_rune_bag_pick_keyboard(items: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for item_id, label in items[:14]:
        short = label if len(label) <= 36 else label[:33] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=short,
                    callback_data=f"wsp:rsk:{item_id}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅ К ювелиру", callback_data="wsp:prof:jeweler")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workshop_rune_socket_pick_keyboard(labels: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for idx, label in labels[:8]:
        rows.append(
            [
                InlineKeyboardButton(
                    text=label[:40],
                    callback_data=f"wsp:rrx:{idx}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅ К ювелиру", callback_data="wsp:prof:jeweler")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workshop_dis_bag_keyboard(
    items: list[tuple[int, str]],
    *,
    rarity_filter: str | None = None,
    kind_filter: str | None = None,
) -> InlineKeyboardMarkup:
    """Разбор в мастерской: те же фильтры, что у кузницы города."""
    rows: list[list[InlineKeyboardButton]] = []
    rar_btns: list[InlineKeyboardButton] = []
    for code in ("all", "common", "uncommon", "rare", "epic"):
        lab = _wsp_dis_rarity_label(code)
        sel = "✅ " if (rarity_filter or "all") == code else ""
        rar_btns.append(
            InlineKeyboardButton(
                text=f"{sel}{lab}",
                callback_data=f"wsp:brk:f:{code}:{kind_filter or 'all'}",
            ),
        )
    rows.append(rar_btns[:3])
    rows.append(rar_btns[3:])
    knd_btns: list[InlineKeyboardButton] = []
    for code, em in (
        ("all", ""),
        ("weapon", "🗡 "),
        ("armor", "🧥 "),
        ("shield", "🛡 "),
        ("ring", "💍 "),
        ("amulet", "📿 "),
    ):
        lab = "Все типы" if code == "all" else f"{em}{item_kind_label_ru(code)}"
        sel = "✅ " if (kind_filter or "all") == code else ""
        knd_btns.append(
            InlineKeyboardButton(
                text=f"{sel}{lab}",
                callback_data=f"wsp:brk:f:{rarity_filter or 'all'}:{code}",
            ),
        )
    rows.append(knd_btns[:3])
    rows.append(knd_btns[3:])
    for item_id, label in items[:12]:
        short = label if len(label) <= 38 else label[:35] + "…"
        rows.append([InlineKeyboardButton(text=short, callback_data=f"wsp:brk:x:{item_id}")])
    rows.append(
        [
            InlineKeyboardButton(text="🧹 Всё обычное", callback_data="wsp:brk:sw:common"),
            InlineKeyboardButton(text="🧹 До необыч. вкл.", callback_data="wsp:brk:sw:uncommon"),
        ],
    )
    rows.append([InlineKeyboardButton(text="⬅ К кузнице", callback_data="wsp:prof:blacksmith")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workshop_rune_elements_keyboard(target_rank: int) -> InlineKeyboardMarkup:
    from game.items.runes import ELEMENTS

    rows: list[list[InlineKeyboardButton]] = []
    line: list[InlineKeyboardButton] = []
    for el, meta in ELEMENTS.items():
        em = str(meta.get("emoji") or "💎")
        line.append(
            InlineKeyboardButton(
                text=f"{em}",
                callback_data=f"wsp:rune:do:{target_rank}:{el}",
            ),
        )
        if len(line) >= 4:
            rows.append(line)
            line = []
    if line:
        rows.append(line)
    rows.append([InlineKeyboardButton(text="⬅ К рангам", callback_data="wsp:rune:menu")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workshop_queue_keyboard(
    entries: list[tuple[str, str, bool]],
) -> InlineKeyboardMarkup:
    """ (slot_id, label, ready) """
    rows: list[list[InlineKeyboardButton]] = []
    for sid, lab, ready in entries:
        if ready:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=lab[:58],
                        callback_data=f"wsp:claim:{sid}",
                    ),
                ],
            )
        else:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=lab[:58],
                        callback_data="wsp:noop",
                    ),
                ],
            )
    if any(ready for _, _, ready in entries):
        rows.append(
            [InlineKeyboardButton(text="📥 Забрать всё готовое", callback_data="wsp:claimall")],
        )
    rows.append([InlineKeyboardButton(text="⬅ Мастерская", callback_data="wsp:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workshop_station_keyboard(profession: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔧 Улучшить станок",
                    callback_data=f"wsp:upg:{profession}",
                ),
            ],
            [InlineKeyboardButton(text="⬅ Назад", callback_data=f"wsp:prof:{profession}")],
            menu_nav_button_row(),
        ],
    )


def city_workshop_orders_keyboard(*, floor_number: int) -> InlineKeyboardMarkup:
    f = int(floor_number)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📜 Разместить заказ", callback_data=f"wso:new:{f}")],
            [InlineKeyboardButton(text="📋 Все заказы", callback_data=f"wso:list:{f}")],
            [InlineKeyboardButton(text="⬅ Город", callback_data=f"frg:city:{f}")],
            menu_nav_button_row(),
        ],
    )


def workshop_orders_list_keyboard(
    floor_number: int,
    rows: list[tuple[int, str, int]],
    *,
    crafter: bool,
) -> InlineKeyboardMarkup:
    """rows: (order_id, label, escrow)"""
    btns: list[list[InlineKeyboardButton]] = []
    for oid, lab, _ in rows[:10]:
        if crafter:
            btns.append(
                [
                    InlineKeyboardButton(
                        text=lab[:58],
                        callback_data=f"wso:take:{floor_number}:{oid}",
                    ),
                ],
            )
        else:
            btns.append(
                [
                    InlineKeyboardButton(
                        text=lab[:58],
                        callback_data=f"wso:noop:{oid}",
                    ),
                ],
            )
    btns.append([InlineKeyboardButton(text="⬅ Назад", callback_data=f"wso:open:{floor_number}")])
    btns.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=btns)
