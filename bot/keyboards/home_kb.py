"""Клавиатуры экрана «Дом» (5 уровней)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import t
from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character


def home_main_keyboard(character: Character, *, locale: str = "ru") -> InlineKeyboardMarkup:
    from services import home_service
    from services.rest_service import apply_completed_rest_if_needed, rest_seconds_left

    loc = locale if locale in ("ru", "en") else "ru"
    apply_completed_rest_if_needed(character)
    sec = rest_seconds_left(character)
    rest_txt = t(loc, "profile_rest_btn_wait", sec=sec) if sec > 0 else t(loc, "profile_rest_btn_start")

    rows: list[list[InlineKeyboardButton]] = []

    # Гардероб всегда
    rows.append([InlineKeyboardButton(text="🪞 Гардероб", callback_data="hom:ward")])
    if int(character.level) >= 15:
        rows.append([InlineKeyboardButton(text="🛏 Покои наёмников", callback_data="hom:merc_q")])
    # Передышка всегда
    rows.append([InlineKeyboardButton(text=rest_txt[:64], callback_data="hom:rest")])

    # Кнопка улучшения дома
    hl = home_service.home_level(character)
    cost_gold = home_service.next_home_upgrade_cost(character)
    cost_trophy = home_service.next_home_trophy_cost(character)
    if cost_gold is not None:
        trophy_part = f" + {cost_trophy}🏆" if cost_trophy > 0 else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🏡 Улучшить дом ({cost_gold:,}💰{trophy_part}) ур.{hl}→{hl+1}"[:64],
                    callback_data="hom:lvup",
                ),
            ],
        )

    # Библиотека (ур.4+)
    if home_service.can_access_library(character):
        h_left = home_service.library_hours_until_ready(character)
        lib_label = "🔬 Библиотека (+1 стат)" if h_left == 0 else f"🔬 Библиотека (~{int(h_left)}ч)"
        rows.append([InlineKeyboardButton(text=lib_label[:64], callback_data="hom:lib")])

    if home_service.is_mine_unlocked(character):
        rows.append(
            [InlineKeyboardButton(text="⛏ Шахта и Ферма", callback_data="hom:mine_menu")],
        )

    # Постройки (дом ур.2+); гача ресурсов — в Мастерской
    if home_service.can_access_workbench(character):
        rows.append([InlineKeyboardButton(text="🏗 Постройки", callback_data="hom:build")])

    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def library_keyboard(*, ready: bool) -> InlineKeyboardMarkup:
    """Меню библиотеки: выбор стата (если готова) или только «назад»."""
    rows: list[list[InlineKeyboardButton]] = []
    if ready:
        rows.append([
            InlineKeyboardButton(text="⚔️ Сила", callback_data="hom:lib:str"),
            InlineKeyboardButton(text="🏹 Ловкость", callback_data="hom:lib:dex"),
        ])
        rows.append([
            InlineKeyboardButton(text="🔮 Интеллект", callback_data="hom:lib:int"),
            InlineKeyboardButton(text="❤️ Тело", callback_data="hom:lib:vit"),
        ])
        rows.append([
            InlineKeyboardButton(text="🍀 Удача", callback_data="hom:lib:luck"),
        ])
    rows.append([InlineKeyboardButton(text="⬅ В дом", callback_data="hom:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wardrobe_keyboard(portrait_keys: list[str], *, current_key: str) -> InlineKeyboardMarkup:
    from utils.profile_portraits import portrait_label_ru

    rows: list[list[InlineKeyboardButton]] = []
    for pk in portrait_keys:
        ru = portrait_label_ru(pk)
        prefix = "✓ " if pk == current_key else ""
        label = f"{prefix}{ru}"
        if len(label) > 36:
            label = label[:33] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"hom:pv:{pk}"[:64],
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅ В дом", callback_data="hom:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def buildings_keyboard(character: Character) -> InlineKeyboardMarkup:
    """Вкладка построек: верстак и др. (алхимический стол убран — алхимик в мастерской)."""
    from services import home_service

    rows: list[list[InlineKeyboardButton]] = []
    if home_service.can_access_workbench(character):
        rows.append([InlineKeyboardButton(text="🛠 Верстак", callback_data="hom:bench")])
    rows.append([InlineKeyboardButton(text="⬅ В дом", callback_data="hom:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workbench_keyboard(*, can_upgrade: bool, back_cb: str = "hom:build") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if can_upgrade:
        rows.append(
            [InlineKeyboardButton(text="⬆ Улучшить верстак", callback_data="hom:wb:up")],
        )
    rows.append([InlineKeyboardButton(text="⬅ Постройки", callback_data=back_cb)])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def alchemy_keyboard(character: Character) -> InlineKeyboardMarkup:
    from services import home_service

    rows: list[list[InlineKeyboardButton]] = []
    tier = home_service.alchemy_tier(character)
    if tier < home_service.ALCHEMY_TIER_MAX:
        cost = home_service.ALCHEMY_UPGRADE_BASE_GOLD * max(1, tier)
        rows.append([InlineKeyboardButton(text=f"⬆ Улучшить стол ({cost:,}💰)", callback_data="hom:alch:up")])

    for key, edef in home_service.ELIXIRS.items():
        if tier < int(edef.get("tier", 1)):
            continue
        rows.append([
            InlineKeyboardButton(
                text=f"{edef['emoji']} Сварить: {edef['name']}",
                callback_data=f"hom:alch:brew:{key}",
            ),
        ])

    rows.append([
        InlineKeyboardButton(text="🔁 common→uncommon", callback_data="hom:alch:trans:common"),
    ])
    rows.append([
        InlineKeyboardButton(text="🔁 uncommon→rare", callback_data="hom:alch:trans:uncommon"),
    ])
    rows.append([
        InlineKeyboardButton(text="🔁 rare→epic", callback_data="hom:alch:trans:rare"),
    ])
    rows.append([
        InlineKeyboardButton(text="🔁 epic→legendary", callback_data="hom:alch:trans:epic"),
    ])
    rows.append([
        InlineKeyboardButton(text="🔁 legendary→mythic", callback_data="hom:alch:trans:legendary"),
    ])
    rows.append([InlineKeyboardButton(text="⬅ В дом", callback_data="hom:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def mine_farm_keyboard(character: Character) -> InlineKeyboardMarkup:
    from services import home_service
    rows: list[list[InlineKeyboardButton]] = []
    
    # Кнопка собрать, если шахта куплена
    if home_service.is_mine_bought(character):
        rows.append([InlineKeyboardButton(text="📦 Забрать ресурсы", callback_data="hom:mine_col")])
        
        # Улучшение или наем NPC
        if not home_service.is_npc_hired(character):
            rows.append([InlineKeyboardButton(text=f"👷 Нанять рабочего ({home_service.NPC_HIRE_GOLD:,}💰)", callback_data="hom:npc_hire")])
        
        up_cost = home_service.mine_upgrade_cost(character)
        if up_cost:
            rows.append([InlineKeyboardButton(text=f"⬆ Улучшить шахту ({up_cost:,}💰)", callback_data="hom:mine_up")])
            
        rows.append([InlineKeyboardButton(text="🍱 Тренировать питомцев", callback_data="hom:pet_train")])
    else:
        rows.append([InlineKeyboardButton(text=f"⛏ Расчистить шахту ({home_service.MINE_PURCHASE_GOLD:,}💰)", callback_data="hom:mine_buy")])
        
    rows.append([InlineKeyboardButton(text="⬅ В дом", callback_data="hom:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pet_training_keyboard(character: Character) -> InlineKeyboardMarkup:
    from game.characters import pets as pets_mod
    rows: list[list[InlineKeyboardButton]] = []
    
    owned = pets_mod.owned_keys(character)
    for pk in owned:
        d = pets_mod._all_defs().get(pk)
        if d:
            rows.append([InlineKeyboardButton(text=f"🍱 Покормить {d.name_ru}", callback_data=f"hom:pet_xp:{pk}")])
            
    rows.append([InlineKeyboardButton(text="⬅ В шахту", callback_data="hom:mine_menu")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wardrobe_preview_keyboard(portrait_key: str, *, is_current: bool) -> InlineKeyboardMarkup:
    pk = portrait_key[:48]
    rows: list[list[InlineKeyboardButton]] = []
    if is_current:
        rows.append([InlineKeyboardButton(text="✓ Надет", callback_data="hom:pvcur")])
    else:
        rows.append([InlineKeyboardButton(text="✅ Надеть", callback_data=f"hom:setp:{pk}"[:64])])
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data="hom:ward")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
