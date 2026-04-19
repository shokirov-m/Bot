"""
/status (и /profile) — карточка героя: статы, полоски UI.
"""

from __future__ import annotations

import html
import re
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
from bot.keyboards.city_market_kb import profile_skills_main_keyboard, profile_skills_pick_keyboard
from bot.keyboards.profile_kb import (
    profile_full_stats_keyboard,
    profile_pet_picker_keyboard,
    profile_view_keyboard,
)
from bot.utils.game_ui import push_game_ui
from services import character_service, leaderboard_service, profession_service, stat_bonus_service, title_service
from scheduler.tasks import schedule_rest_completion_notification
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
from game.characters.player_skills import (
    SKILL_BY_KEY,
    ensure_skill_meta,
    equipped_skill_key_slots,
    learned_skill_keys,
    set_equipped_slot,
)
from game.characters.skills import passive_combat_modifiers_merged
from game.characters.titles import TITLE_BY_KEY, format_title_bonus_brief
from game.characters.weapon_mastery import mastery_profile_lines, weapon_type_from_item_data
from game.combat import formulas
from utils.game_images_prefs import game_images_enabled
from utils.profile_portraits import portrait_path_for_character
from utils.ui import (
    LINE_SEP,
    _BAR_LEN,
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


def build_skills_screen_html(char: Character, *, locale: str) -> str:
    """Экран экипировки трёх боевых навыков (магия/физ. — как в combat engine)."""
    loc = locale if locale in ("ru", "en") else "ru"
    ensure_skill_meta(char)
    slots = equipped_skill_key_slots(char)
    lines = [
        t(loc, "skills_screen_title"),
        "",
    ]
    for i, key in enumerate(slots):
        sk = SKILL_BY_KEY.get(key) if key else None
        nm = html.escape(sk.name) if sk else "—"
        slot_label = html.escape(t(loc, "skills_slot_btn", n=i + 1))
        lines.append(f"<b>{slot_label}</b>: {nm}")
    lines.extend(["", t(loc, "skills_equip_hint")])
    return "\n".join(lines)


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


def _fmt_stat_plain(base: int, extra: int) -> str:
    b = int(base)
    e = int(extra)
    if e <= 0:
        return str(b)
    return f"{b} (+{e})"


def _build_profile_text(
    char: Character,
    *,
    compact: bool = True,
    weapon_attack: int,
    weapon_type: str = "blade",
    global_passives_line: str = "",
    gear_stat_bonus: dict[str, int] | None = None,
    title_stat_bonus: dict[str, int] | None = None,
    effective_stats: dict[str, int] | None = None,
    ranker_badge: str = "",
    ranker_effect: str = "",
    locale: str = "ru",
) -> str:
    cls = get_class_or_none(char.class_key)
    if cls:
        class_title = f"{cls.emoji} {html.escape(cls.name_ru)}"
    else:
        class_title = html.escape(char.class_key)
    profession_service.ensure_profession_meta(char)
    loc = locale if locale in ("ru", "en") else "ru"
    p1 = profession_service.active_primary_key(char)
    p2 = profession_service.active_secondary_key(char)
    prof_parts: list[str] = []
    if p1:
        prof_parts.append(html.escape(profession_service.profession_display_name(p1, locale=loc)))
    if p2:
        prof_parts.append(html.escape(profession_service.profession_display_name(p2, locale=loc)))
    if prof_parts:
        class_title += " · " + " / ".join(prof_parts)
    rank_raw = path_rank_name_ru(char)
    rank_s = html.escape(rank_raw) if rank_raw else "—"
    sec_raw = (char.meta_progress or {}).get("active_title_secondary_name_ru")
    sec_s = str(sec_raw).strip() if sec_raw else ""
    t1 = html.escape(char.active_title) if char.active_title else "—"
    t2 = html.escape(sec_s) if sec_s else "—"
    titles_row = f"① {t1} · ② {t2}" if (char.active_title or sec_s) else "—"

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
        crit_pct = crit_p * 100.0
        dodge_pct = dodge_p * 100.0

    gp_plain = global_passives_line.strip()
    gid_disp = str(int(char.game_id)) if char.game_id is not None else "—"
    gid_esc = html.escape(gid_disp)

    str_e = int(gb["str"]) + int(tb["str"])
    dex_e = int(gb["dex"]) + int(tb["dex"])
    int_e = int(gb["int"]) + int(tb["int"])
    vit_e = int(gb["vit"]) + int(tb["vit"])
    luck_e = int(gb["luck"]) + int(tb["luck"])

    head_row_compact = (
        f"🗡️ {html.escape(char.display_name)} · 🎮 <b>ID {gid_esc}</b> "
        f"• Ур.{char.level} 📍 Этаж: {char.floor_number}"
    )
    head_row_full = (
        f"🗡️ {html.escape(char.display_name)} · 🎮 ID {gid_esc} "
        f"• Ур.{char.level} 📍 Этаж: {char.floor_number}"
    )
    if ranker_badge:
        rank_combine = f"{rank_s} + {ranker_badge}" if rank_raw else ranker_badge
    else:
        rank_combine = rank_s

    if compact:
        gp_show = html.escape(global_passives_line) if global_passives_line.strip() else "—"
        lines: list[str] = [
            LINE_SEP,
            head_row_compact,
            f"🎖️ Звание: {rank_combine}",
            f"🏆 Титулы: {titles_row}",
        ]
        if ranker_effect:
            lines.append(ranker_effect)
        lines.extend(
            [
                f"🌐 Глобальные бонусы: <i>{gp_show}</i>",
                LINE_SEP,
                f"💰 Золото: {format_number(int(char.gold))}",
                LINE_SEP,
                render_hp_bar(char.hp_current, char.hp_max, wrap_bar_in_code=False),
                "",
                render_mp_bar(char.mp_current, char.mp_max, wrap_bar_in_code=False),
                "",
                render_stamina_bar(
                    char.stamina,
                    settings.MAX_STAMINA,
                    length=_BAR_LEN,
                    minutes_to_next=st_hint,
                    wrap_bar_in_code=False,
                ),
                "",
                format_rest_status_line_html(char),
                "",
                render_exp_bar(int(char.experience), xp_need, wrap_bar_in_code=False),
                LINE_SEP,
                "📊 <b>Характеристики</b>",
                f"⚔️ СИЛ: {_fmt_stat_plain(char.stat_strength, str_e)}    🏃 ЛОВ: {_fmt_stat_plain(char.stat_dexterity, dex_e)}",
                f"🔮 ИНТ: {_fmt_stat_plain(char.stat_intelligence, int_e)}    🛡️ ВЫН: {_fmt_stat_plain(char.stat_vitality, vit_e)}",
                f"🍀 УДА: {_fmt_stat_plain(char.stat_luck, luck_e)}",
                LINE_SEP,
            ],
        )
        unspent = int(getattr(char, "unspent_stat_points", 0) or 0)
        if unspent > 0:
            lines.append(f"✨ Свободных очков характеристик: <b>{unspent}</b> — /stats")
        return "\n".join(lines)

    # Полные характеристики — шаблон как в ТЗ (разделители «------------------------»).
    title_slots: list[tuple[str, str] | None] = []
    for tk in (
        title_service.active_title_key(char),
        title_service.active_secondary_title_key(char),
    ):
        if tk and tk in TITLE_BY_KEY:
            td = TITLE_BY_KEY[tk]
            title_slots.append((td.name_ru, format_title_bonus_brief(td)))
        else:
            title_slots.append(None)
    named = [s for s in title_slots if s]
    title_name_w = max((len(n) for n, _ in named), default=0)
    title_name_w = max(8, min(title_name_w, 22))

    def _title_row(circle: str, slot: tuple[str, str] | None) -> str:
        if not slot:
            return f" {circle} —"
        name, brief = slot
        gap = max(1, title_name_w - len(name) + 2)
        return f" {circle} {html.escape(name)}{' ' * gap}{html.escape(brief)}"

    lines = [
        LINE_SEP,
        head_row_full,
        f"🎖️ Звание: {rank_combine}",
        "🏆 Титулы:",
        "",
    ]
    lines.append(_title_row("①", title_slots[0]))
    lines.append(_title_row("②", title_slots[1]))
    lines.append("")
    if ranker_effect:
        lines.append(ranker_effect)
        lines.append("")
    lines.append("🌐 Глобальные бонусы:")
    if not gp_plain or gp_plain == "—":
        lines.append(" —")
    else:
        lines.append("")
        gp_parts = [p.strip() for p in global_passives_line.split(";") if p.strip()]
        last_i = len(gp_parts) - 1
        for i, p in enumerate(gp_parts):
            suf = ";" if i < last_i else ""
            lines.append(f" {html.escape(p)}{suf}")
    lines.extend(
        [
            LINE_SEP,
            f"💰 Золото: {format_number(int(char.gold))}",
            f"⚗️ Рунные камни: {format_number(char.rune_stones)}",
            LINE_SEP,
            f"📜 Класс: {class_title}",
            "",
            render_hp_bar(char.hp_current, char.hp_max, wrap_bar_in_code=False),
            "",
            render_mp_bar(char.mp_current, char.mp_max, wrap_bar_in_code=False),
            "",
            render_stamina_bar(
                char.stamina,
                settings.MAX_STAMINA,
                length=_BAR_LEN,
                minutes_to_next=st_hint,
                wrap_bar_in_code=False,
            ),
            "",
            format_rest_status_line_html(char),
            "",
            render_exp_bar(int(char.experience), xp_need, wrap_bar_in_code=False),
            LINE_SEP,
            "📊 Характеристики (база (+экип и титул))",
            f"⚔️ СИЛ: {_fmt_stat_plain(char.stat_strength, str_e)}    🏃 ЛОВ: {_fmt_stat_plain(char.stat_dexterity, dex_e)}",
            f"🔮 ИНТ: {_fmt_stat_plain(char.stat_intelligence, int_e)}    🛡️ ВЫН: {_fmt_stat_plain(char.stat_vitality, vit_e)}",
            f"🍀 УДА: {_fmt_stat_plain(char.stat_luck, luck_e)}",
            LINE_SEP,
        ],
    )
    m1, m2 = mastery_profile_lines(char, weapon_type)
    lines.extend([m1, "", m2, LINE_SEP])
    elem_ln = (
        "🔮 Элемент: нейтральный"
        if not char.element
        else element_profile_line(char.element)
    )
    lines.extend(
        [
            f"🗡️ Удар (физ.): {dmg_lo}–{dmg_hi}",
            f"💥 Крит: {crit_pct:.1f}%    💨 Уклонение: {dodge_pct:.1f}%",
            LINE_SEP,
        ],
    )
    unspent = int(getattr(char, "unspent_stat_points", 0) or 0)
    if unspent > 0:
        lines.append(f"✨ Свободных очков характеристик: {unspent} — /stats")
    lines.extend(
        [
            elem_ln,
            f"📍 Этаж: {char.floor_number} / 100 · открыто до: {int(char.highest_floor_reached)}",
        ],
    )
    return "\n".join(lines)


async def build_profile_html_async(session: AsyncSession, char: Character) -> str:
    if pets_mod.repair_pet_meta_if_needed(char):
        await session.flush()
    refresh_global_passives(char)
    w_atk = await _weapon_attack_value(session, char)
    weapon = await inventory_repo.get_equipped_weapon(session, char.id)
    wtype = "unarmed" if weapon is None else weapon_type_from_item_data(weapon.item_data or {})
    gp = format_unlocked_global_passives_ru(char)
    gear_b, title_b = await stat_bonus_service.extra_stat_bonuses(session, char)
    eff = await stat_bonus_service.effective_primary_stats(session, char)
    loc = get_locale(char, None)
    rk_badge, rk_eff = await leaderboard_service.profile_ranker_status_parts(session, char, locale=loc)
    base = _build_profile_text(
        char,
        compact=True,
        weapon_attack=w_atk,
        weapon_type=wtype,
        global_passives_line=gp,
        gear_stat_bonus=gear_b,
        title_stat_bonus=title_b,
        effective_stats=eff,
        ranker_badge=rk_badge,
        ranker_effect=rk_eff,
        locale=loc,
    )
    pet_blk = pets_mod.format_pet_profile_block_html(char, locale=loc, compact_status_line=True)
    return f"{base}\n{LINE_SEP}\n{pet_blk}"


async def build_profile_full_stats_html_async(session: AsyncSession, char: Character) -> str:
    """Полные боевые и вспомогательные бонусы, передышка, урон/крит/уклонение."""
    if pets_mod.repair_pet_meta_if_needed(char):
        await session.flush()
    refresh_global_passives(char)
    w_atk = await _weapon_attack_value(session, char)
    weapon = await inventory_repo.get_equipped_weapon(session, char.id)
    wtype = "unarmed" if weapon is None else weapon_type_from_item_data(weapon.item_data or {})
    gp = format_unlocked_global_passives_ru(char)
    gear_b, title_b = await stat_bonus_service.extra_stat_bonuses(session, char)
    eff = await stat_bonus_service.effective_primary_stats(session, char)
    loc = get_locale(char, None)
    rk_badge, rk_eff = await leaderboard_service.profile_ranker_status_parts(session, char, locale=loc)
    base = _build_profile_text(
        char,
        compact=False,
        weapon_attack=w_atk,
        weapon_type=wtype,
        global_passives_line=gp,
        gear_stat_bonus=gear_b,
        title_stat_bonus=title_b,
        effective_stats=eff,
        ranker_badge=rk_badge,
        ranker_effect=rk_eff,
        locale=loc,
    )
    pet_blk = pets_mod.format_pet_profile_block_html(char, locale=loc, compact_status_line=False)
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
            reply_markup=profile_full_stats_keyboard(char, locale=loc),
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


@router.callback_query(F.data == "prf:skills")
async def on_profile_skills(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
        ensure_skill_meta(char)
        await session.flush()
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        text = build_skills_screen_html(char, locale=loc)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=profile_skills_main_keyboard(locale=loc),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer()
    except Exception:
        logger.exception("prf:skills")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^prf:sk_slot:\d+$"))
async def on_profile_skills_slot(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None or callback.data is None:
            await callback.answer()
            return
        m = re.match(r"^prf:sk_slot:(\d+)$", callback.data)
        if m is None:
            await callback.answer()
            return
        slot = int(m.group(1))
        if slot not in (0, 1, 2):
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
        ensure_skill_meta(char)
        learned = sorted(learned_skill_keys(char))
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        if not learned:
            hint = "Сначала купи навыки в школе у храма на 3 этаже." if loc == "ru" else "Buy skills at the temple school on floor 3."
            await callback.answer(hint, show_alert=True)
            return
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=build_skills_screen_html(char, locale=loc),
            reply_markup=profile_skills_pick_keyboard(slot=slot, learned_keys=learned),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer()
    except Exception:
        logger.exception("prf:sk_slot")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^prf:sk_eq:\d+:.+$"))
async def on_profile_skills_equip(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None or callback.data is None:
            await callback.answer()
            return
        m = re.match(r"^prf:sk_eq:(\d+):(.+)$", callback.data)
        if m is None:
            await callback.answer()
            return
        slot = int(m.group(1))
        skill_key = m.group(2).strip()
        if slot not in (0, 1, 2):
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
        ensure_skill_meta(char)
        if not set_equipped_slot(char, slot, skill_key):
            await callback.answer("Нельзя назначить этот навык.", show_alert=True)
            return
        await session.flush()
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        text = build_skills_screen_html(char, locale=loc)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=profile_skills_main_keyboard(locale=loc),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer()
    except Exception:
        logger.exception("prf:sk_eq")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("prf:petpick:"))
async def on_profile_pet_pick(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None or callback.data is None:
            await callback.answer()
            return
        parts = callback.data.split(":", 2)
        if len(parts) < 3:
            await callback.answer()
            return
        pet_key = parts[2].strip()
        if not pet_key:
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
        if pets_mod.repair_pet_meta_if_needed(char):
            await session.flush()
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        if pet_key not in pets_mod.owned_keys(char):
            await callback.answer("Этого питомца нет.", show_alert=True)
            return
        ok, msg = pets_mod.set_active_pet(char, pet_key)
        if not ok:
            await callback.answer(msg[:200], show_alert=True)
            return
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
        await callback.answer(t(loc, "profile_pet_set_ok", name=msg)[:200], show_alert=False)
    except Exception:
        logger.exception("prf:petpick")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "prf:petback")
async def on_profile_pet_back(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
        await callback.answer()
    except Exception:
        logger.exception("prf:petback")
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
        ok, payload, rest_until = try_begin_or_claim_rest(char)
        await session.flush()
        if ok and rest_until is not None:
            schedule_rest_completion_notification(
                callback.bot,
                chat_id=callback.message.chat.id,
                telegram_id=callback.from_user.id,
                until=rest_until,
            )
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
async def on_profile_pet_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Список питомцев и выбор активного."""
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
        if pets_mod.repair_pet_meta_if_needed(char):
            await session.flush()
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        own = pets_mod.owned_keys(char)
        if not own:
            await callback.answer(t(loc, "profile_pet_none_hint"), show_alert=True)
            return
        title_service.refresh_unlocks(char)
        apply_completed_rest_if_needed(char)
        await session.flush()
        body = pets_mod.build_pet_picker_html(char, locale=loc)
        kb = profile_pet_picker_keyboard(
            own,
            locale=loc,
            active_key=pets_mod.active_pet_key(char),
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=body,
            reply_markup=kb,
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer()
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
