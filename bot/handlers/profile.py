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
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale, set_locale, t
from config import settings
from db.models.character import Character
from db.repository import character_repo, inventory_repo, user_repo
from bot.keyboards.menu_kb import main_menu_keyboard, menu_nav_button_row
from bot.keyboards.city_market_kb import (
    profile_skills_main_keyboard,
    profile_skills_pick_keyboard,
    profile_passive_pick_keyboard,
)
from bot.keyboards.profile_kb import (
    profile_full_stats_keyboard,
    profile_pet_picker_keyboard,
    profile_spec_submenu_keyboard,
    profile_view_keyboard,
)
from bot.keyboards.tree_kb import skill_tree_keyboard, node_action_keyboard
from bot.utils.game_ui import push_game_ui
from bot.utils.ui_photos import specialization_menu_photo_path
from services import character_service, fame_service, leaderboard_service, stat_bonus_service, title_service
from services.workshop_profile_ui import workshop_compact_line, workshop_full_stats_block
from services.rest_service import apply_completed_rest_if_needed
from game.characters import pets as pets_mod
from game.characters.classes import get_class_or_none
from game.archetypes import manager as arch_manager
from game.characters.global_passives import format_unlocked_global_passives_ru, refresh_global_passives
from game.characters.path_ranks import path_rank_lore, path_rank_name_ru
from services.character_service import experience_needed_for_next_level
from game.characters.player_skills import (
    SKILL_BY_KEY,
    ensure_skill_meta,
    equipped_skill_key_slots,
    equipped_passive_key,
    learned_skill_keys,
    learned_passives,
    passive_emoji,
    set_equipped_slot,
    set_passive_slot,
    skill_emoji,
)
from game.characters.skills import passive_combat_modifiers_merged
from game.characters.titles import format_title_bonus_brief
from game.crafting.recipes_data import PROF_ALCHEMIST, PROF_BLACKSMITH, PROF_JEWELER
from game.crafting.workshop_meta import get_workshop_state, save_workshop_state
from game.characters.weapon_mastery import (
    mastery_all_types_line,
    mastery_profile_lines,
    weapon_type_from_item_data,
)
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
    """Экран экипировки трёх боевых навыков + слот пассивки."""
    loc = locale if locale in ("ru", "en") else "ru"
    ensure_skill_meta(char)
    slots = equipped_skill_key_slots(char)
    lines = [
        t(loc, "skills_screen_title"),
        "",
        "<b>⚔️ Активные навыки:</b>",
    ]
    for i, key in enumerate(slots):
        sk = SKILL_BY_KEY.get(key) if key else None
        if sk:
            emoji = skill_emoji(sk.kind)
            nm = f"{emoji} {html.escape(sk.name)}"
        else:
            nm = "— (не выбран)"
        slot_label = html.escape(t(loc, "skills_slot_btn", n=i + 1))
        lines.append(f"  <b>{slot_label}:</b> {nm}")

    # Слот пассивки
    lines.append("")
    lines.append("<b>🛡️ Пассивный навык:</b>")
    pas_key = equipped_passive_key(char)
    if pas_key:
        pas_list = {p.key: p for p in learned_passives(char)}
        p = pas_list.get(pas_key)
        if p:
            em = passive_emoji(p.modifiers)
            lines.append(f"  {em} {html.escape(p.name_ru)} — <i>{html.escape(p.description_ru)}</i>")
        else:
            lines.append("  — (не выбрана)")
    else:
        lines.append("  — (не выбрана)")

    lines.append("")
    lines.append(
        "<i>Пассивные узлы из древа (Ярость, Жажда крови и др.) работают автоматически "
        "и не попадают в список ниже — только активные навыки можно поставить в слоты 1–3.</i>"
    )

    learned = sorted(learned_skill_keys(char))
    if learned:
        lines.extend(["", "<b>📚 Изученные активные навыки</b> (можно поставить в слоты):"])
        for k in learned:
            sk_row = SKILL_BY_KEY.get(k)
            sk_v2 = arch_manager.get_skill(k)
            if sk_row and sk_v2:
                emoji = skill_emoji(sk_row.kind)
                lines.append(
                    f"  {emoji} <b>{html.escape(sk_row.name)}</b> — "
                    f"<i>{html.escape(sk_v2.description_ru)}</i> · MP {sk_row.mp_cost}, CD {sk_row.cooldown}"
                )
            elif sk_row:
                emoji = skill_emoji(sk_row.kind)
                lines.append(f"  {emoji} <b>{html.escape(sk_row.name)}</b>")
            else:
                lines.append(f"  • <code>{html.escape(k)}</code>")

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
    ranker_name_prefix: str = "",
    locale: str = "ru",
    gear_defense: int = 0,
    chance_bonuses_line: str = "",
    achievement_bonuses_line: str = "",
    stat_derivatives_block: str = "",
    skill_tree_passives_block: str = "",
) -> str:
    ck = str(char.class_key or "wanderer").lower().strip()
    arch = arch_manager.get_archetype(ck)
    if arch:
        class_title = f"{arch.emoji} {html.escape(arch.name_ru)}"
    else:
        class_title = html.escape(ck)
    loc = locale if locale in ("ru", "en") else "ru"
    rank_raw = path_rank_name_ru(char)
    rank_s = html.escape(rank_raw) if rank_raw else "—"
    rank_lore_raw = path_rank_lore(char) if rank_raw else None
    rank_lore_s = html.escape(rank_lore_raw) if rank_lore_raw else ""
    sec_raw = (char.meta_progress or {}).get("active_title_secondary_name_ru")
    sec_s = str(sec_raw).strip() if sec_raw else ""
    t1 = html.escape(char.active_title) if char.active_title else "—"
    t2 = html.escape(sec_s) if sec_s else "—"
    titles_row = f"① {t1} · ② {t2}" if (char.active_title or sec_s) else "—"

    xp_need = experience_needed_for_next_level(char.level)
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

    crit_pct = dodge_pct = miss_pct = hit_pct = 0.0
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
        miss_p = formulas.miss_chance_percent(int(eff["dex"]))
        dmg_lo, dmg_hi = formulas.physical_damage_range(
            int(eff["str"]),
            weapon_attack,
            0,
            elemental_bonus_percent=0,
        )
        crit_pct = crit_p * 100.0
        dodge_pct = dodge_p * 100.0
        miss_pct = miss_p * 100.0
        hit_pct = max(0.0, 100.0 - miss_pct)

    gp_plain = global_passives_line.strip()
    gid_disp = str(int(char.game_id)) if char.game_id is not None else "—"
    gid_esc = html.escape(gid_disp)

    str_e = int(gb["str"]) + int(tb["str"])
    dex_e = int(gb["dex"]) + int(tb["dex"])
    int_e = int(gb["int"]) + int(tb["int"])
    vit_e = int(gb["vit"]) + int(tb["vit"])
    luck_e = int(gb["luck"]) + int(tb["luck"])

    rp_esc = html.escape(ranker_name_prefix) if ranker_name_prefix else ""
    head_row_compact = (
        f"🗡️ {rp_esc}{html.escape(char.display_name)} · 🎮 <b>ID {gid_esc}</b> "
        f"• Ур.{char.level} 📍 Этаж: {char.floor_number}"
    )
    head_row_full = (
        f"🗡️ {rp_esc}{html.escape(char.display_name)} · 🎮 ID {gid_esc} "
        f"• Ур.{char.level} 📍 Этаж: {char.floor_number}"
    )
    rank_combine = rank_s

    if compact:
        gp_show = html.escape(global_passives_line) if global_passives_line.strip() else "—"
        lines: list[str] = [
            LINE_SEP,
            head_row_compact,
            f"🎖️ Звание: {rank_combine}",
            f"🏆 Титулы: {titles_row}",
        ]
        lines.extend(
            [
                f"🌐 Глобальные бонусы: <i>{gp_show}</i>",
                LINE_SEP,
                f"💰 Золото: {format_number(int(char.gold))}",
                "",
                fame_service.format_fame_html(char),
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
                render_exp_bar(int(char.experience), xp_need, wrap_bar_in_code=False),
                "",
                workshop_compact_line(char),
                LINE_SEP,
                "📊 <b>Характеристики</b>",
                f"⚔️ СИЛ: {_fmt_stat_plain(char.stat_strength, str_e)}    🏃 ЛОВ: {_fmt_stat_plain(char.stat_dexterity, dex_e)}",
                f"🔮 ИНТ: {_fmt_stat_plain(char.stat_intelligence, int_e)}    🛡️ ВЫН: {_fmt_stat_plain(char.stat_vitality, vit_e)}",
                f"🍀 УДА: {_fmt_stat_plain(char.stat_luck, luck_e)}",
                f"🛡️ Защита (броня): <b>{gear_defense}</b>",
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
        if tk:
            td = title_service.title_def_for(char, tk)
            if td is not None:
                title_slots.append((td.name_ru, format_title_bonus_brief(td)))
            else:
                title_slots.append(None)
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
    ]
    if rank_lore_s:
        lines.append(f"<i>📖 {rank_lore_s} (только лор, без эффектов)</i>")
    lines.extend([
        "🏆 Титулы:",
        "",
    ])
    lines.append(_title_row("①", title_slots[0]))
    lines.append(_title_row("②", title_slots[1]))
    lines.append("")
    if arch:
        about = (getattr(arch, "description_ru", None) or "").strip()
        if about:
            lines.append("📘 <b>Об архетипе</b>")
            lines.append(f"<i>{html.escape(about[:900])}</i>")
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
        ]
    )
    if arch and (arch.description_ru or "").strip():
        lines.append(f"<i>{html.escape((arch.description_ru or '').strip())}</i>")
    lines.extend(
        [
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
            render_exp_bar(int(char.experience), xp_need, wrap_bar_in_code=False),
            LINE_SEP,
            "📊 Характеристики (база (+экип и титул))",
            f"⚔️ СИЛ: {_fmt_stat_plain(char.stat_strength, str_e)}    🏃 ЛОВ: {_fmt_stat_plain(char.stat_dexterity, dex_e)}",
            f"🔮 ИНТ: {_fmt_stat_plain(char.stat_intelligence, int_e)}    🛡️ ВЫН: {_fmt_stat_plain(char.stat_vitality, vit_e)}",
            f"🍀 УДА: {_fmt_stat_plain(char.stat_luck, luck_e)}",
            f"🛡️ Защита (броня): <b>{gear_defense}</b>",
            LINE_SEP,
        ],
    )
    if stat_derivatives_block.strip() and (not compact):
        lines.append(stat_derivatives_block.strip())
        lines.append(LINE_SEP)
    m1, m2 = mastery_profile_lines(char, weapon_type)
    lines.extend([m1, "", m2])
    all_m = mastery_all_types_line(char)
    if all_m:
        lines.append(f"📚 Все типы: <i>{all_m}</i>")
    lines.append(LINE_SEP)
    lines.append(workshop_full_stats_block(char).rstrip())
    lines.append(LINE_SEP)
    elem_ln = (
        "🔮 Элемент: нейтральный"
        if not char.element
        else element_profile_line(char.element)
    )
    lines.extend(
        [
            f"🗡️ Удар (физ.): {dmg_lo}–{dmg_hi}",
            f"💥 Крит: {crit_pct:.1f}%    💨 Уклонение: {dodge_pct:.1f}%",
            f"🎯 Попадание: {hit_pct:.1f}%    💨 Промах: {miss_pct:.1f}%",
            LINE_SEP,
        ],
    )
    if chance_bonuses_line:
        lines.extend([
            "✨ Бонусы экипировки:",
            f" {chance_bonuses_line}",
            LINE_SEP,
        ])
    if achievement_bonuses_line:
        lines.extend([
            "🏅 От достижений:",
            f" {achievement_bonuses_line}",
            LINE_SEP,
        ])
    stp = skill_tree_passives_block.strip()
    if stp:
        lines.extend([
            "<b>🌳 Древо навыков (пассивные узлы)</b>",
            "<i>Не в слотах 1–3 — бонусы действуют сами по себе.</i>",
            "",
            stp,
            LINE_SEP,
        ])
    unspent = int(getattr(char, "unspent_stat_points", 0) or 0)
    if unspent > 0:
        lines.append(f"✨ Свободных очков характеристик: {unspent} — /stats")
    lines.extend(
        [
            elem_ln,
            f"📍 Этаж: {char.floor_number} / 135 · открыто до: {int(char.highest_floor_reached)}",
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
    gear_def = await stat_bonus_service.equipped_gear_defense_total(session, char.id)
    loc = get_locale(char, None)
    lb_rank = await leaderboard_service.best_leaderboard_rank(session, char)
    rp = t(loc, "profile_ranker_name_badge") if lb_rank is not None else ""
    base = _build_profile_text(
        char,
        compact=True,
        weapon_attack=w_atk,
        weapon_type=wtype,
        global_passives_line=gp,
        gear_stat_bonus=gear_b,
        title_stat_bonus=title_b,
        effective_stats=eff,
        ranker_name_prefix=rp,
        locale=loc,
        gear_defense=gear_def,
    )
    pet_blk = pets_mod.format_pet_profile_block_html(char, locale=loc, compact_status_line=True)
    return f"{base}\n{LINE_SEP}\n{pet_blk}"


async def build_profile_full_stats_html_async(session: AsyncSession, char: Character) -> str:
    """Полные боевые и вспомогательные бонусы, урон/крит/уклонение."""
    if pets_mod.repair_pet_meta_if_needed(char):
        await session.flush()
    refresh_global_passives(char)
    w_atk = await _weapon_attack_value(session, char)
    weapon = await inventory_repo.get_equipped_weapon(session, char.id)
    wtype = "unarmed" if weapon is None else weapon_type_from_item_data(weapon.item_data or {})
    gp = format_unlocked_global_passives_ru(char)
    gear_b, title_b = await stat_bonus_service.extra_stat_bonuses(session, char)
    eff = await stat_bonus_service.effective_primary_stats(session, char)
    gear_def = await stat_bonus_service.equipped_gear_defense_total(session, char.id)
    loc = get_locale(char, None)
    lb_rank = await leaderboard_service.best_leaderboard_rank(session, char)
    rp = t(loc, "profile_ranker_name_badge") if lb_rank is not None else ""

    chance_bonuses = await stat_bonus_service.aggregate_chance_bonuses(session, int(char.id))
    chance_line = stat_bonus_service.format_chance_bonuses_html(chance_bonuses)
    from services import achievement_service as _achs
    ach_line = _achs.format_achievement_bonuses_html(char)

    deriv = stat_bonus_service.format_stat_derived_effects_ru(eff)
    tree_pass_html = arch_manager.format_skill_tree_passives_profile_html_ru(char)
    base = _build_profile_text(
        char,
        compact=False,
        weapon_attack=w_atk,
        weapon_type=wtype,
        global_passives_line=gp,
        gear_stat_bonus=gear_b,
        title_stat_bonus=title_b,
        effective_stats=eff,
        ranker_name_prefix=rp,
        locale=loc,
        gear_defense=gear_def,
        chance_bonuses_line=chance_line,
        achievement_bonuses_line=ach_line,
        stat_derivatives_block=deriv,
        skill_tree_passives_block=tree_pass_html,
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
            character=char,
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


@router.callback_query(F.data == "prf:achievements")
async def on_profile_achievements(
    query: CallbackQuery, session: AsyncSession, state: FSMContext,
) -> None:
    try:
        if query.from_user is None or query.message is None:
            await query.answer()
            return
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if not user or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if not char:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        from services import achievement_service

        achievement_service.check_and_apply_achievements(char)
        await session.flush()
        text = achievement_service.format_achievements_html(char)
        loc = get_locale(char, query.from_user.language_code if query.from_user else None)
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=text,
            reply_markup=profile_full_stats_keyboard(locale=loc),
            target_message=query.message,
            photo_path=None,
            character=char,
        )
        await query.answer()
    except Exception:
        logger.exception("prf:achievements")
        await query.answer("Ошибка.", show_alert=True)


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
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("prf:full")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "prf:spec")
async def on_profile_spec_submenu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        text = t(loc, "profile_spec_intro")
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=profile_spec_submenu_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("prf:spec")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "prf:wsspec_menu")
async def prf_wsspec_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
        ws = get_workshop_state(char)
        if ws.get("spec_locked"):
            await callback.answer("Специализация уже выбрана навсегда.", show_alert=True)
            return
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="⚒️ Кузнец", callback_data="prf:wsspec_do:blacksmith"),
                    InlineKeyboardButton(text="⚗️ Алхимик", callback_data="prf:wsspec_do:alchemist"),
                ],
                [InlineKeyboardButton(text="💎 Ювелир", callback_data="prf:wsspec_do:jeweler")],
                [InlineKeyboardButton(text=t(loc, "profile_back_compact"), callback_data="prf:spec")],
                menu_nav_button_row(),
            ],
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text="🔧 <b>Специализация ремесла</b>\n\nОдин раз навсегда: +10% к опыту выбранной профессии.",
            reply_markup=kb,
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("prf:wsspec_menu")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("prf:wsspec_do:"))
async def prf_wsspec_do(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        pk = str(callback.data.split(":")[2]).lower().strip()
        if pk not in (PROF_BLACKSMITH, PROF_ALCHEMIST, PROF_JEWELER):
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
        ws = get_workshop_state(char)
        if ws.get("spec_locked"):
            await callback.answer("Уже выбрано.", show_alert=True)
            return
        ws["spec_profession"] = pk
        ws["spec_locked"] = True
        save_workshop_state(char, ws)
        await session.commit()
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        pr_ru = {
            PROF_BLACKSMITH: "Кузнец",
            PROF_ALCHEMIST: "Алхимик",
            PROF_JEWELER: "Ювелир",
        }.get(pk, pk)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=f"✅ Специализация: <b>{html.escape(pr_ru)}</b> (+10% опыта этой профессии).",
            reply_markup=profile_spec_submenu_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer("Сохранено.")
    except Exception:
        logger.exception("prf:wsspec_do")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "prf:wsshow_menu")
