"""
/status (и /profile) — карточка героя: статы, полоски UI.
"""

from __future__ import annotations

import html
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale, set_locale, t
from config import settings
from db.models.character import Character
from db.repository import character_repo, inventory_repo, user_repo
from bot.keyboards.menu_kb import main_menu_keyboard
from bot.keyboards.profile_kb import (
    profile_full_stats_keyboard,
    profile_view_keyboard,
)
from bot.utils.game_ui import push_game_ui
from services import character_service, class_arc_service, leaderboard_service, stat_bonus_service, title_service
from services.rest_service import (
    apply_completed_rest_if_needed,
    format_rest_status_line_html,
    try_begin_or_claim_rest,
)
from game.characters import pets as pets_mod
from game.characters.classes import get_class_or_none
from game.characters.global_passives import format_unlocked_global_passives_ru, refresh_global_passives
from game.characters.path_ranks import path_rank_name_ru
from game.characters.progression import experience_needed_for_next_level
from game.characters.skills import passive_combat_modifiers_merged
from game.characters.titles import TITLE_BY_KEY, format_title_bonus_line
from game.characters.weapon_mastery import mastery_summary_line, weapon_type_from_item_data
from game.combat import formulas
from utils.game_images_prefs import game_images_enabled
from utils.profile_portraits import portrait_path_for_character
from utils.ui import (
    LINE_SEP,
    element_profile_line,
    format_number,
    render_exp_bar,
    render_hp_bar,
    render_mp_bar,
    render_stamina_bar,
)

router = Router(name="profile")


def clamp_profile_caption_for_photo(html: str, max_len: int = 1000) -> str:
    """Подпись к фото профиля (лимит Telegram ~1024)."""
    if len(html) <= max_len:
        return html
    cut = html[: max_len - 80]
    last_nl = cut.rfind("\n")
    if last_nl > max_len // 2:
        cut = cut[:last_nl]
    return (
        cut
        + "\n<i>…полный текст — кнопка «Полные характеристики» или /profile заново.</i>"
    )


