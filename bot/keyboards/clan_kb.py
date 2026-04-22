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

def clan_treasury_keyboard(role: str) -> InlineKeyboardMarkup:
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
    if role in ("leader",):
        rows.append([
            InlineKeyboardButton(text="⬆️ Повысить уровень клана", callback_data="cln:lvlup"),
        ])
    rows.append([_back_clan(), _menu_btn()])
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

def clan_capture_keyboard(role: str) -> InlineKeyboardMarkup:
    from services.clan_service import CAPTURABLE_FLOORS
    rows: list[list[InlineKeyboardButton]] = []
    if can_manage(role):
        row: list[InlineKeyboardButton] = []
        for fl in CAPTURABLE_FLOORS:
            row.append(InlineKeyboardButton(
                text=f"⚔️ Эт.{fl}", callback_data=f"cln:cap:{fl}"
            ))
            if len(row) == 3:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
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