async def prf_wsshow_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="⚒️ Кузнец", callback_data="prf:wsshow_do:blacksmith"),
                    InlineKeyboardButton(text="⚗️ Алхимик", callback_data="prf:wsshow_do:alchemist"),
                ],
                [InlineKeyboardButton(text="💎 Ювелир", callback_data="prf:wsshow_do:jeweler")],
                [InlineKeyboardButton(text=t(loc, "profile_back_compact"), callback_data="prf:spec")],
                menu_nav_button_row(),
            ],
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text="📌 <b>Профессия на карточке статуса</b>\n\nЧто показывать в строке ремесла (можно менять когда угодно).",
            reply_markup=kb,
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("prf:wsshow_menu")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("prf:wsshow_do:"))
async def prf_wsshow_do(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        pk = str(callback.data.split(":")[2]).lower().strip()
        if pk not in (PROF_BLACKSMITH, PROF_ALCHEMIST, PROF_JEWELER):
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
        ws = get_workshop_state(char)
        ws["status_profession"] = pk
        save_workshop_state(char, ws)
        await session.commit()
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        sh_ru = {
            PROF_BLACKSMITH: "Кузнец",
            PROF_ALCHEMIST: "Алхимик",
            PROF_JEWELER: "Ювелир",
        }.get(pk, pk)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=f"✅ На карточке будет показываться: <b>{html.escape(sh_ru)}</b>.",
            reply_markup=profile_spec_submenu_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer("Ок.")
    except Exception:
        logger.exception("prf:wsshow_do")
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
            character=char,
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
        if char.level >= 10:
            arch_manager.sync_unspent_sp_with_tree(char)
        await session.flush()
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)

        text = (
            "🌳 <b>Древо навыков</b>\n\n"
            "Здесь ты тратишь очки навыков (SP): они начисляются после <b>10 уровня</b>. "
            "Узлы дают постоянные бонусы или открывают активные способности для боевых кнопок.\n\n"
            "<i>В карточке узла — текст ветки, блок «Эффект» с цифрами, для активных навыков ещё MP, КД и тип урона.</i>"
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=skill_tree_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("prf:skills")
        await callback.answer("Ошибка.", show_alert=True)

@router.callback_query(F.data.startswith("tree:view:"))
async def on_tree_node_view(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        node_key = callback.data.split(":")[-1]
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        tree = arch_manager.get_character_tree(char)
        node = tree.get(node_key)
        if not node:
            await callback.answer("Узел не найден.", show_alert=True)
            return

        unlocked = arch_manager.get_unlocked_node_keys(char)
        is_unlocked = node_key in unlocked
        can_buy = (
            not is_unlocked
            and all(p in unlocked for p in node.parent_keys)
            and arch_manager.get_character_sp(char) >= node.cost_sp
        )

        status = "✅ Изучено" if is_unlocked else ("🌟 Доступно" if can_buy else "🔒 Заблокировано")

        text = (
            f"📍 <b>{html.escape(node.name_ru)}</b>\n"
            f"Стоимость: <b>{node.cost_sp} SP</b>\n"
            f"Статус: <b>{status}</b>\n\n"
            f"{node.description_ru}\n\n"
        )

        fx = arch_manager.format_skill_tree_node_effect_ru(node)
        if fx.strip():
            text += f"<b>Эффект (цифры):</b>\n<pre>{html.escape(fx)}</pre>\n\n"

        if node.node_type == "active_skill":
            sk = arch_manager.get_skill(str(node.value))
            if sk:
                text += (
                    f"🔮 <b>Активный навык:</b> {html.escape(sk.name_ru)}\n"
                    f"<i>{html.escape(sk.description_ru)}</i>\n"
                    f"Ресурс: <b>{sk.mp_cost}</b> MP · перезарядка <b>{sk.cooldown}</b> ход. · "
                    f"{'магия' if sk.kind == 'mag' else 'физ'} · сила ×{sk.power_mult:g}\n\n"
                )

        if node.parent_keys:
            parents = ", ".join([tree[p].name_ru for p in node.parent_keys])
            text += f"<i>Требуется:</i> {html.escape(parents)}"

        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=node_action_keyboard(node_key, can_buy, cost_sp=node.cost_sp),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("tree:view")
        await callback.answer("Ошибка.", show_alert=True)

@router.callback_query(F.data.startswith("tree:buy:"))
async def on_tree_node_buy(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        node_key = callback.data.split(":")[-1]
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        from config import is_admin as _is_admin

        ok, msg = arch_manager.try_unlock_node(char, node_key, admin_bypass=_is_admin(callback.from_user.id))
        if not ok:
            await callback.answer(msg, show_alert=True)
            return

        await session.commit()
        await callback.answer(msg, show_alert=False)

        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        text = (
            "🌳 <b>Древо навыков</b>\n\n"
            "Узел успешно изучен! Новые способности можно выбрать в "
            "<b>Специализация → Экипировать навыки</b>."
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=skill_tree_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
    except Exception:
        logger.exception("tree:buy")
        await callback.answer("Ошибка при изучении.", show_alert=True)


@router.callback_query(F.data == "tree:spxg")
async def on_tree_sp_exchange_gold(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Пост-кап: обменять 1 неизрасходованный SP на золото, если все узлы открыты."""
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
        if char.level >= 10:
            arch_manager.sync_unspent_sp_with_tree(char)
        ok, err = arch_manager.consume_one_unspent_sp(char)
        if not ok:
            await callback.answer(err, show_alert=True)
            return
        gold_amt = max(150, int(char.level or 1) * 40)
        character_service.add_gold(
            char,
            gold_amt,
            spend_for="",
            spend_kind="skill_tree",
        )
        await session.commit()
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        text = (
            "🌳 <b>Древо навыков</b>\n\n"
            f"Обмен: <b>−1 SP</b> → <b>+{gold_amt:,}</b> 💰 "
            "<i>(доступно, пока древо полностью открыто и есть очки.)</i>"
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=skill_tree_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer("Готово!")
    except Exception:
        logger.exception("tree:spxg")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "prf:skills_equip")
async def on_profile_skills_equip_menu(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext,
) -> None:
    """Меню экипировки трёх боевых навыков (из специализации)."""
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
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=build_skills_screen_html(char, locale=loc),
            reply_markup=profile_skills_main_keyboard(locale=loc),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("prf:skills_equip")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "prf:stathelp")
async def on_profile_stat_help(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext,
) -> None:
    """Справка: что в целом даёт СИЛ/ЛОВ/…"""
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if not user or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if not char:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        text = stat_bonus_service.format_stat_cheat_sheet_ru()
        rows = [
            [InlineKeyboardButton(text="📊 Полные характеристики", callback_data="prf:full")],
            [
                InlineKeyboardButton(text=t(loc, "profile_back_compact"), callback_data="prf:back"),
            ],
            [
                InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub"),
                InlineKeyboardButton(text=t(loc, "profile_spec_btn"), callback_data="prf:spec"),
            ],
        ]
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            target_message=callback.message,
            photo_path=None,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("prf:stathelp")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "prf:elements_info")
async def on_profile_elements_info(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext,
) -> None:
    """Справка по стихиям: слабости, резистентности."""
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id) if user and not user.is_banned else None
        from game.items.runes import ELEMENTS, ELEMENT_WEAKNESS, ELEMENT_RESISTANCE
        lines = [
            "🔮 <b>Стихии монстров и слабости</b>",
            "",
            "При атаке монстра его слабой стихией — <b>+25% урона</b>.",
            "При атаке устойчивой стихией — <b>-15% урона</b>.",
            "Совпадение стихий — <b>+10% урона</b>.",
            "",
            "<b>Таблица слабостей:</b>",
        ]
        for elem_key, info in ELEMENTS.items():
            weak_to = ELEMENT_WEAKNESS.get(elem_key, "—")
            resist = ELEMENT_RESISTANCE.get(elem_key, "—")
            weak_info = ELEMENTS.get(weak_to, {})
            resist_info = ELEMENTS.get(resist, {})
            weak_str = f"{weak_info.get('emoji','')}{weak_info.get('name', weak_to)}" if weak_to != "—" else "—"
            resist_str = f"{resist_info.get('emoji','')}{resist_info.get('name', resist)}" if resist != "—" else "—"
            lines.append(
                f"{info['emoji']} <b>{info['name']}</b>: "
                f"слаб к {weak_str} · устойчив к {resist_str}"
            )
        lines.extend([
            "",
            "<i>Узнать стихию монстра можно в бою — она указана рядом с именем врага.</i>",
            "<i>Настроить свою стихию: экипируй оружие с руной нужного элемента.</i>",
        ])
        text = "\n".join(lines)
        rows = [
            [InlineKeyboardButton(text="📊 Полные характеристики", callback_data="prf:full")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="prf:back")],
        ]
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            target_message=callback.message,
            photo_path=None,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("prf:elements_info")
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
        if slot not in (0, 1, 2, 3):
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
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)

        # Слот 3 — выбор пассивки
        if slot == 3:
            passives = learned_passives(char)
            if not passives:
                await callback.answer("У тебя нет пассивных навыков.", show_alert=True)
                return
            await push_game_ui(
                state, callback.bot,
                chat_id=callback.message.chat.id,
                text=build_skills_screen_html(char, locale=loc),
                reply_markup=profile_passive_pick_keyboard(passives),
                target_message=callback.message,
                photo_path=specialization_menu_photo_path(),
                character=char,
            )
            await callback.answer()
            return

        # Слоты 0-2 — выбор активного навыка
        learned = sorted(learned_skill_keys(char))
        if not learned:
            await callback.answer("Нет разблокированных навыков.", show_alert=True)
            return
        await push_game_ui(
            state, callback.bot,
            chat_id=callback.message.chat.id,
            text=build_skills_screen_html(char, locale=loc),
            reply_markup=profile_skills_pick_keyboard(slot=slot, learned_keys=learned),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
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
        if slot not in (0, 1, 2, 3):
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

        if slot == 3:
            # Экипировка пассивки
            if not set_passive_slot(char, skill_key):
                await callback.answer("Эта пассивка недоступна.", show_alert=True)
                return
            await session.flush()
            loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
            await push_game_ui(
                state, callback.bot,
                chat_id=callback.message.chat.id,
                text=build_skills_screen_html(char, locale=loc),
                reply_markup=profile_skills_main_keyboard(locale=loc),
                target_message=callback.message,
                photo_path=specialization_menu_photo_path(),
                character=char,
            )
            await callback.answer("🛡️ Пассивка выбрана!")
            return

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
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer("✅ Навык экипирован!")
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
            character=char,
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
            character=char,
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
        await session.flush()
        await callback.answer(
            "Передышка доступна в разделе «Дом» (кнопка 🏠 в меню).",
            show_alert=True,
        )
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
            character=char,
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
            reply_markup=main_menu_keyboard(locale=arg, character=char),
        )
    except Exception:
        logger.exception("cmd_lang")
        await message.answer("Ошибка.")
