"""Экран «Дом»: гардероб, верстак, алхимия, библиотека, улучшение."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.menu_kb import menu_nav_button_row
from bot.keyboards.home_kb import (
    alchemy_keyboard,
    buildings_keyboard,
    home_main_keyboard,
    library_keyboard,
    mine_farm_keyboard,
    wardrobe_keyboard,
    wardrobe_preview_keyboard,
    workbench_keyboard,
)
from bot.i18n import get_locale
from utils.media.game_art import menu_home_library_photo_path, menu_home_photo_path, menu_home_wardrobe_photo_path
from utils.telegram.game_ui import push_game_ui, push_game_ui_animation, push_game_ui_video
from db.repository import character_repo, mercenary_repo, user_repo
from scheduler.tasks import schedule_rest_completion_notification
import services.progression.home_service as home_service
import services.social.mercenary_service as mercenary_service
from game.mercenaries.shadow_market_meta import (
    floor_26_shadow_cleared,
    get_merc_xp_share_percent,
    get_party_merc_ids,
    roster_collection_cap,
    set_merc_xp_share_percent,
    set_party_merc_ids,
)
from game.core.paths import assets_root, data_root
from services.progression.rest_service import try_begin_or_claim_rest

router = Router(name="home")

MERC_ROMANCE_DATA_PATH = data_root() / "merc_quarters_romance_ru.json"
MERC_ROMANCE_ASSETS_DIR = assets_root() / "home" / "merc_quarters" / "romance"
# Портреты наёмников (карточка наёмника + меню «Покои»).
MERC_PORTRAITS_DIR = assets_root() / "home" / "merc_quarters" / "portraits"
# Следующий индекс варианта по ключу "merc_id:interaction_id" (цикл при «Повторить»).
MERC_ROM_VARIANT_CYCLE_KEY = "merc_rom_variant_cycle"

_MERC_ROM_INTERACTION_RE = re.compile(r"^hom:merc:rom:(\d+):([a-zA-Z0-9_\-]+)(?::l)?$")


def _adult_allowed(user) -> bool:
    return bool(getattr(user, "adult_age_declared", None)) is True and bool(getattr(user, "adult_content_enabled", None)) is True


def _merc_romance_allowed(user) -> bool:
    """18+ в покоях: согласие в настройках и контент не запечатан."""
    from game.mercenaries.adult_content_seal import merc_adult_content_sealed

    return _adult_allowed(user) and not merc_adult_content_sealed()


async def _answer_merc_romance_denied(callback: CallbackQuery) -> None:
    from game.mercenaries.adult_content_seal import merc_adult_content_sealed, merc_adult_seal_alert_text

    if merc_adult_content_sealed():
        await callback.answer(merc_adult_seal_alert_text(), show_alert=True)
    else:
        await callback.answer("🔞 Включи 18+ в настройках.", show_alert=True)


_FEMALE_NAMES = frozenset({"Лира", "Мира", "Сильва", "Найра", "Эйва", "Тесс", "Инга"})


def _merc_is_female(m) -> bool:
    ex = dict(getattr(m, "extra", None) or {})
    g = str(ex.get("gender") or "").strip().lower()
    if g in ("female", "f", "woman", "girl"):
        return True
    if g in ("male", "m", "man", "boy"):
        return False
    # fallback heuristic: known female names
    nm = str(getattr(m, "display_name", "") or "").strip()
    return nm in _FEMALE_NAMES


def _merc_portrait_path(m) -> str | None:
    ex = dict(getattr(m, "extra", None) or {})
    fn = str(ex.get("portrait") or "").strip()
    if not fn:
        return None
    return str(MERC_PORTRAITS_DIR / fn)


def _merc_key(m) -> str:
    ex = dict(getattr(m, "extra", None) or {})
    return str(ex.get("merc_key") or "").strip()


def _load_merc_romance_data() -> dict:
    if not MERC_ROMANCE_DATA_PATH.is_file():
        return {}
    try:
        raw = json.loads(MERC_ROMANCE_DATA_PATH.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        logger.exception("merc romance data load failed")
        return {}


def _format_interaction_lines(lines: list[str], *, merc_name: str) -> str:
    safe_name = html.escape(merc_name)
    out = []
    for ln in lines:
        try:
            out.append(str(ln).format(name=safe_name))
        except Exception:
            out.append(str(ln))
    return "\n".join(out)


def _romance_single_variant_from_item(it: dict) -> dict:
    lines = it.get("lines")
    lines_f = [x for x in (lines or []) if isinstance(x, str)]
    return {
        "title": str(it.get("title") or "Взаимодействие").strip(),
        "media_type": str(it.get("media_type") or "photo").strip().lower(),
        "media": str(it.get("media") or "").strip(),
        "aff_delta": int(it.get("aff_delta", 0) or 0),
        "lines": lines_f,
    }


def _romance_variants_for_interaction(it: dict, *, merc_key: str = "") -> list[dict]:
    """Несколько вариантов сцены.

    Поддерживает:
    - variants: общий набор
    - per_merc[merc_key]: переопределение (variants/title/media/aff_delta/lines) под конкретную наёмницу
    """
    mk = str(merc_key or "").strip()
    base = dict(it)
    per = base.get("per_merc")
    if mk and isinstance(per, dict):
        override = per.get(mk)
        if isinstance(override, dict):
            merged = dict(base)
            merged.update(dict(override))
            base = merged

    raw = base.get("variants")
    if isinstance(raw, list) and raw:
        parent = _romance_single_variant_from_item(base)
        out: list[dict] = []
        for v in raw:
            if not isinstance(v, dict):
                continue
            vl = v.get("lines")
            lines_f = [x for x in (vl or []) if isinstance(x, str)] if isinstance(vl, list) else []
            if not lines_f:
                lines_f = list(parent["lines"])
            aff = parent["aff_delta"]
            if "aff_delta" in v:
                aff = int(v.get("aff_delta") or 0)
            out.append(
                {
                    "title": str(v.get("title") or parent["title"]).strip(),
                    "media_type": str(v.get("media_type") or parent["media_type"]).strip().lower(),
                    "media": str(v.get("media") or parent["media"]).strip(),
                    "aff_delta": aff,
                    "lines": lines_f,
                },
            )
        return out if out else [_romance_single_variant_from_item(base)]
    return [_romance_single_variant_from_item(base)]


def _romance_interaction_kb(mid: int, iid: str, *, from_merc_list: bool = False) -> InlineKeyboardMarkup:
    suf = ":l" if from_merc_list else ""
    if from_merc_list:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Повторить", callback_data=f"hom:merc:rom:{mid}:{iid}{suf}")],
                [
                    InlineKeyboardButton(text="⬅ К действиям", callback_data=f"hom:merc:roml:{mid}"),
                    InlineKeyboardButton(text="⬅ Наёмницы", callback_data="hom:merc:rom18"),
                ],
                [InlineKeyboardButton(text="⬅ Покои", callback_data="hom:merc_q")],
                menu_nav_button_row(),
            ],
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Повторить", callback_data=f"hom:merc:rom:{mid}:{iid}{suf}")],
            [InlineKeyboardButton(text="⬅ К наёмнице", callback_data=f"hom:merc:det:{mid}")],
            [InlineKeyboardButton(text="⬅ К списку", callback_data="hom:merc_q")],
            menu_nav_button_row(),
        ],
    )


def _romance_menu_kb(mid: int, items: list[dict], *, from_merc_list: bool = False) -> InlineKeyboardMarkup:
    suf = ":l" if from_merc_list else ""
    rows: list[list[InlineKeyboardButton]] = []
    for it in items[:10]:
        iid = str(it.get("id") or "").strip()
        lbl = str(it.get("label") or "").strip()
        if not iid or not lbl:
            continue
        rows.append([InlineKeyboardButton(text=lbl[:64], callback_data=f"hom:merc:rom:{mid}:{iid}{suf}")])
    if from_merc_list:
        rows.append([InlineKeyboardButton(text="⬅ К списку наёмниц", callback_data="hom:merc:rom18")])
    else:
        rows.append([InlineKeyboardButton(text="⬅ К наёмнице", callback_data=f"hom:merc:det:{mid}")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _merc_female_romance_list_keyboard(mercs: list) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for mi, m in enumerate(mercs, start=1):
        name = str(m.display_name).replace("\n", " ")[:28]
        if len(name) >= 28:
            name = name[:25] + "…"
        rows.append([
            InlineKeyboardButton(
                text=f"{mi}. 🔥 {name}",
                callback_data=f"hom:merc:roml:{m.id}",
            ),
        ])
    rows.append([InlineKeyboardButton(text="⬅ Покои", callback_data="hom:merc_q")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _romance_apply_affection(m, delta: int) -> int:
    ex = dict(getattr(m, "extra", None) or {})
    cur = int(ex.get("romance_aff", 0) or 0)
    cur = max(0, cur + int(delta))
    ex["romance_aff"] = cur
    m.extra = ex
    try:
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(m, "extra")
    except Exception:
        pass
    return cur


async def _char(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user is None:
        return None
    user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
    if user is None or getattr(user, "is_banned", False):
        return None
    return await character_repo.get_by_user_id(session, user.id)


# ---------------------------------------------------------------------------
# Главный экран дома
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "hom:hub")
async def home_hub(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_home_main_html(char),
            reply_markup=home_main_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:hub")
        await callback.answer("Ошибка.", show_alert=True)


# ---------------------------------------------------------------------------
# Гардероб
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "hom:mine_col")
async def home_mine_collect(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = await home_service.collect_mine_farm_rewards(session, char)
        if not ok:
            await callback.answer(msg[:200], show_alert=True)
            return
        
        await session.flush()
        text = home_service.format_mine_farm_menu_html(char) + f"\n\n✅ {msg}"
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=mine_farm_keyboard(char),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Собрано!")
    except Exception:
        logger.exception("hom:mine_col")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "hom:mine_menu")
async def home_mine_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if not home_service.is_mine_unlocked(char):
            await callback.answer("Шахта откроется на ур. 4 дома.", show_alert=True)
            return

        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_mine_farm_menu_html(char),
            reply_markup=mine_farm_keyboard(char),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:mine_menu")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "hom:mine_buy")
async def home_mine_buy(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = home_service.try_buy_mine(char)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        await session.flush()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_mine_farm_menu_html(char) + f"\n\n{msg}",
            reply_markup=mine_farm_keyboard(char),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Поздравляем!")
    except Exception:
        logger.exception("hom:mine_buy")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "hom:npc_hire")
async def home_npc_hire(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = home_service.try_hire_npc(char)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        await session.flush()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_mine_farm_menu_html(char) + f"\n\n{msg}",
            reply_markup=mine_farm_keyboard(char),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Рабочий нанят!")
    except Exception:
        logger.exception("hom:npc_hire")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "hom:mine_up")
async def home_mine_upgrade(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = home_service.try_upgrade_mine(char)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        await session.flush()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_mine_farm_menu_html(char) + f"\n\n{msg}",
            reply_markup=mine_farm_keyboard(char),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Улучшено!")
    except Exception:
        logger.exception("hom:mine_up")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "hom:pet_train")
async def home_pet_train(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        from bot.keyboards.home_kb import pet_training_keyboard
        from game.characters import pets as pets_mod
        
        mp, st = pets_mod._pets_meta(char)
        treats = int(st.get("treats") or 0)
        
        text = (
            "🍱 <b>Тренировка питомцев</b>\n\n"
            f"Запас корма: <b>{treats}</b> ед.\n"
            "Потрать 1 ед. корма, чтобы дать питомцу <b>+50 XP</b>. "
            "Корм добывается на ферме (ур. 4 дома).\n\n"
            "Выбери питомца для кормления:"
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=pet_training_keyboard(char),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:pet_train")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:pet_xp:"))
async def home_pet_xp(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        pet_key = callback.data.removeprefix("hom:pet_xp:").strip()
        
        ok, msg = home_service.try_feed_pet_for_xp(char, pet_key)
        await session.flush()
        
        from game.characters import pets as pets_mod
        from bot.keyboards.home_kb import pet_training_keyboard
        mp, st = pets_mod._pets_meta(char)
        treats = int(st.get("treats") or 0)
        
        text = (
            "🍱 <b>Тренировка питомцев</b>\n\n"
            f"Запас корма: <b>{treats}</b> ед.\n"
            f"<i>{msg}</i>\n\n"
            "Выбери питомца для кормления:"
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=pet_training_keyboard(char),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Приятного аппетита!" if ok else msg[:180], show_alert=not ok)
    except Exception:
        logger.exception("hom:pet_xp")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "hom:ward")
async def home_wardrobe(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        from utils.media.profile_portraits import META_PORTRAIT_KEY

        mp = char.meta_progress or {}
        cur = str(mp.get(META_PORTRAIT_KEY) or "")
        keys = home_service.wardrobe_all_selectable_keys(char)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_wardrobe_html(char),
            reply_markup=wardrobe_keyboard(keys, current_key=cur),
            target_message=callback.message,
            photo_path=menu_home_wardrobe_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:ward")
        await callback.answer("Ошибка.", show_alert=True)


# ---------------------------------------------------------------------------
# Передышка
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "hom:rest")
async def home_rest(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        ok, payload, rest_until = try_begin_or_claim_rest(char)
        await session.flush()
        if ok and rest_until is not None:
            schedule_rest_completion_notification(
                callback.bot,
                chat_id=callback.message.chat.id,
                telegram_id=callback.from_user.id,
                until=rest_until,
            )
        loc = get_locale(char, callback.from_user.language_code)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_home_main_html(char),
            reply_markup=home_main_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer(payload[:200], show_alert=not ok)
    except Exception:
        logger.exception("hom:rest")
        await callback.answer("Ошибка.", show_alert=True)


# ---------------------------------------------------------------------------
# Улучшение уровня дома
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "hom:lvup")
async def home_level_upgrade(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        # Считаем трофеев в сумке (если нужны)
        trophy_count = 0
        trophy_needed = home_service.next_home_trophy_cost(char)
        if trophy_needed > 0:
            from db.repository import inventory_repo
            from game.items.materials import total_boss_trophies_in_bag
            bag_items = await inventory_repo.list_bag_items(session, char.id)
            trophy_count = total_boss_trophies_in_bag(bag_items)

        ok, msg, trophies_to_consume = home_service.try_upgrade_home_level(char, trophy_count)

        # Списываем трофеи из сумки
        if ok and trophies_to_consume > 0:
            from db.repository import inventory_repo
            bag_items = await inventory_repo.list_bag_items(session, char.id)
            remaining = trophies_to_consume
            for it in bag_items:
                if remaining <= 0:
                    break
                d = it.item_data or {}
                if str(d.get("kind")) == "boss_trophy":
                    cnt = max(1, int(d.get("count", 1)))
                    if cnt <= remaining:
                        remaining -= cnt
                        await session.delete(it)
                    else:
                        d["count"] = cnt - remaining
                        it.item_data = d
                        remaining = 0

        await session.flush()
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        body = home_service.format_home_main_html(char) + (f"\n\n{msg}" if ok else f"\n\n<i>{msg}</i>")
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=body,
            reply_markup=home_main_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Готово!" if ok else msg[:180], show_alert=not ok)
    except Exception:
        logger.exception("hom:lvup")
        await callback.answer("Ошибка.", show_alert=True)


# ---------------------------------------------------------------------------
# Библиотека (ур.4+)
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "hom:lib")
async def home_library(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if not home_service.can_access_library(char):
            await callback.answer("Библиотека откроется на ур. 4 дома.", show_alert=True)
            return
        ready = home_service.library_hours_until_ready(char) == 0
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_library_html(char),
            reply_markup=library_keyboard(ready=ready),
            target_message=callback.message,
            photo_path=menu_home_library_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:lib")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:lib:"))
async def home_library_apply(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        stat_key = callback.data.removeprefix("hom:lib:").strip()
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        ok, msg = home_service.try_use_library(char, stat_key)
        await session.flush()
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        ready = home_service.library_hours_until_ready(char) == 0
        body = home_service.format_library_html(char) + f"\n\n{msg}"
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=body,
            reply_markup=library_keyboard(ready=ready),
            target_message=callback.message,
            photo_path=menu_home_library_photo_path(),
            character=char,
        )
        await callback.answer("Готово!" if ok else msg[:180], show_alert=not ok)
    except Exception:
        logger.exception("hom:lib:stat")
        await callback.answer("Ошибка.", show_alert=True)


# ---------------------------------------------------------------------------
# Портреты
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "hom:pvcur")
async def home_portrait_already_equipped(callback: CallbackQuery) -> None:
    await callback.answer("Этот облик уже надет.", show_alert=True)


@router.callback_query(F.data.startswith("hom:pv:"))
async def home_portrait_preview(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        pk = callback.data.removeprefix("hom:pv:").strip()
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if pk not in home_service.wardrobe_all_selectable_keys(char):
            await callback.answer("Этот облик недоступен.", show_alert=True)
            return
        from utils.media.profile_portraits import META_PORTRAIT_KEY, portrait_path_if_exists

        mp = char.meta_progress or {}
        cur = str(mp.get(META_PORTRAIT_KEY) or "")
        caption = home_service.portrait_preview_caption_html(char, pk)
        img = portrait_path_if_exists(pk)
        extra = "\n\n⚠️ <i>Изображение для этого облика пока не загружено.</i>" if img is None else ""
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=caption + extra,
            reply_markup=wardrobe_preview_keyboard(pk, is_current=(pk == cur)),
            target_message=callback.message,
            photo_path=str(img) if img is not None else None,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:pv")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:setp:"))
async def home_set_portrait(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        pk = callback.data.removeprefix("hom:setp:").strip()
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = home_service.try_set_portrait_key(char, pk)
        await session.flush()
        if not ok:
            await callback.answer(msg[:180], show_alert=True)
            return
        from utils.media.profile_portraits import META_PORTRAIT_KEY

        mp = char.meta_progress or {}
        cur = str(mp.get(META_PORTRAIT_KEY) or "")
        keys = home_service.wardrobe_all_selectable_keys(char)
        body = home_service.format_wardrobe_html(char) + f"\n\n✅ {msg}"
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=body,
            reply_markup=wardrobe_keyboard(keys, current_key=cur),
            target_message=callback.message,
            photo_path=menu_home_wardrobe_photo_path(),
            character=char,
        )
        await callback.answer("Готово.")
    except Exception:
        logger.exception("hom:setp")
        await callback.answer("Ошибка.", show_alert=True)


# ---------------------------------------------------------------------------
# Постройки, гача, мастерская из дома
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "hom:build")
async def home_buildings(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if not home_service.can_access_workbench(char):
            await callback.answer("Постройки откроются на ур. 2 дома.", show_alert=True)
            return
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=(
                "🏗 <b>Постройки</b>\n\n"
                "🛠 <b>Верстак</b> — бонус к заточке в кузнице.\n"
                "<i>Ремесло — раздел «Локации» → «Мастерская».</i>"
            ),
            reply_markup=buildings_keyboard(char),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:build")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:gacha"))
async def home_gacha_deprecated(callback: CallbackQuery) -> None:
    """Старые кнопки «Гача» в доме — гача перенесена в Мастерскую."""
    await callback.answer(
        "Гача ресурсов перенесена в Мастерскую: меню → Мастерская → 🎰 Гача ресурсов.",
        show_alert=True,
    )


# ---------------------------------------------------------------------------
# Верстак
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "hom:bench")
async def home_workbench(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if not home_service.can_access_workbench(char):
            await callback.answer(
                "Верстак откроется на ур. 2 дома — улучши дом за золото.",
                show_alert=True,
            )
            return
        wt = home_service.workbench_tier(char)
        cost = home_service.upgrade_workbench_cost_gold(wt)
        can = cost is not None and int(char.gold) >= cost
        text = home_service.format_workbench_html(char)
        kb = workbench_keyboard(can_upgrade=can)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=kb,
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:bench")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "hom:wb:up")
async def home_workbench_upgrade(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = home_service.try_upgrade_workbench(char)
        await session.flush()
        wt = home_service.workbench_tier(char)
        cost = home_service.upgrade_workbench_cost_gold(wt)
        can_up = cost is not None and int(char.gold) >= int(cost)
        text = home_service.format_workbench_html(char) + (f"\n\n{msg}" if ok else f"\n\n<i>{msg}</i>")
        kb = workbench_keyboard(can_upgrade=can_up)
        if callback.bot is not None:
            await push_game_ui(
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=kb,
                target_message=callback.message,
                photo_path=menu_home_photo_path(),
                character=char,
            )
        if ok:
            await callback.answer("Улучшено!")
        else:
            await callback.answer(msg[:180], show_alert=True)
    except Exception:
        logger.exception("hom:wb:up")
        await callback.answer("Ошибка.", show_alert=True)


# ---------------------------------------------------------------------------
# Алхимия
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "hom:alch")
async def home_alchemy(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if not home_service.can_access_alchemy(char):
            await callback.answer(
                "Алхимия откроется на ур. 3 дома — сначала улучши дом.",
                show_alert=True,
            )
            return
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_alchemy_menu_html(char),
            reply_markup=alchemy_keyboard(char),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:alch")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "hom:alch:up")
async def home_alchemy_upgrade(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        await character_repo.lock_character_row(session, char.id)
        ok, msg = home_service.try_upgrade_alchemy(char)
        await session.flush()
        text = home_service.format_alchemy_menu_html(char) + (f"\n\n{msg}" if ok else f"\n\n<i>{msg}</i>")
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=alchemy_keyboard(char),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Улучшено!" if ok else msg[:180], show_alert=not ok)
    except Exception:
        logger.exception("hom:alch:up")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:alch:brew:"))
async def home_alchemy_brew(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if not home_service.can_access_alchemy(char):
            await callback.answer("Алхимия откроется на ур. 3 дома.", show_alert=True)
            return
        await character_repo.lock_character_row(session, char.id)
        elixir_key = callback.data.rsplit(":", 1)[-1]
        ok, msg = await home_service.try_brew_elixir(session, char, elixir_key)
        await session.flush()
        text = home_service.format_alchemy_menu_html(char) + (f"\n\n{msg}" if ok else f"\n\n<i>{msg}</i>")
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=alchemy_keyboard(char),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Сварено!" if ok else msg[:180], show_alert=not ok)
    except Exception:
        logger.exception("hom:alch:brew")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:alch:trans:"))
async def home_alchemy_transmute(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if not home_service.can_access_alchemy(char):
            await callback.answer("Алхимия откроется на ур. 3 дома.", show_alert=True)
            return
        await character_repo.lock_character_row(session, char.id)
        from_rarity = callback.data.rsplit(":", 1)[-1]
        ok, msg = await home_service.try_transmute_materials(session, char, from_rarity)
        await session.flush()
        text = home_service.format_alchemy_menu_html(char) + (f"\n\n{msg}" if ok else f"\n\n<i>{msg}</i>")
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=alchemy_keyboard(char),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Готово!" if ok else msg[:180], show_alert=not ok)
    except Exception:
        logger.exception("hom:alch:trans")
        await callback.answer("Ошибка.", show_alert=True)


def _merc_quarters_keyboard(character, mercs: list, *, user=None) -> InlineKeyboardMarkup:
    party = set(get_party_merc_ids(character))
    rows: list[list[InlineKeyboardButton]] = []
    for mi, m in enumerate(mercs, start=1):
        mark = "✅" if int(m.id) in party else "➕"
        label = f"{mi}.{mark}"[:6]
        name = str(m.display_name).replace("\n", " ")[:22]
        if len(name) >= 22:
            name = name[:19] + "…"
        rows.append([
            InlineKeyboardButton(
                text=f"{label} {name}",
                callback_data=f"hom:merc:det:{m.id}",
            ),
        ])
    if user is not None and _merc_romance_allowed(user) and any(_merc_is_female(m) for m in mercs):
        rows.append([InlineKeyboardButton(text="🔥 18+ (наёмницы)", callback_data="hom:merc:rom18")])
    xp = get_merc_xp_share_percent(character)
    rows.append([
        InlineKeyboardButton(
            text=("✓XP·20%" if xp == 20 else "XP·20%"),
            callback_data="hom:merc:xp:20",
        ),
        InlineKeyboardButton(
            text=("✓30%" if xp == 30 else "XP·30%"),
            callback_data="hom:merc:xp:30",
        ),
        InlineKeyboardButton(
            text=("✓40%" if xp == 40 else "XP·40%"),
            callback_data="hom:merc:xp:40",
        ),
    ])
    rows.append([InlineKeyboardButton(text="⬅ В дом", callback_data="hom:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _merc_detail_keyboard(character, m, *, user=None) -> InlineKeyboardMarkup:
    from game.mercenaries.constants import (
        MERC_GEAR_ARMOR_MAX,
        MERC_GEAR_BLADE_MAX,
        MERC_QUARTERS_GIFT_GOLD,
        MERC_TRAIN_GOLD,
        merc_gear_armor_upgrade_cost,
        merc_gear_blade_upgrade_cost,
    )

    rows: list[list[InlineKeyboardButton]] = []
    ph = mercenary_service.merc_work_phase(m)

    if ph == "idle":
        party = set(get_party_merc_ids(character))
        in_p = int(m.id) in party
        rows.append([
            InlineKeyboardButton(
                text=("✅ Убрать из отряда" if in_p else "➕ Взять в отряд"),
                callback_data=f"hom:merc:ptog:{m.id}",
            ),
        ])
    else:
        rows.append([
            InlineKeyboardButton(
                text="⏳ На подработке",
                callback_data=f"hom:merc:wx:{m.id}",
            ),
        ])

    tr_ok = mercenary_service.quarters_train_available_today(m)
    tr_txt = f"🎯 Тренировка {MERC_TRAIN_GOLD}💰" if tr_ok else "🎯 Уже бились"
    rows.append([InlineKeyboardButton(text=tr_txt[:64], callback_data=f"hom:merc:tr:{m.id}")])

    ex = dict(m.extra or {})
    b_lv = int(ex.get("gear_blade_lv", 0))
    a_lv = int(ex.get("gear_armor_lv", 0))
    if b_lv >= MERC_GEAR_BLADE_MAX:
        bbtn = InlineKeyboardButton(text="⚔ Клинок MAX", callback_data=f"hom:merc:gx:{m.id}")
    else:
        bc = merc_gear_blade_upgrade_cost(b_lv)
        bbtn = InlineKeyboardButton(text=f"⚔ Клинок+ {bc}💰", callback_data=f"hom:merc:gb:{m.id}")
    if a_lv >= MERC_GEAR_ARMOR_MAX:
        abtn = InlineKeyboardButton(text="🛡 Доспех MAX", callback_data=f"hom:merc:gx:{m.id}")
    else:
        ac = merc_gear_armor_upgrade_cost(a_lv)
        abtn = InlineKeyboardButton(text=f"🛡 Доспех+ {ac}💰", callback_data=f"hom:merc:ga:{m.id}")
    rows.append([bbtn, abtn])

    dlg_lbl = "💕 Свидание" if mercenary_service.quarters_dialog_available_today(m) else "💕 Завтра снова"
    gift_ok = mercenary_service.quarters_gift_available_today(m)
    gift_lbl = f"🎁 Подарок {MERC_QUARTERS_GIFT_GOLD}💰" if gift_ok else "🎁 Дарили сегодня"
    rows.append([
        InlineKeyboardButton(text=dlg_lbl[:64], callback_data=f"hom:merc:dlg:{m.id}"),
        InlineKeyboardButton(text=gift_lbl[:64], callback_data=f"hom:merc:gift:{m.id}"),
    ])

    # 18+ взаимодействия (только если включено и наёмница).
    if user is not None and _merc_romance_allowed(user) and _merc_is_female(m):
        rows.append([InlineKeyboardButton(text="🔥 18+ Взаимодействия", callback_data=f"hom:merc:rom:{m.id}")])

    if ph == "running":
        left = max(1, mercenary_service.merc_work_seconds_left(m) // 60)
        rows.append([
            InlineKeyboardButton(text=f"⏳ Ещё ~{left} мин", callback_data=f"hom:merc:wr:{m.id}"),
        ])
    elif ph == "ready":
        rows.append([InlineKeyboardButton(text="📥 Забрать зарплату", callback_data=f"hom:merc:wc:{m.id}")])
    else:
        rows.append([InlineKeyboardButton(text="💼 Подработка 2ч", callback_data=f"hom:merc:ws:{m.id}")])

    rows.append([InlineKeyboardButton(text="⬅ К списку", callback_data="hom:merc_q")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "hom:merc_q")
async def home_merc_quarters(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if int(char.level) < 15:
            await callback.answer("Покои откроются с 15 уровня.", show_alert=True)
            return
        from game.necromancer.service import is_necromancer, mercenaries_blocked_message

        if is_necromancer(char):
            await callback.answer(mercenaries_blocked_message(), show_alert=True)
            return
        mercs = await mercenary_repo.list_for_character(session, char.id)
        cap = roster_collection_cap(char)
        raw_party = get_party_merc_ids(char)
        by_id = {int(x.id): x for x in mercs}
        clean_party = [
            mid for mid in raw_party
            if (mm := by_id.get(int(mid))) is not None and not mercenary_service.merc_work_busy(mm)
        ]
        if clean_party != raw_party:
            set_party_merc_ids(char, clean_party)
            await session.flush()
        party_ids = get_party_merc_ids(char)
        unlocked = floor_26_shadow_cleared(char)
        hint = (
            "\n\n🌑 <i>Чёрный рынок доступен после зачистки 26 этажа.</i>"
            if not unlocked
            else ""
        )
        text = mercenary_service.format_quarters_html(char, mercs, cap=cap, party_ids=party_ids) + hint
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id) if callback.from_user else None
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_merc_quarters_keyboard(char, mercs, user=user),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:merc_q")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:merc:det:"))
async def home_merc_detail(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id) if callback.from_user else None
        mid = int(callback.data.rsplit(":", 1)[-1])
        m = await mercenary_repo.get_by_id(session, mid)
        if m is None or int(m.character_id) != int(char.id):
            await callback.answer("Нет такого наёмника.", show_alert=True)
            return
        party_ids = get_party_merc_ids(char)
        text = mercenary_service.format_merc_detail_html(m, party_ids=party_ids)
        pp = _merc_portrait_path(m) or menu_home_photo_path()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_merc_detail_keyboard(char, m, user=user),
            target_message=callback.message,
            photo_path=pp,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:merc:det")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "hom:merc:rom18")
async def home_merc_romance_list_hub(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None or callback.from_user is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if int(char.level) < 15:
            await callback.answer("Покои откроются с 15 уровня.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        if not _merc_romance_allowed(user):
            await _answer_merc_romance_denied(callback)
            return
        mercs = await mercenary_repo.list_for_character(session, char.id)
        females = [m for m in mercs if _merc_is_female(m)]
        if not females:
            await callback.answer("Нет наёмниц в ростере.", show_alert=True)
            return
        data = _load_merc_romance_data()
        if not list(data.get("interactions") or []):
            await callback.answer("Нет контента.", show_alert=True)
            return
        text = (
            "🔥 <b>18+ · наёмницы</b>\n\n"
            "<i>Выбери наёмницу — откроется меню взаимодействий.</i>"
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_merc_female_romance_list_keyboard(females),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:merc:rom18")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^hom:merc:roml:(\d+)$"))
async def home_merc_romance_menu_from_list(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None or callback.from_user is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        if not _merc_romance_allowed(user):
            await _answer_merc_romance_denied(callback)
            return
        mid = int(callback.data.rsplit(":", 1)[-1])
        m = await mercenary_repo.get_by_id(session, mid)
        if m is None or int(m.character_id) != int(char.id):
            await callback.answer("Нет такого наёмника.", show_alert=True)
            return
        if not _merc_is_female(m):
            await callback.answer("Раздел доступен только для наёмниц.", show_alert=True)
            return
        data = _load_merc_romance_data()
        items = list(data.get("interactions") or [])
        items = [x for x in items if isinstance(x, dict)]
        if not items:
            await callback.answer("Нет контента.", show_alert=True)
            return
        aff = int(dict(m.extra or {}).get("romance_aff", 0) or 0)
        text = (
            f"🛏 <b>Покои</b> · <b>{html.escape(m.display_name)}</b>\n"
            f"💞 Близость: <b>{aff}</b>\n\n"
            "<i>Выбери взаимодействие.</i>"
        )
        pp = _merc_portrait_path(m) or menu_home_photo_path()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_romance_menu_kb(mid, items, from_merc_list=True),
            target_message=callback.message,
            photo_path=pp,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:merc:roml")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^hom:merc:rom:(\d+)$"))
async def home_merc_romance_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None or callback.from_user is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        if not _merc_romance_allowed(user):
            await _answer_merc_romance_denied(callback)
            return
        mid = int(callback.data.rsplit(":", 1)[-1])
        m = await mercenary_repo.get_by_id(session, mid)
        if m is None or int(m.character_id) != int(char.id):
            await callback.answer("Нет такого наёмника.", show_alert=True)
            return
        if not _merc_is_female(m):
            await callback.answer("Раздел доступен только для наёмниц.", show_alert=True)
            return
        data = _load_merc_romance_data()
        items = list(data.get("interactions") or [])
        items = [x for x in items if isinstance(x, dict)]
        if not items:
            await callback.answer("Нет контента.", show_alert=True)
            return
        aff = int(dict(m.extra or {}).get("romance_aff", 0) or 0)
        text = (
            f"🛏 <b>Покои</b> · <b>{html.escape(m.display_name)}</b>\n"
            f"💞 Близость: <b>{aff}</b>\n\n"
            "<i>Выбери взаимодействие.</i>"
        )
        pp = _merc_portrait_path(m) or menu_home_photo_path()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_romance_menu_kb(mid, items, from_merc_list=False),
            target_message=callback.message,
            photo_path=pp,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:merc:rom menu")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.func(lambda d: bool(d and _MERC_ROM_INTERACTION_RE.match(d))))
async def home_merc_romance_interaction(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None or callback.from_user is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        if not _merc_romance_allowed(user):
            await _answer_merc_romance_denied(callback)
            return
        rm = _MERC_ROM_INTERACTION_RE.match(callback.data)
        if rm is None:
            await callback.answer()
            return
        mid = int(rm.group(1))
        iid = rm.group(2)
        from_merc_list = callback.data.endswith(":l")
        m = await mercenary_repo.get_by_id(session, mid)
        if m is None or int(m.character_id) != int(char.id):
            await callback.answer("Нет такого наёмника.", show_alert=True)
            return
        if not _merc_is_female(m):
            await callback.answer("Раздел доступен только для наёмниц.", show_alert=True)
            return
        data = _load_merc_romance_data()
        items = list(data.get("interactions") or [])
        items = [x for x in items if isinstance(x, dict)]
        by_id = {str(x.get("id") or ""): x for x in items}
        it = by_id.get(iid)
        if it is None:
            await callback.answer("Не найдено.", show_alert=True)
            return
        variants = _romance_variants_for_interaction(it, merc_key=_merc_key(m))
        nvar = len(variants)
        sdata = await state.get_data()
        cycle = dict(sdata.get(MERC_ROM_VARIANT_CYCLE_KEY) or {})
        sk = f"{mid}:{iid}"
        idx = int(cycle.get(sk, 0)) % nvar
        variant = variants[idx]
        cycle[sk] = (idx + 1) % nvar
        await state.update_data({MERC_ROM_VARIANT_CYCLE_KEY: cycle})

        lines = [x for x in variant.get("lines") or [] if isinstance(x, str)]
        body = _format_interaction_lines(lines, merc_name=str(m.display_name))
        delta = int(variant.get("aff_delta", 0) or 0)
        if delta:
            await mercenary_repo.get_by_id(session, mid)  # ensure loaded
            aff_now = _romance_apply_affection(m, delta)
            await session.commit()
        else:
            aff_now = int(dict(m.extra or {}).get("romance_aff", 0) or 0)
        title = str(variant.get("title") or "Взаимодействие").strip()
        text = f"💞 <b>{html.escape(title)}</b>\n\n{body}\n\n💞 Близость: <b>{aff_now}</b>"
        if nvar > 1:
            text += f"\n\n<i>Вариант {idx + 1} из {nvar}. «Повторить» — следующий вариант по кругу.</i>"

        media_type = str(variant.get("media_type") or "photo").strip().lower()
        media = str(variant.get("media") or "").strip()
        mk = _merc_key(m)
        if media:
            # Медиа храним отдельно по каждой наёмнице: romance/<merc_key>/<file>.
            # Если merc_key не задан — используем старую структуру romance/<file>.
            media_path = str((MERC_ROMANCE_ASSETS_DIR / mk / media) if mk else (MERC_ROMANCE_ASSETS_DIR / media))
        else:
            media_path = None
        kb = _romance_interaction_kb(mid, iid, from_merc_list=from_merc_list)

        if media_type == "animation" and media_path:
            await push_game_ui_animation(
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=kb,
                target_message=callback.message,
                animation_path=media_path,
            )
        elif media_type == "video" and media_path:
            await push_game_ui_video(
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=kb,
                target_message=callback.message,
                video_path=media_path,
            )
        else:
            await push_game_ui(
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=kb,
                target_message=callback.message,
                photo_path=media_path,
                character=char,
            )
        await callback.answer()
    except Exception:
        logger.exception("hom:merc:rom interaction")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:merc:dlg:"))
async def home_merc_dialog(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        mid = int(callback.data.rsplit(":", 1)[-1])
        m = await mercenary_repo.get_by_id(session, mid)
        if m is None or int(m.character_id) != int(char.id):
            await callback.answer("Нет такого наёмника.", show_alert=True)
            return
        ok, msg = mercenary_service.apply_quarters_dialog(m)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        await session.flush()
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id) if callback.from_user else None
        party_ids = get_party_merc_ids(char)
        text = mercenary_service.format_merc_detail_html(m, party_ids=party_ids) + f"\n\n{msg}"
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_merc_detail_keyboard(char, m, user=user),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Готово")
    except Exception:
        logger.exception("hom:merc:dlg")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:merc:gift:"))
async def home_merc_gift(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        mid = int(callback.data.rsplit(":", 1)[-1])
        m = await mercenary_repo.get_by_id(session, mid)
        if m is None or int(m.character_id) != int(char.id):
            await callback.answer("Нет такого наёмника.", show_alert=True)
            return
        ok, msg = await mercenary_service.apply_quarters_gift(session, char, m)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id) if callback.from_user else None
        party_ids = get_party_merc_ids(char)
        text = mercenary_service.format_merc_detail_html(m, party_ids=party_ids) + f"\n\n✅ {msg}"
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_merc_detail_keyboard(char, m, user=user),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Подарено")
    except Exception:
        logger.exception("hom:merc:gift")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:merc:tr:"))
async def home_merc_train(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        mid = int(callback.data.rsplit(":", 1)[-1])
        m = await mercenary_repo.get_by_id(session, mid)
        if m is None or int(m.character_id) != int(char.id):
            await callback.answer("Нет такого наёмника.", show_alert=True)
            return
        ok, msg = await mercenary_service.apply_merc_train(session, char, m)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        await session.commit()
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id) if callback.from_user else None
        party_ids = get_party_merc_ids(char)
        text = mercenary_service.format_merc_detail_html(m, party_ids=party_ids) + f"\n\n✅ {msg}"
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_merc_detail_keyboard(char, m, user=user),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Готово")
    except Exception:
        logger.exception("hom:merc:tr")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:merc:gb:"))
async def home_merc_gear_blade(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        mid = int(callback.data.rsplit(":", 1)[-1])
        m = await mercenary_repo.get_by_id(session, mid)
        if m is None or int(m.character_id) != int(char.id):
            await callback.answer("Нет такого наёмника.", show_alert=True)
            return
        ok, msg = await mercenary_service.upgrade_merc_gear_blade(session, char, m)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        await session.commit()
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id) if callback.from_user else None
        party_ids = get_party_merc_ids(char)
        text = mercenary_service.format_merc_detail_html(m, party_ids=party_ids) + f"\n\n✅ {msg}"
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_merc_detail_keyboard(char, m, user=user),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Усилено")
    except Exception:
        logger.exception("hom:merc:gb")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:merc:ga:"))
async def home_merc_gear_armor(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        mid = int(callback.data.rsplit(":", 1)[-1])
        m = await mercenary_repo.get_by_id(session, mid)
        if m is None or int(m.character_id) != int(char.id):
            await callback.answer("Нет такого наёмника.", show_alert=True)
            return
        ok, msg = await mercenary_service.upgrade_merc_gear_armor(session, char, m)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        await session.commit()
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id) if callback.from_user else None
        party_ids = get_party_merc_ids(char)
        text = mercenary_service.format_merc_detail_html(m, party_ids=party_ids) + f"\n\n✅ {msg}"
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_merc_detail_keyboard(char, m, user=user),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Усилено")
    except Exception:
        logger.exception("hom:merc:ga")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:merc:ws:"))
async def home_merc_work_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        mid = int(callback.data.rsplit(":", 1)[-1])
        m = await mercenary_repo.get_by_id(session, mid)
        if m is None or int(m.character_id) != int(char.id):
            await callback.answer("Нет такого наёмника.", show_alert=True)
            return
        ok, msg = await mercenary_service.start_merc_work_session(session, char, m)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id) if callback.from_user else None
        party_ids = get_party_merc_ids(char)
        text = mercenary_service.format_merc_detail_html(m, party_ids=party_ids) + f"\n\n✅ {msg}"
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_merc_detail_keyboard(char, m, user=user),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Ушёл на смену")
    except Exception:
        logger.exception("hom:merc:ws")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:merc:wc:"))
async def home_merc_work_claim(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        mid = int(callback.data.rsplit(":", 1)[-1])
        m = await mercenary_repo.get_by_id(session, mid)
        if m is None or int(m.character_id) != int(char.id):
            await callback.answer("Нет такого наёмника.", show_alert=True)
            return
        ok, msg = await mercenary_service.claim_merc_work_reward(session, char, m)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id) if callback.from_user else None
        party_ids = get_party_merc_ids(char)
        text = mercenary_service.format_merc_detail_html(m, party_ids=party_ids) + f"\n\n✅ {msg}"
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_merc_detail_keyboard(char, m, user=user),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Получено")
    except Exception:
        logger.exception("hom:merc:wc")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:merc:wr:"))
async def home_merc_work_remain(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.from_user is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        mid = int(callback.data.rsplit(":", 1)[-1])
        m = await mercenary_repo.get_by_id(session, mid)
        if m is None or int(m.character_id) != int(char.id):
            await callback.answer("Нет наёмника.", show_alert=True)
            return
        left = mercenary_service.merc_work_seconds_left(m) // 60
        await callback.answer(f"До конца смены ~{max(1, left)} мин.", show_alert=True)
    except Exception:
        logger.exception("hom:merc:wr")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:merc:wx:"))
async def home_merc_work_busy_hint(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        mid = int(callback.data.rsplit(":", 1)[-1])
        m = await mercenary_repo.get_by_id(session, mid)
        if m is None or int(m.character_id) != int(char.id):
            await callback.answer("Нет наёмника.", show_alert=True)
            return
        if mercenary_service.merc_work_phase(m) == "ready":
            await callback.answer("Сначала забери зарплату кнопкой ниже.", show_alert=True)
        else:
            left = mercenary_service.merc_work_seconds_left(m) // 60
            await callback.answer(f"На подработке. Осталось ~{max(1, left)} мин.", show_alert=True)
    except Exception:
        logger.exception("hom:merc:wx")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:merc:gx:"))
async def home_merc_gear_max_hint(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await callback.answer("Этот слот экипа уже на максимуме.", show_alert=True)


@router.callback_query(F.data.startswith("hom:merc:ptog:"))
async def home_merc_party_toggle_detail(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        mid = int(callback.data.rsplit(":", 1)[-1])
        m = await mercenary_repo.get_by_id(session, mid)
        if m is None or int(m.character_id) != int(char.id):
            await callback.answer("Нет такого наёмника.", show_alert=True)
            return
        if mercenary_service.merc_work_phase(m) != "idle":
            await callback.answer(
                "Пока наёмник на подработке — в отряд возьми после смены или забери зарплату.",
                show_alert=True,
            )
            return
        from game.necromancer.service import is_necromancer, mercenaries_blocked_message

        if is_necromancer(char):
            await callback.answer(mercenaries_blocked_message(), show_alert=True)
            return
        cur = list(get_party_merc_ids(char))
        if mid in cur:
            cur = [x for x in cur if int(x) != mid]
        else:
            cur.append(mid)
        set_party_merc_ids(char, cur)
        await session.flush()
        party_ids = get_party_merc_ids(char)
        text = mercenary_service.format_merc_detail_html(m, party_ids=party_ids)
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id) if callback.from_user else None
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_merc_detail_keyboard(char, m, user=user),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Отряд обновлён")
    except Exception:
        logger.exception("hom:merc:ptog")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:merc:xp:"))
async def home_merc_xp(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id) if callback.from_user else None
        pct = int(callback.data.rsplit(":", 1)[-1])
        set_merc_xp_share_percent(char, pct)
        await session.flush()
        mercs = await mercenary_repo.list_for_character(session, char.id)
        cap = roster_collection_cap(char)
        party_ids = get_party_merc_ids(char)
        text = mercenary_service.format_quarters_html(char, mercs, cap=cap, party_ids=party_ids)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text + f"\n\n✅ Доля опыта наёмников: <b>{pct}%</b> от твоего опыта за бой.",
            reply_markup=_merc_quarters_keyboard(char, mercs, user=user),
            target_message=callback.message,
            photo_path=menu_home_photo_path(),
            character=char,
        )
        await callback.answer("Сохранено")
    except Exception:
        logger.exception("hom:merc:xp")
        await callback.answer("Ошибка.", show_alert=True)
