"""Клавиатуры для клановой системы."""

from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.clan_service import (
    BUILDING_DEFS,
    RELIC_DEFS,
    can_manage,
    role_label,
)
from db.models.clan import Clan, ClanMembership
from db.models.character import Character


def _back_clan() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="◀️ Назад", callback_data="cln:hub")


def _menu_btn() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub")


# ─────────────────────────── Главный хаб (без клана) ────────────────────────

def clan_no_clan_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать клан", callback_data="cln:create")],
            [InlineKeyboardButton(text="🔍 Вступить по ID", callback_data="cln:join")],
            [_menu_btn()],
        ]
    )


# ─────────────────────────── Главный хаб (в клане) ──────────────────────────

def clan_hub_keyboard(role: str, war_status: str | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="📋 Карточка клана", callback_data="cln:info"),
            InlineKeyboardButton(text="👥 Участники", callback_data="cln:members"),
        ],
        [
            InlineKeyboardButton(text="💰 Казна", callback_data="cln:treasury"),
            InlineKeyboardButton(text="🔨 Постройки", callback_data="cln:blds"),
        ],
        [
            InlineKeyboardButton(text="✨ Реликвии", callback_data="cln:relics"),
            InlineKeyboardButton(text="🗺️ Захват этажей", callback_data="cln:cap"),
        ],
        [InlineKeyboardButton(text="⚔️ Войны", callback_data="cln:war")],
    ]
    if role in ("leader", "officer"):
        rows.append([InlineKeyboardButton(text="⚙️ Настройки клана", callback_data="cln:settings")])
    if role == "leader":
        rows.append([InlineKeyboardButton(text="👑 Панель лидера", callback_data="cln:panel")])
    rows.append([
        InlineKeyboardButton(text="🚪 Покинуть клан", callback_data="cln:leave"),
        _menu_btn(),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────── Карточка клана ─────────────────────────────────

def clan_info_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[_back_clan(), _menu_btn()]]
    )


# ─────────────────────────── Казна ──────────────────────────────────────────