def _stamina_minutes_hint(stamina: int, last_regen: datetime | None) -> int | None:
    """Минуты до +1 стамины; для подсказки только при нулевой стамине."""
    if stamina > 0:
        return None
    interval = max(1, settings.STAMINA_REGEN_INTERVAL)
    if last_regen is None:
        return max(1, interval // 60)
    now = datetime.now(UTC)
    last = last_regen
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    elapsed = max(0.0, (now - last).total_seconds())
    remainder = interval - (elapsed % interval)
    return max(1, int(remainder // 60))


async def _weapon_attack_value(session: AsyncSession, char: Character) -> int:
    return await character_service.equipped_weapon_attack_value(session, char)


def _fmt_stat_base_plus(base: int, extra: int) -> str:
    if extra <= 0:
        return str(int(base))
    return f"{int(base)} <i>(+{int(extra)})</i>"


def _build_profile_text(
    char: Character,
    *,
    compact: bool = True,
    weapon_attack: int,
    mastery_html: str = "",
    global_passives_line: str = "",
    gear_stat_bonus: dict[str, int] | None = None,
    title_stat_bonus: dict[str, int] | None = None,
    effective_stats: dict[str, int] | None = None,
    ranker_line: str = "",
) -> str:
    cls = get_class_or_none(char.class_key)
    if cls:
        class_title = f"{cls.emoji} {html.escape(cls.name_ru)}"
    else:
        class_title = html.escape(char.class_key)
    sub = class_arc_service.subclass_display_ru(char.subclass_key)
    if sub:
        class_title += f" · ⭐ {html.escape(sub)}"
    rank = path_rank_name_ru(char)
    rank_s = html.escape(rank) if rank else "—"
    title = html.escape(char.active_title) if char.active_title else "—"
    title_bonus = ""
    if not compact and char.active_title:
        k = title_service.active_title_key(char)
        if k and k in TITLE_BY_KEY:
            title_bonus = (
                f"\n<i>Титул: {html.escape(format_title_bonus_line(TITLE_BY_KEY[k]))}</i>"
            )

    xp_need = experience_needed_for_next_level(char.level, char.floor_number)
    st_hint = _stamina_minutes_hint(char.stamina, char.last_stamina_regen_at)

    gb = gear_stat_bonus or {k: 0 for k in ("str", "dex", "int", "vit", "luck")}
    tb = title_stat_bonus or {k: 0 for k in ("str", "dex", "int", "vit", "luck")}
    eff = effective_stats or {
        "str": int(char.stat_strength),
        "dex": int(char.stat_dexterity),
        "int": int(char.stat_intelligence),
        "vit": int(char.stat_vitality),
        "luck": int(char.stat_luck),
    }

    crit_pct = dodge_pct = 0.0
    dmg_lo = dmg_hi = 0
    if not compact:
        mods = passive_combat_modifiers_merged(char)
        crit_p = formulas.crit_chance_percent(
            int(eff["luck"]),
            crit_bonus_flat=float(mods.get("crit_bonus", 0.0)),
        )
        dodge_p = formulas.dodge_chance_percent(
            int(eff["dex"]),
            dodge_bonus_flat=float(mods.get("dodge_bonus", 0.0)),
        )
        dmg_lo, dmg_hi = formulas.physical_damage_range(
            int(eff["str"]),
            weapon_attack,
            0,
            elemental_bonus_percent=0,
        )
        crit_pct = round(crit_p * 100.0, 1)
        dodge_pct = round(dodge_p * 100.0, 1)

    gp_show = html.escape(global_passives_line) if global_passives_line.strip() else "—"

    gid_s = html.escape(str(int(char.game_id))) if char.game_id is not None else "—"
    lines = [
        LINE_SEP,
        f"🗡️ {html.escape(char.display_name)} · 🎮 <b>ID {gid_s}</b> • {class_title} • Ур.{char.level}",
        f"🎖️ Звание: <b>{rank_s}</b>",
    ]
    lines.append(f"🏆 Титул: {title}{title_bonus}")
    if ranker_line:
        lines.append(ranker_line)
    lines.append(f"🌐 Глобальные бонусы: <i>{gp_show}</i>")
    if not compact and mastery_html:
        lines.append(mastery_html)
    lines.append(LINE_SEP)
    lines.extend(
        [
            render_hp_bar(char.hp_current, char.hp_max),
            "",
            render_mp_bar(char.mp_current, char.mp_max),
            "",
            render_stamina_bar(
                char.stamina,
                settings.MAX_STAMINA,
                minutes_to_next=st_hint,
            ),
            "",
        ],
    )
    if not compact:
        lines.append(format_rest_status_line_html(char))
        lines.append("")
    lines.extend(
        [
            render_exp_bar(int(char.experience), xp_need),
            LINE_SEP,
            "📊 <b>Характеристики</b> <i>(база из героя; + с экипировки и титула)</i>",
            (
                f"⚔️ СИЛ: {_fmt_stat_base_plus(char.stat_strength, int(gb['str']) + int(tb['str']))}    "
                f"🏃 ЛОВ: {_fmt_stat_base_plus(char.stat_dexterity, int(gb['dex']) + int(tb['dex']))}"
            ),
            (
                f"🔮 ИНТ: {_fmt_stat_base_plus(char.stat_intelligence, int(gb['int']) + int(tb['int']))}     "
                f"🛡️ ВЫН: {_fmt_stat_base_plus(char.stat_vitality, int(gb['vit']) + int(tb['vit']))}"
            ),
            f"🍀 УДА: {_fmt_stat_base_plus(char.stat_luck, int(gb['luck']) + int(tb['luck']))}",
            LINE_SEP,
        ],
    )
    if not compact:
        lines.extend(
            [
                f"🗡️ Удар (физ.): <b>{dmg_lo}–{dmg_hi}</b>",
                f"💥 Крит: <b>{crit_pct}%</b>    💨 Уклонение: <b>{dodge_pct}%</b>",
                LINE_SEP,
            ],
        )
    unspent = int(getattr(char, "unspent_stat_points", 0) or 0)
    if unspent > 0:
        lines.append(
            f"✨ Свободных очков характеристик: <b>{unspent}</b> — /stats",
        )
    lines.extend(
        [
            element_profile_line(char.element),
            f"📍 Этаж: {char.floor_number} / 100 · открыто до: {int(char.highest_floor_reached)}",
            f"💰 Золото: {format_number(int(char.gold))}",
            f"⚗️ Рунные камни: {format_number(char.rune_stones)}",
        ],
    )
    return "\n".join(lines)


async def build_profile_html_async(session: AsyncSession, char: Character) -> str:
    refresh_global_passives(char)
    w_atk = await _weapon_attack_value(session, char)
    weapon = await inventory_repo.get_equipped_weapon(session, char.id)
    wtype = "unarmed" if weapon is None else weapon_type_from_item_data(weapon.item_data or {})
    mast = mastery_summary_line(char, wtype)
    gp = format_unlocked_global_passives_ru(char)
    gear_b, title_b = await stat_bonus_service.extra_stat_bonuses(session, char)
    eff = await stat_bonus_service.effective_primary_stats(session, char)
    loc = get_locale(char, None)
    rk = ""
    if await leaderboard_service.character_has_ranker_gold_bonus(session, char):
        rk = t(loc, "profile_ranker_line")
    base = _build_profile_text(
        char,
        compact=True,
        weapon_attack=w_atk,
        mastery_html=mast,
        global_passives_line=gp,
        gear_stat_bonus=gear_b,
        title_stat_bonus=title_b,
        effective_stats=eff,
        ranker_line=rk,
    )
    pet_blk = pets_mod.format_pet_profile_block_html(char, locale=loc)
    return f"{base}\n{LINE_SEP}\n{pet_blk}"


async def build_profile_full_stats_html_async(session: AsyncSession, char: Character) -> str:
    """Полные боевые и вспомогательные бонусы, передышка, урон/крит/уклонение."""
    refresh_global_passives(char)
    w_atk = await _weapon_attack_value(session, char)
    weapon = await inventory_repo.get_equipped_weapon(session, char.id)
    wtype = "unarmed" if weapon is None else weapon_type_from_item_data(weapon.item_data or {})
    mast = mastery_summary_line(char, wtype)
    gp = format_unlocked_global_passives_ru(char)
    gear_b, title_b = await stat_bonus_service.extra_stat_bonuses(session, char)
    eff = await stat_bonus_service.effective_primary_stats(session, char)
    loc = get_locale(char, None)
    rk = ""
    if await leaderboard_service.character_has_ranker_gold_bonus(session, char):
        rk = t(loc, "profile_ranker_line")
    base = _build_profile_text(
        char,
        compact=False,
        weapon_attack=w_atk,
        mastery_html=mast,
        global_passives_line=gp,
        gear_stat_bonus=gear_b,
        title_stat_bonus=title_b,
        effective_stats=eff,
        ranker_line=rk,
    )
    pet_blk = pets_mod.format_pet_profile_block_html(char, locale=loc)
    return f"{base}\n{LINE_SEP}\n{pet_blk}"


@router.message(Command("profile", "status", "профиль", "статус"))
async def cmd_profile(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Показать статус героя или попросить пройти регистрацию."""
    try:
        if message.from_user is None:
            return

        tg = message.from_user
        user = await user_repo.get_by_telegram_id(session, tg.id)
        if user is None or user.is_banned:
            await message.answer("Сначала нажми /start и создай героя.")
            return

        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Персонаж ещё не создан. Нажми /start и выбери класс.")
            return

        title_service.refresh_unlocks(char)
        apply_completed_rest_if_needed(char)
        await session.flush()
        loc = get_locale(char, message.from_user.language_code if message.from_user else None)
        text = await build_profile_html_async(session, char)
        p = portrait_path_for_character(char) if game_images_enabled(char) else None
        cap = clamp_profile_caption_for_photo(text) if p is not None else text
        await push_game_ui(
            state,
            message.bot,
            chat_id=message.chat.id,
            text=cap,
            reply_markup=profile_view_keyboard(char, locale=loc),
            fallback_message=message,
            photo_path=p,
        )
    except Exception:
        logger.exception("Ошибка в /status")
        try:
            await message.answer(
                "Не удалось открыть статус. Если недавно обновлял бота — "
                "перезапусти его; при повторении напиши админу.",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            logger.exception("Не удалось отправить сообщение об ошибке статуса")


@router.callback_query(F.data == "prf:full")
async def on_profile_full_stats(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        title_service.refresh_unlocks(char)
        apply_completed_rest_if_needed(char)
        await session.flush()
        text = await build_profile_full_stats_html_async(session, char)
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=profile_full_stats_keyboard(locale=loc),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer()
    except Exception:
        logger.exception("prf:full")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "prf:back")
async def on_profile_back_compact(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        title_service.refresh_unlocks(char)
        apply_completed_rest_if_needed(char)
        await session.flush()
        text = await build_profile_html_async(session, char)
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        p = portrait_path_for_character(char) if game_images_enabled(char) else None
        cap = clamp_profile_caption_for_photo(text) if p is not None else text
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=cap,
            reply_markup=profile_view_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=p,
        )
        await callback.answer()
    except Exception:
        logger.exception("prf:back")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "prf:rest")
async def on_profile_rest(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        title_service.refresh_unlocks(char)
        ok, payload = try_begin_or_claim_rest(char)
        await session.flush()
        text_compact = await build_profile_html_async(session, char)
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        p = portrait_path_for_character(char) if game_images_enabled(char) else None
        cap = clamp_profile_caption_for_photo(text_compact) if p is not None else text_compact
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=cap,
            reply_markup=profile_view_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=p,
        )
        await callback.answer(payload[:200], show_alert=not ok)
    except Exception:
        logger.exception("prf:rest")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "prf:pet")
async def on_profile_pet_cycle(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Смена активного питомца из статуса (если открыто больше одного)."""
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        own = pets_mod.owned_keys(char)
        if not own:
            await callback.answer()
            return
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        if len(own) < 2:
            disp = pets_mod.active_pet_display(char)
            await callback.answer(
                (disp or t(loc, "profile_pet_single_hint"))[:200],
                show_alert=True,
            )
            return
        disp = pets_mod.cycle_active_pet(char)
        await session.flush()
        title_service.refresh_unlocks(char)
        apply_completed_rest_if_needed(char)
        await session.flush()
        text_compact = await build_profile_html_async(session, char)
        p = portrait_path_for_character(char) if game_images_enabled(char) else None
        cap = clamp_profile_caption_for_photo(text_compact) if p is not None else text_compact
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=cap,
            reply_markup=profile_view_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=p,
        )
        await callback.answer((disp or "🐾")[:180], show_alert=False)
    except Exception:
        logger.exception("prf:pet")
        await callback.answer("Ошибка.", show_alert=True)


@router.message(Command("lang"))
async def cmd_lang(message: Message, session: AsyncSession, command: CommandObject) -> None:
    """Переключение языка меню: ru | en."""
    try:
        if message.from_user is None:
            return
        arg = (command.args or "").strip().lower()
        if arg not in ("ru", "en"):
            await message.answer(t("ru", "lang_usage"), parse_mode=ParseMode.HTML)
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None or user.is_banned:
            await message.answer("Нет доступа.")
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Сначала /start.")
            return
        set_locale(char, arg)
        await session.commit()
        await message.answer(
            t(arg, "lang_set", lang=arg.upper()),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(locale=arg),
        )
    except Exception:
        logger.exception("cmd_lang")
        await message.answer("Ошибка.")