def clan_treasury_keyboard(role: str, *, has_pending_salary: bool = False) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    rows.append([
        InlineKeyboardButton(text="💰 1 000", callback_data="cln:don:1000"),
        InlineKeyboardButton(text="💰 5 000", callback_data="cln:don:5000"),
        InlineKeyboardButton(text="💰 10 000", callback_data="cln:don:10000"),
    ])
    rows.append([
        InlineKeyboardButton(text="💰 50 000", callback_data="cln:don:50000"),
        InlineKeyboardButton(text="💰 Другая", callback_data="cln:don:custom"),
    ])
    rows.append([
        InlineKeyboardButton(text="🌿 Материалы", callback_data="cln:donate:mats"),
    ])
    if has_pending_salary:
        rows.append([
            InlineKeyboardButton(text="📥 Забрать ЗП", callback_data="cln:salary:claim"),
        ])
    if can_manage(role):
        rows.append([
            InlineKeyboardButton(text="💼 Выделить ЗП", callback_data="cln:salary:menu"),
        ])
    if role in ("leader",):
        rows.append([
            InlineKeyboardButton(text="⬆️ Повысить уровень клана", callback_data="cln:lvlup"),
        ])
    rows.append([_back_clan(), _menu_btn()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def clan_salary_menu_keyboard(
    members: list[tuple[int, str, str, int]]
) -> InlineKeyboardMarkup:
    """Меню распределения ЗП — список участников. members: [(char_id, name, role, pending)]."""
    rows: list[list[InlineKeyboardButton]] = []
    for cid, name, role, pending in members:
        prefix = "📌 " if pending > 0 else ""
        suffix = f" · ждёт {pending:,}💰" if pending > 0 else ""
        text_label = f"{prefix}{role_label(role).split(' ', 1)[0]} {name}{suffix}"
        rows.append([
            InlineKeyboardButton(
                text=text_label[:64],
                callback_data=f"cln:salary:pick:{cid}",
            )
        ])
    rows.append([
        InlineKeyboardButton(text="◀️ Назад в казну", callback_data="cln:treasury"),
        _menu_btn(),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def clan_salary_amount_keyboard(target_char_id: int) -> InlineKeyboardMarkup:
    cid = int(target_char_id)
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="+1 000", callback_data=f"cln:salary:add:{cid}:1000"),
            InlineKeyboardButton(text="+5 000", callback_data=f"cln:salary:add:{cid}:5000"),
            InlineKeyboardButton(text="+10 000", callback_data=f"cln:salary:add:{cid}:10000"),
        ],
        [
            InlineKeyboardButton(text="+50 000", callback_data=f"cln:salary:add:{cid}:50000"),
            InlineKeyboardButton(text="✏️ Другая", callback_data=f"cln:salary:custom:{cid}"),
        ],
        [
            InlineKeyboardButton(text="◀️ К списку", callback_data="cln:salary:menu"),
            _menu_btn(),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────── Постройки ──────────────────────────────────────

def clan_buildings_keyboard(
    payload: dict[str, Any], clan_level: int, role: str
) -> InlineKeyboardMarkup:
    from services.clan_service import _buildings, _has_building, check_and_complete_buildings
    check_and_complete_buildings(payload)
    blds = _buildings(payload)
    rows: list[list[InlineKeyboardButton]] = []
    for key, bdef in BUILDING_DEFS.items():
        bstate = blds.get(key) or {}
        if bstate.get("built"):
            label = f"✅ {bdef['name']}"
        elif bstate.get("build_until"):
            label = f"🔨 {bdef['name']} (строится)"
        elif clan_level < bdef["unlock_level"]:
            label = f"🔒 {bdef['name']}"
        else:
            label = f"⬜ {bdef['name']}"
        cb = f"cln:bld:{key}"
        rows.append([InlineKeyboardButton(text=label, callback_data=cb)])
    rows.append([_back_clan(), _menu_btn()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def clan_building_detail_keyboard(
    key: str, can_build: bool, role: str
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if can_build and can_manage(role):
        rows.append([
            InlineKeyboardButton(text="🔨 Построить", callback_data=f"cln:bld:{key}:build")
        ])
    rows.append([
        InlineKeyboardButton(text="◀️ К постройкам", callback_data="cln:blds"),
        _menu_btn(),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────── Реликвии ───────────────────────────────────────

def clan_relics_keyboard(
    payload: dict[str, Any], role: str, has_alchemy_lab: bool
) -> InlineKeyboardMarkup:
    from services.clan_service import _relics
    relics = _relics(payload)
    rows: list[list[InlineKeyboardButton]] = []
    if has_alchemy_lab and can_manage(role):
        for rk in RELIC_DEFS:
            if rk not in relics:
                rdef = RELIC_DEFS[rk]
                rows.append([
                    InlineKeyboardButton(
                        text=f"⚗️ Создать {rdef['name']}",
                        callback_data=f"cln:relic:craft:{rk}",
                    )
                ])
    rows.append([_back_clan(), _menu_btn()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────── Захват этажей ──────────────────────────────────

def clan_capture_keyboard(
    role: str,
    active_caps: dict[str, Any] | None = None,
    cap_limit: int = 2,
    page: int = 0,
    page_size: int = 12,
) -> InlineKeyboardMarkup:
    from services.clan_service import CAPTURABLE_FLOORS, _floor_capture_active
    from datetime import datetime, UTC
    rows: list[list[InlineKeyboardButton]] = []

    now = datetime.now(UTC)
    ac = active_caps or {}
    active_count = sum(1 for v in ac.values() if _floor_capture_active(v, now))

    # Пагинация по этажам
    total = len(CAPTURABLE_FLOORS)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    visible = CAPTURABLE_FLOORS[page * page_size:(page + 1) * page_size]

    if can_manage(role):
        row: list[InlineKeyboardButton] = []
        for fl in visible:
            fl_key = str(fl)
            if fl_key in ac and _floor_capture_active(ac[fl_key], now):
                label = f"✅ Эт.{fl}"
            elif active_count >= cap_limit:
                label = f"🔒 Эт.{fl}"
            else:
                label = f"⚔️ Эт.{fl}"
            row.append(InlineKeyboardButton(text=label, callback_data=f"cln:cap:{fl}"))
            if len(row) == 4:
                rows.append(row)
                row = []
        if row:
            rows.append(row)

        # Навигация по страницам
        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"cln:cap:pg:{page-1}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"cln:cap:pg:{page+1}"))
        if nav:
            rows.append(nav)

    rows.append([
        InlineKeyboardButton(
            text=f"📊 Захвачено: {active_count}/{cap_limit}",
            callback_data="cln:cap",
        ),
    ])
    rows.append([_back_clan(), _menu_btn()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────── Войны ──────────────────────────────────────────

def clan_war_keyboard(
    role: str, war_status: str | None
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if role == "leader":
        if war_status is None:
            rows.append([
                InlineKeyboardButton(text="⚔️ Объявить войну", callback_data="cln:war:decl")
            ])
        elif war_status == "incoming":
            rows.append([
                InlineKeyboardButton(text="✅ Принять", callback_data="cln:war:acc"),
                InlineKeyboardButton(text="❌ Отказать", callback_data="cln:war:rej"),
            ])
    rows.append([_back_clan(), _menu_btn()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────── Панель лидера ──────────────────────────────────

def clan_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Управление участниками", callback_data="cln:panel:members")],
            [InlineKeyboardButton(text="📋 Журнал событий", callback_data="cln:panel:log")],
            [_back_clan(), _menu_btn()],
        ]
    )


def clan_panel_members_keyboard(
    rows: list[tuple[ClanMembership, Character]],
    acting_id: int,
) -> InlineKeyboardMarkup:
    btns: list[list[InlineKeyboardButton]] = []
    for mbr, char in rows:
        if int(char.id) == acting_id or mbr.role == "leader":
            continue
        name_short = (char.display_name or "?")[:20]
        btns.append([
            InlineKeyboardButton(
                text=f"⚙️ {name_short} ({role_label(mbr.role)})",
                callback_data=f"cln:pm:{char.id}",
            )
        ])
    btns.append([
        InlineKeyboardButton(text="◀️ Панель", callback_data="cln:panel"),
        _menu_btn(),
    ])
    return InlineKeyboardMarkup(inline_keyboard=btns)


def clan_member_actions_keyboard(target_char_id: int, target_role: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    cid = target_char_id
    if target_role != "officer":
        rows.append([InlineKeyboardButton(text="⬆️ → Офицер", callback_data=f"cln:role:{cid}:officer")])
    if target_role != "veteran":
        rows.append([InlineKeyboardButton(text="🛡️ → Ветеран", callback_data=f"cln:role:{cid}:veteran")])
    if target_role != "member":
        rows.append([InlineKeyboardButton(text="🧑 → Рядовой", callback_data=f"cln:role:{cid}:member")])
    rows.append([InlineKeyboardButton(text="👑 Передать лидерство", callback_data=f"cln:transfer:{cid}")])
    rows.append([InlineKeyboardButton(text="🚫 Исключить", callback_data=f"cln:kick:{cid}")])
    rows.append([
        InlineKeyboardButton(text="◀️ К списку", callback_data="cln:panel:members"),
        _menu_btn(),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────── Подтверждения ──────────────────────────────────

def confirm_leave_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, покинуть", callback_data="cln:leave:yes"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cln:hub"),
            ]
        ]
    )


def confirm_levelup_keyboard(level: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"✅ Повысить до ур.{level}", callback_data="cln:lvlup:yes"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cln:treasury"),
            ]
        ]
    )


# ─────────────────────────── Участники (просмотр) ───────────────────────────

def clan_members_keyboard(role: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if role == "leader":
        rows.append([InlineKeyboardButton(text="👑 Управление", callback_data="cln:panel:members")])
    rows.append([_back_clan(), _menu_btn()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────── Браузер кланов ─────────────────────────────────

def clan_browse_keyboard(
    clans: list, page: int, total: int, page_size: int, in_clan: bool
) -> InlineKeyboardMarkup:
    """Список кланов с кнопками «Вступить» и пагинацией."""
    rows: list[list[InlineKeyboardButton]] = []
    for clan, cnt in clans:
        max_m_val = __import__("services.clan_service", fromlist=["max_members_for_level"]).max_members_for_level(int(clan.clan_level))
        tag_part = f"[{clan.tag}] " if clan.tag else ""
        label = f"{tag_part}{clan.name[:22]} Ур.{clan.clan_level} ({cnt}/{max_m_val})"
        if not in_clan and cnt < max_m_val:
            rows.append([InlineKeyboardButton(
                text=f"➕ {label}", callback_data=f"cln:join:{clan.id}"
            )])
        else:
            rows.append([InlineKeyboardButton(
                text=f"🔍 {label}", callback_data=f"cln:browse:view:{clan.id}"
            )])

    total_pages = max(1, (total + page_size - 1) // page_size)
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"cln:browse:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"cln:browse:{page + 1}"))
    if nav:
        rows.append(nav)

    if not in_clan:
        rows.append([
            InlineKeyboardButton(text="🆔 Вступить по ID", callback_data="cln:join:prompt"),
            InlineKeyboardButton(text="➕ Создать клан", callback_data="cln:create"),
        ])

    back_cb = "cln:hub" if in_clan else "cln:nohub"
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data=back_cb), _menu_btn()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def clan_no_hub_keyboard() -> InlineKeyboardMarkup:
    """Для незарегистрированного в клане — только Create/Browse/Menu."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать клан", callback_data="cln:create")],
            [InlineKeyboardButton(text="🔍 Найти и вступить", callback_data="cln:browse:0")],
            [InlineKeyboardButton(text="🆔 Вступить по ID", callback_data="cln:join:prompt")],
            [_menu_btn()],
        ]
    )


# ─────────────────────────── Настройки клана (для лидера/офицера) ───────────

def clan_settings_keyboard(role: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data="cln:set:desc")],
        [InlineKeyboardButton(text="💬 Ссылка на чат", callback_data="cln:set:chat")],
    ]
    if role == "leader":
        rows.insert(0, [InlineKeyboardButton(text="🏷️ Изменить тег", callback_data="cln:set:tag")])
        rows.insert(0, [InlineKeyboardButton(text="📛 Переименовать (5 000 💰)", callback_data="cln:set:name")])
    rows.append([_back_clan(), _menu_btn()])
    return InlineKeyboardMarkup(inline_keyboard=rows)
