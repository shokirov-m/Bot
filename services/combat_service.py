"""
Старт боя, обработка ходов, победа/поражение, награды и штрафы смерти.
"""

from __future__ import annotations

import asyncio
import copy
import html
import random
from typing import Any

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Chat, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale, t
from bot.keyboards.combat_kb import combat_item_picker_keyboard, combat_main_keyboard
from bot.keyboards.menu_kb import menu_nav_button_row
from bot.states.combat_states import CombatStates
from bot.utils.game_ui import GAME_UI_CHAT_ID, GAME_UI_MESSAGE_ID, push_game_ui
from config import settings
from db.models.character import Character
from db.models.inventory import InventoryItem
from db.repository import character_repo, floor_progress_repo, inventory_repo, user_repo
from game.characters.classes import get_class_or_none
from game.characters.path_ranks import PATH_RANK_BY_KEY
from game.characters.player_skills import battle_skills_tuple, ensure_skill_meta
from game.characters.skills import passive_combat_modifiers_merged, skills_for_class
from game.characters.weapon_mastery import damage_multiplier_for_type, record_strike, weapon_type_from_item_data
from game.combat import consumables, effects, engine, formulas, monster_ai, night_mode as combat_night
from game.items import runes as rune_items
from game.balance import (
    DEATH_GOLD_LOSS_FRACTION,
    MAX_DEATH_GOLD_LOSS,
    MONSTER_ATK_FLAT_ELITE,
    MONSTER_ATK_FLAT_NORMAL,
    MONSTER_FLOOR10_MAJOR_BOSS_MULT,
    MONSTER_FLOOR20_SLIME_KING_ARMOR_PENETRATION,
    MONSTER_FLOOR20_SLIME_KING_STAT_MULT,
    MONSTER_FLOOR20_SLIME_KING_TEMPLATE_KEY,
    MONSTER_FLOOR5_MINIBOSS_HP_CAP,
    MONSTER_LATE_ATK_MULT,
    MONSTER_LATE_FLOOR_THRESHOLD,
    MONSTER_LATE_HP_MULT,
    MONSTER_MULT_ELITE_ATK,
    MONSTER_MULT_ELITE_HP,
    MONSTER_MULT_MAJOR_ATK,
    MONSTER_MULT_MAJOR_HP,
    MONSTER_MULT_MINI_ATK,
    MONSTER_MULT_MINI_HP,
    PLAYER_DEFENSE_BONUS_PER_LEVEL,
)
from game.characters import pets as pets_mod
from game.floors import floor_data
from game.floors import long_floor as long_floor_mod
from game.floors import monster_catalog as monster_catalog_mod
from game.floors import rotten_swamps as rotten_swamps_mod
from game.floors import room_clear_floor as room_clear_mod
from game.floors import wave_floor as wave_floor_mod
from game.floors import explore_floor as explore_floor_mod
from utils.image_assets import combat_monster_portrait_path
from game.floors.monster_stat_formula import compute_formula_stat_bundle, monster_strike_ailment
from game.floors.monsters import FloorMonsterSpawn, MonsterTemplate, build_spawns_for_floor
from game.economy import sinks as sink_rules
from game.floors.rewards import experience_reward, gold_reward, roll_item_drop, roll_rune_stone
from game.items import enchant as enchant_rules
from game.items.rarity_scaling import scaled_armor_defense_value
from game.items import loot as loot_tables
from game.characters.global_passives import refresh_global_passives
from utils.game_images_prefs import game_images_enabled

from services import (
    anticheat_service,
    character_service,
    city_quest_service,
    clan_service,
    combat_idle_service,
    daily_service,
    floor10_pioneer_service,
    game_metrics_service,
    golden_goblin_service,
    leaderboard_service,
    profession_service,
    quest_service,
    rest_service,
    season_record_service,
    stat_bonus_service,
    title_service,
)
from services.tutorial_battle_service import apply_path_rank_from_tutorial, tutorial_battle_pending
from game.economy.stamina import spend_stamina
from services.stamina_service import can_start_combat
from utils.ui import LINE_SEP, LINE_SEP_BATTLE, render_hp_bar, render_mp_bar

TUTORIAL_DUMMY_TEMPLATE = MonsterTemplate(
    "tutorial_dummy",
    "Учебный манекен",
    "🎭",
    "earth",
    "Наставник наблюдает за твоим стилем боя.",
)
TUTORIAL_SPAWN = FloorMonsterSpawn(
    slot_code="tutorial",
    template=TUTORIAL_DUMMY_TEMPLATE,
    is_elite=False,
    is_mini_boss=False,
    is_major_boss=False,
)


def _taunt_banner_html(taunt_line: str) -> str:
    """Насмешка монстра (сырой текст хранится для экрана боя в 💬 «…»)."""
    t = (taunt_line or "").strip()
    if not t:
        return ""
    return html.escape(t)


def _clamp_battle_caption(html: str, max_len: int = 1020) -> str:
    if len(html) <= max_len:
        return html
    return html[: max_len - 1] + "…"


async def _safe_edit_combat_message_text(
    state: FSMContext,
    message: Message,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    """
    Правка текста боя / победы / поражения.
    Не рвёт транзакцию из‑за «message is not modified» или редкого несовпадения типа сообщения.
    Для боя с портретом-монстром (фото) длинные экраны переводятся в обычное текстовое сообщение.
    """
    data = await state.get_data()
    mid = data.get("combat_message_id")
    cid = data.get("combat_chat_id")
    is_photo = bool(data.get("combat_ui_is_photo"))
    bot = message.bot

    if is_photo and len(text) > 1019:
        await push_game_ui(
            state,
            bot,
            chat_id=int(cid or message.chat.id),
            text=text,
            reply_markup=reply_markup,
            target_message=message,
            photo_path=None,
        )
        u = await state.get_data()
        nmid = u.get(GAME_UI_MESSAGE_ID)
        ncid = u.get(GAME_UI_CHAT_ID)
        if nmid is not None and ncid is not None:
            await state.update_data(
                combat_ui_is_photo=False,
                combat_message_id=int(nmid),
                combat_chat_id=int(ncid),
            )
        return True

    use_mid = int(mid) if mid is not None else message.message_id
    use_cid = int(cid) if cid is not None else message.chat.id

    try:
        if is_photo:
            cap = _clamp_battle_caption(text)
            await bot.edit_message_caption(
                chat_id=use_cid,
                message_id=use_mid,
                caption=cap,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )
        else:
            await bot.edit_message_text(
                chat_id=use_cid,
                message_id=use_mid,
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )
        return True
    except TelegramBadRequest as e:
        err = str(e).lower()
        if "message is not modified" in err:
            return True
        if "message can't be edited" in err or "there is no text" in err or "have no text" in err:
            logger.warning("combat UI: правка сообщения пропущена ({})", e)
            return False
        raise


def _tutorial_monster_bundle() -> dict[str, Any]:
    return {
        "name": TUTORIAL_DUMMY_TEMPLATE.name,
        "emoji": TUTORIAL_DUMMY_TEMPLATE.emoji,
        "template_key": TUTORIAL_DUMMY_TEMPLATE.key,
        "hp": 34,
        "max_hp": 34,
        "atk": 4,
        "defense": 0,
        "element": "earth",
        "is_elite": False,
        "is_mini_boss": False,
        "is_major_boss": False,
    }


def _tutorial_monster_wave2() -> dict[str, Any]:
    return {
        "name": "Манекен — давление",
        "emoji": "🥊",
        "template_key": "tutorial_dummy_2",
        "hp": 32,
        "max_hp": 32,
        "atk": 7,
        "defense": 1,
        "element": "earth",
        "is_elite": False,
        "is_mini_boss": False,
        "is_major_boss": False,
    }


def _monster_stat_bundle_from_catalog(
    floor_number: int,
    spawn: FloorMonsterSpawn,
    cat: dict[str, Any],
) -> dict[str, Any]:
    """Явные hp/atk/def из каталога (.py) + опционально множители роли (элита / мини / мажор)."""
    ratio = monster_catalog_mod.floor_ratio(cat, int(floor_number))
    tpl_key = str(spawn.template.key or "")
    skip_role = bool(cat.get("catalog_skip_spawn_mults"))

    if skip_role:
        hp_out = max(1, int(float(cat["hp"]) * ratio))
        atk_out = max(1, int(float(cat["atk"]) * ratio))
        def_out = max(0, int(float(cat["def"]) * ratio))
    else:
        hp0 = max(1, int(float(cat["hp"]) * ratio))
        atk0 = max(1, int(float(cat["atk"]) * ratio))
        def0 = max(0, int(float(cat["def"]) * ratio))
        mult_hp = 1.0
        mult_atk = 1.0
        if spawn.is_elite:
            mult_hp *= MONSTER_MULT_ELITE_HP
            mult_atk *= MONSTER_MULT_ELITE_ATK
        if spawn.is_mini_boss:
            mult_hp *= MONSTER_MULT_MINI_HP
            mult_atk *= MONSTER_MULT_MINI_ATK
        if spawn.is_major_boss:
            mult_hp *= MONSTER_MULT_MAJOR_HP
            mult_atk *= MONSTER_MULT_MAJOR_ATK
        if floor_number >= MONSTER_LATE_FLOOR_THRESHOLD:
            mult_hp *= MONSTER_LATE_HP_MULT
            mult_atk *= MONSTER_LATE_ATK_MULT

        atk_scaled = max(1, int(atk0 * mult_atk))
        atk_scaled += MONSTER_ATK_FLAT_ELITE if spawn.is_elite else MONSTER_ATK_FLAT_NORMAL
        hp_out = max(1, int(hp0 * mult_hp))
        atk_out = atk_scaled
        def_out = max(0, int(def0 * mult_hp))

        if int(floor_number) == 10 and spawn.is_major_boss:
            m10 = float(MONSTER_FLOOR10_MAJOR_BOSS_MULT)
            hp_out = max(1, int(hp_out * m10))
            atk_out = max(1, int(atk_out * m10))
            def_out = max(0, int(def_out * m10))

        if (
            int(floor_number) == 20
            and spawn.is_major_boss
            and tpl_key == MONSTER_FLOOR20_SLIME_KING_TEMPLATE_KEY
        ):
            msk = float(MONSTER_FLOOR20_SLIME_KING_STAT_MULT)
            hp_out = max(1, int(hp_out * msk))
            atk_out = max(1, int(atk_out * msk))
            def_out = max(0, int(def_out * msk))

        if int(floor_number) == 5 and spawn.is_mini_boss:
            hp_out = max(1, min(int(hp_out), int(MONSTER_FLOOR5_MINIBOSS_HP_CAP)))

    ail_mult, ail_lab, ail_em = monster_strike_ailment(floor_number, spawn)
    display_name = str(cat.get("name") or spawn.template.name).strip()
    elem = str(cat.get("element") or spawn.template.element or "earth")
    phrases = cat.get("phrases") if isinstance(cat.get("phrases"), list) else []
    skills = cat.get("skills") if isinstance(cat.get("skills"), list) else []

    bundle: dict[str, Any] = {
        "name": display_name,
        "emoji": spawn.template.emoji,
        "template_key": tpl_key,
        "hp": hp_out,
        "max_hp": hp_out,
        "atk": atk_out,
        "defense": def_out,
        "element": elem,
        "strike_ailment_mult": ail_mult,
        "strike_ailment_label_ru": ail_lab,
        "strike_ailment_emoji": ail_em,
        "catalog_phrases": [str(p) for p in phrases if p],
        "catalog_skills": skills,
        "catalog_loot_table": str(cat.get("loot_table") or ""),
        "from_catalog": True,
    }
    if (
        int(floor_number) == 20
        and spawn.is_major_boss
        and tpl_key == MONSTER_FLOOR20_SLIME_KING_TEMPLATE_KEY
    ):
        bundle["armor_penetration"] = float(MONSTER_FLOOR20_SLIME_KING_ARMOR_PENETRATION)
        bundle["applies_poison_on_hit"] = True
    return bundle


def _monster_stat_bundle(
    floor_number: int,
    spawn: FloorMonsterSpawn,
) -> dict[str, Any]:
    """HP/атака/защита: каталог (.py) или общая формула monster_stat_formula."""
    cat = monster_catalog_mod.get_definition(str(spawn.template.key or ""))
    if cat and monster_catalog_mod.has_explicit_stats(cat):
        return _monster_stat_bundle_from_catalog(floor_number, spawn, cat)
    return compute_formula_stat_bundle(floor_number, spawn)


async def _weapon_profile(
    session: AsyncSession,
    character: Character,
) -> tuple[int, str, float, dict | None]:
    """Атака оружия (основная + вторая рука, если там оружие с атакой), тип мастерства с основной руки."""
    weapon = await inventory_repo.get_equipped_weapon(session, character.id)
    off = await inventory_repo.get_equipped_in_slot(session, int(character.id), "offhand")
    lv = int(character.level)
    fl = int(character.floor_number)

    off_atk = 0
    off_data: dict | None = dict(off.item_data or {}) if off else None
    if off_data:
        oa = int(off_data.get("attack", off_data.get("atk", 0)) or 0)
        if oa > 0:
            off_atk = character_service.weapon_attack_value_from_item_data(off_data, level=lv, floor_number=fl)

    if weapon is None:
        if off_atk > 0 and off_data is not None:
            wtype = weapon_type_from_item_data(off_data)
            return off_atk, wtype, damage_multiplier_for_type(character, wtype), off_data
        atk = character_service.weapon_attack_value_from_item_data(None, level=lv, floor_number=fl)
        wtype = "unarmed"
        return atk, wtype, damage_multiplier_for_type(character, wtype), None

    data = dict(weapon.item_data or {})
    main_atk = character_service.weapon_attack_value_from_item_data(data, level=lv, floor_number=fl)
    atk = main_atk + off_atk
    wtype = weapon_type_from_item_data(data)
    return atk, wtype, damage_multiplier_for_type(character, wtype), data


def _apply_weapon_runes_to_state(
    combat_state: dict[str, Any],
    character: Character,
    weapon_item_data: dict | None,
) -> None:
    """Бонусы рун с надетого оружия: урон, крит, защита, полезная нагрузка для статусов."""
    from game.items.runes import (
        calculate_elemental_bonus,
        parse_weapon_runes,
        rune_combat_extras,
        total_weapon_rune_flat_elemental_damage,
    )

    runes_list = parse_weapon_runes(weapon_item_data)
    mon_el = str(combat_state.get("monster", {}).get("element") or "earth")
    pct = calculate_elemental_bonus(runes_list, mon_el, character.element)
    combat_state["weapon_rune_flat_elemental"] = int(total_weapon_rune_flat_elemental_damage(runes_list))
    loc_rune = get_locale(character, None)
    if pct >= 30:
        _append_logs(combat_state, [t(loc_rune, "combat_rune_weak_spot", pct=int(pct))])
    elif pct >= 15:
        _append_logs(combat_state, [t(loc_rune, "combat_rune_elemental_hit", pct=int(pct))])
    ex = rune_combat_extras(runes_list)
    combat_state["weapon_rune_bonus_pct"] = int(pct)
    combat_state["rune_crit_damage_bonus_percent"] = int(ex.get("crit_damage_bonus_percent", 0))
    combat_state["rune_armor_mult"] = float(ex.get("armor_mult", 1.0))
    combat_state["weapon_rune_payloads"] = [r.as_dict() for r in runes_list]
    combat_state["rune_synergy_name"] = str(ex.get("synergy_name") or "")


async def _equipped_gear_defense_total(session: AsyncSession, character_id: int) -> int:
    """Сумма defense с надетых предметов; заточка даёт +5%/ур. к scaled защите."""
    items = await inventory_repo.list_equipped_items(session, character_id)
    total = 0
    for it in items:
        data = it.item_data or {}
        base_def = int(data.get("defense", data.get("armor", 0)) or 0)
        def_val = scaled_armor_defense_value(base_def, data)
        ench = enchant_rules.current_enchant_level(data)
        mult = enchant_rules.enchant_stat_multiplier(ench)
        total += max(0, int(round(def_val * mult)))
    return total


def _build_combat_dict(
    character: Character,
    spawn: FloorMonsterSpawn,
    monster: dict[str, Any],
    *,
    primary_stats: dict[str, int] | None = None,
) -> dict[str, Any]:
    mods = passive_combat_modifiers_merged(character)
    if primary_stats is None:
        st = {
            "str": int(character.stat_strength),
            "dex": int(character.stat_dexterity),
            "int": int(character.stat_intelligence),
            "vit": int(character.stat_vitality),
            "luck": int(character.stat_luck),
        }
    else:
        st = {k: int(primary_stats[k]) for k in ("str", "dex", "int", "vit", "luck")}
    state: dict[str, Any] = {
        "monster": monster,
        "floor": character.floor_number,
        "spawn_slot": spawn.slot_code,
        "class_key": character.class_key,
        "combat_skill_class_key": profession_service.combat_skill_class_key(character),
        "stats": st,
        "player_hp": character.hp_current,
        "player_hp_max": character.hp_max,
        "player_mp": character.mp_current,
        "player_mp_max": character.mp_max,
        "weapon_attack": 0,
        "skill_cd": {"0": 0, "1": 0, "2": 0},
        "monster_turn": 0,
        "monster_special_cd": 0,
        "monster_phase": 1,
        "monster_fortify_flat": 0,
        "monster_fortify_turns": 0,
        "passive_mods": mods,
        "ui_logs": [],
        "weapon_mastery_mult": 1.0,
        "player_weapon_type": "blade",
        "mastery_strike_pending": False,
        "tutorial_phase": 0,
        "weapon_rune_bonus_pct": 0,
        "weapon_rune_flat_elemental": 0,
        "rune_crit_damage_bonus_percent": 0,
        "rune_armor_mult": 1.0,
        "weapon_rune_payloads": [],
        "rune_synergy_name": "",
        "player_level_def_bonus": max(0, int(character.level) - 1) * int(PLAYER_DEFENSE_BONUS_PER_LEVEL),
        "battle_taunt_html": "",
        "combo_streak": 0,
        "combo_next_mult": 1.0,
        "night_battle": False,
        "player_last_damage_to_monster": None,
        "monster_last_damage_to_player": None,
    }
    ensure_skill_meta(character)
    state["combat_skills"] = battle_skills_tuple(character)
    effects.init_effects(state)
    loc_battle = get_locale(character, None)
    pet_base = pets_mod.format_pet_battle_line_html(character, locale=loc_battle)
    state["pet_line_html"] = pet_base or ""
    return state


def format_battle_view(state: dict[str, Any], _class_name_ru: str) -> str:
    """Экран боя: этаж, враг (полосы, баффы), игрок, лог с репликой монстра."""
    m = state["monster"]
    monster_ai.sync_monster_rage_visual(state)

    elem = m.get("element", "earth")
    elem_icons = {
        "fire": "🔥",
        "ice": "❄️",
        "lightning": "⚡",
        "dark": "🌑",
        "light": "✨",
        "earth": "🌿",
        "poison": "☠️",
    }
    el_icon = elem_icons.get(str(elem).lower(), "🌀")

    name_esc = html.escape(str(m.get("name", "Враг")))
    if m.get("is_major_boss"):
        enemy_line = f"👑 <b>{name_esc}</b> {el_icon} <i>(Босс)</i>"
    elif m.get("is_mini_boss"):
        enemy_line = f"👑 <b>{name_esc}</b> {el_icon} <i>(Мини-босс)</i>"
    elif m.get("is_elite"):
        enemy_line = f"⭐ <b>{name_esc}</b> {el_icon} <i>(Элита)</i>"
    else:
        enemy_line = f"{html.escape(str(m.get('emoji', '👹')))} <b>{name_esc}</b> {el_icon}"

    hp_mon = render_hp_bar(
        int(m["hp"]),
        int(m["max_hp"]),
        wrap_bar_in_code=False,
        spaced_numbers=True,
    )
    mp_line = render_mp_bar(
        int(state["player_mp"]),
        int(state["player_mp_max"]),
        wrap_bar_in_code=False,
        spaced_numbers=True,
    )
    php_line = render_hp_bar(
        int(state["player_hp"]),
        int(state["player_hp_max"]),
        wrap_bar_in_code=False,
        spaced_numbers=True,
    )

    buff_parts: list[str] = []
    ph = int(state.get("monster_phase", 1))
    if (m.get("is_mini_boss") or m.get("is_major_boss")) and ph >= 3:
        buff_parts.append("💀 Фаза 3 (+50% урон)")
    elif (m.get("is_mini_boss") or m.get("is_major_boss")) and ph >= 2:
        buff_parts.append("⚡️ Фаза 2")
    if state.get("monster_rage"):
        buff_parts.append("💢 Ярость (+30%)")
    if float(state.get("monster_outgoing_mult", 1.0)) < 1.0 and int(state.get("monster_debuff_turns", 0)) > 0:
        buff_parts.append(f"🌫️ Слабость ({int(state['monster_debuff_turns'])} х.)")
    buff_line = ""
    if buff_parts:
        buff_line = "Баффы: " + " | ".join(buff_parts) + "\n"

    taunt_raw = str(state.get("battle_taunt_html") or "").strip()

    shield_p = ""
    sh_val = int(state.get("player_shield_hp", 0))
    if sh_val > 0:
        shield_p = f"🛡️ Щит: <b>{sh_val}</b>\n"

    pet_p = ""
    pl = state.get("pet_line_html")
    if pl:
        pet_p = f"{pl}\n"

    logs = list(state.get("ui_logs", []) or [])
    log_lines = "\n".join(logs) if logs else ""
    taunt_line = ""
    if taunt_raw:
        taunt_line = taunt_raw if taunt_raw.startswith("💬") else f"💬 «{taunt_raw}»"
    if log_lines and taunt_line:
        log_block = f"{log_lines}\n{taunt_line}"
    elif log_lines:
        log_block = log_lines
    elif taunt_line:
        log_block = taunt_line
    else:
        log_block = ""

    fln = int(state.get("floor", 0))
    sep = LINE_SEP_BATTLE
    night_note = ""
    if state.get("night_battle"):
        night_note = (
            "<i>🌑 Ночь UTC: враг +20% HP/ATK, победа +40% золото и опыт.</i>\n"
        )

    title = f"⚔️ <b>Этаж {fln}</b>"
    if state.get("night_battle"):
        title += " 🌑"

    log_section = f"{sep}\n{log_block}" if log_block else ""
    return (
        f"{title}\n"
        f"{night_note}"
        f"{enemy_line}\n"
        f"{hp_mon}\n"
        f"{buff_line}"
        f"\n"
        f"{php_line}\n"
        f"{mp_line}\n"
        f"{shield_p}"
        f"{pet_p}"
        f"{log_section}"
    )


def _append_logs(state: dict[str, Any], lines: list[str]) -> None:
    """Добавить строки в лог текущего хода (перед новым ходом список обнуляется в handle_combat_callback)."""
    if not lines:
        return
    buf = list(state.get("ui_logs", []) or [])
    buf.extend(lines)
    state["ui_logs"] = buf


async def start_combat(
    *,
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    character: Character,
    spawn: FloorMonsterSpawn,
) -> bool:
    """Начать бой. True если бой начат."""
    if not can_start_combat(character, settings.MAX_STAMINA):
        await query.answer("Недостаточно стамины (нужна 1).", show_alert=True)
        return False

    if rest_service.apply_completed_rest_if_needed(character):
        await session.flush()
    if rest_service.is_rest_in_progress(character):
        left = rest_service.rest_seconds_left(character)
        await query.answer(
            f"Передышка: подожди ещё ~{left} с (полные HP/MP после отдыха).",
            show_alert=True,
        )
        return False

    current_state = await state.get_state()
    if current_state == CombatStates.in_battle.state:
        await query.answer("Ты уже в бою.", show_alert=True)
        return False

    spent = await spend_stamina(session, int(character.id))
    if not spent:
        await query.answer("Не удалось списать стамину. Попробуй ещё раз.", show_alert=True)
        return False
    await session.refresh(character)
    if pets_mod.repair_pet_meta_if_needed(character):
        await session.flush()

    swamp_prefight_logs: list[str] = []
    if rotten_swamps_mod.is_rotten_swamps_zone(int(character.floor_number)):
        def_tot = await _equipped_gear_defense_total(session, character.id)
        if def_tot >= 5:
            swamp_prefight_logs.append(
                "🧪 <b>Токсичный туман:</b> яд не пробивает твою броню "
                f"(защита снаряжения <b>{def_tot}</b> ≥ 5).",
            )
        else:
            character.hp_current = max(1, int(character.hp_current) - 5)
            swamp_prefight_logs.append("🧪 <b>Токсичный туман:</b> −5 HP до боя.")
        await session.flush()

    if query.from_user is not None:
        await anticheat_service.record_fight_start(
            session,
            character,
            telegram_id=query.from_user.id,
            username=query.from_user.username,
            bot=query.bot,
        )

    monster = _monster_stat_bundle(character.floor_number, spawn)
    monster["is_elite"] = spawn.is_elite
    monster["is_mini_boss"] = spawn.is_mini_boss
    monster["is_major_boss"] = spawn.is_major_boss
    monster["is_milestone_boss"] = spawn.is_major_boss and floor_data.is_tower_milestone_boss_floor(
        int(character.floor_number),
    )
    night_on = combat_night.is_night_utc()
    if night_on:
        combat_night.apply_night_to_monster_bundle(monster)

    await character_service.refresh_hp_mp_from_effective(session, character)
    await session.flush()

    eff_stats = await stat_bonus_service.effective_primary_stats(session, character)
    combat_state = _build_combat_dict(character, spawn, monster, primary_stats=eff_stats)
    combat_state["night_battle"] = night_on
    if str(spawn.slot_code) == golden_goblin_service.SLOT_CODE:
        combat_state["golden_goblin_wave"] = await golden_goblin_service.current_wave(session)
    wa, wtype, wmult, w_item = await _weapon_profile(session, character)
    combat_state["weapon_attack"] = wa
    combat_state["player_weapon_type"] = wtype
    combat_state["weapon_mastery_mult"] = wmult
    combat_state["player_equipment_defense"] = await _equipped_gear_defense_total(session, character.id)
    _apply_weapon_runes_to_state(combat_state, character, w_item)

    if swamp_prefight_logs:
        _append_logs(combat_state, swamp_prefight_logs)

    leech_tgt = rotten_swamps_mod.get_leech_target_floor(character)
    if leech_tgt is not None and int(character.floor_number) == leech_tgt:
        effects.add_effect(
            "player",
            combat_state,
            "Пиявки (заражение)",
            "poison",
            4,
            {"potency_percent": 4},
        )
        rotten_swamps_mod.clear_leech_target(character)
        _append_logs(
            combat_state,
            ["🪱 <b>Пиявки:</b> яд с прошлого этажа — бой начинается с <b>ядом</b>."],
        )
        await session.flush()

    taunt = engine.opening_taunt(combat_state)
    combat_state["battle_taunt_html"] = _taunt_banner_html(taunt)

    await game_metrics_service.record_event(
        session,
        event_type="combat_start",
        floor=int(character.floor_number),
        class_key=str(character.class_key or ""),
    )

    await state.set_state(CombatStates.in_battle)
    await state.update_data(combat=combat_state)

    cls = get_class_or_none(character.class_key)
    class_ru = cls.name_ru if cls else character.class_key
    text = format_battle_view(combat_state, class_ru)
    kb = combat_main_keyboard(character)

    if query.message is None:
        await state.clear()
        await session.execute(
            update(Character)
            .where(Character.id == int(character.id))
            .values(stamina=Character.stamina + 1),
        )
        await session.refresh(character)
        if query.from_user is not None:
            combat_idle_service.cancel_combat_idle_timer(int(query.from_user.id))
        await query.answer()
        return False

    tpl_key = str(monster.get("template_key") or "")
    battle_photo = (
        combat_monster_portrait_path(tpl_key)
        if game_images_enabled(character)
        else None
    )

    try:
        opened_with_portrait = False
        if battle_photo is not None:
            try:
                cap = _clamp_battle_caption(text)
                await push_game_ui(
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    text=cap,
                    reply_markup=kb,
                    target_message=query.message,
                    photo_path=battle_photo,
                )
                data = await state.get_data()
                mid = data.get(GAME_UI_MESSAGE_ID)
                cid = data.get(GAME_UI_CHAT_ID)
                if mid is not None and cid is not None:
                    await state.update_data(
                        combat_message_id=int(mid),
                        combat_chat_id=int(cid),
                        combat_ui_is_photo=True,
                    )
                    opened_with_portrait = True
            except Exception:
                logger.exception("start_combat: портрет монстра — откат на текст")
        if not opened_with_portrait:
            try:
                ok = await _safe_edit_combat_message_text(state, query.message, text, reply_markup=kb)
            except TelegramBadRequest:
                logger.warning("Не удалось отредактировать сообщение этажа — замена через якорь UI.")
                ok = False
            if ok:
                await state.update_data(
                    combat_message_id=query.message.message_id,
                    combat_chat_id=query.message.chat.id,
                    combat_ui_is_photo=False,
                )
            else:
                await push_game_ui(
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    text=text,
                    reply_markup=kb,
                    target_message=query.message,
                    photo_path=None,
                )
                data = await state.get_data()
                mid = data.get(GAME_UI_MESSAGE_ID)
                cid = data.get(GAME_UI_CHAT_ID)
                if mid is not None and cid is not None:
                    await state.update_data(
                        combat_message_id=int(mid),
                        combat_chat_id=int(cid),
                        combat_ui_is_photo=False,
                    )
        if query.from_user is not None:
            await combat_idle_service.arm_combat_idle_after_player_turn(
                bot=query.bot,
                state=state,
                telegram_user_id=int(query.from_user.id),
            )
        await query.answer("Бой!")
        return True
    except Exception:
        logger.exception("start_combat: UI после входа в бой")
        await state.clear()
        await session.execute(
            update(Character)
            .where(Character.id == int(character.id))
            .values(stamina=Character.stamina + 1),
        )
        await session.refresh(character)
        if query.from_user is not None:
            combat_idle_service.cancel_combat_idle_timer(int(query.from_user.id))
        try:
            await query.answer(
                "Не удалось открыть экран боя. Стамина возвращена — открой этаж снова.",
                show_alert=True,
            )
        except Exception:
            pass
        return False


async def start_tutorial_combat(
    *,
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    character: Character,
) -> bool:
    """Разовый учебный бой на 1 этаже. Стамину не тратит."""
    if int(character.floor_number) != 1:
        await query.answer("Обучение только на первом этаже.", show_alert=True)
        return False
    if not tutorial_battle_pending(character):
        await query.answer("Ты уже прошёл обучение у наставника.", show_alert=True)
        return False

    if rest_service.apply_completed_rest_if_needed(character):
        await session.flush()
    if rest_service.is_rest_in_progress(character):
        left = rest_service.rest_seconds_left(character)
        await query.answer(
            f"Передышка: подожди ещё ~{left} с.",
            show_alert=True,
        )
        return False

    if await state.get_state() == CombatStates.in_battle.state:
        await query.answer("Ты уже в бою.", show_alert=True)
        return False

    monster = _tutorial_monster_bundle()
    await character_service.refresh_hp_mp_from_effective(session, character)
    await session.flush()

    eff_stats = await stat_bonus_service.effective_primary_stats(session, character)
    combat_state = _build_combat_dict(character, TUTORIAL_SPAWN, monster, primary_stats=eff_stats)
    wa, wtype, wmult, w_item = await _weapon_profile(session, character)
    combat_state["weapon_attack"] = wa
    combat_state["player_weapon_type"] = wtype
    combat_state["weapon_mastery_mult"] = wmult
    _apply_weapon_runes_to_state(combat_state, character, w_item)
    combat_state["player_equipment_defense"] = await _equipped_gear_defense_total(session, character.id)
    combat_state["is_tutorial"] = True
    combat_state["night_battle"] = False
    combat_state["tutorial_phase"] = 1
    combat_state["tutorial_player_rounds"] = 0
    combat_state["tutorial_used_skill"] = False
    combat_state["battle_taunt_html"] = _taunt_banner_html(engine.opening_taunt(combat_state))
    prelude = list(combat_state.get("ui_logs", []))
    combat_state["ui_logs"] = prelude + [
        "🎓 <b>Наставник Зарен:</b> «Два раунда. Первый — разминка, второй — давление. "
        "Смотрю на скорость, осторожность и используешь ли навык не только автоударами».",
        "🌀 <i>По периметру круга встаёт первый манекен — дерево и железо скрипят.</i>",
    ]

    await state.set_state(CombatStates.in_battle)
    await state.update_data(combat=combat_state)

    cls = get_class_or_none(character.class_key)
    class_ru = cls.name_ru if cls else character.class_key
    text = format_battle_view(combat_state, class_ru)
    kb = combat_main_keyboard(character)

    if query.message is None:
        await state.clear()
        if query.from_user is not None:
            combat_idle_service.cancel_combat_idle_timer(int(query.from_user.id))
        await query.answer()
        return False

    try:
        ok = await _safe_edit_combat_message_text(state, query.message, text, reply_markup=kb)
    except TelegramBadRequest:
        logger.warning("Не удалось отредактировать сообщение (учебный бой) — замена через якорь UI.")
        ok = False
    try:
        if ok:
            await state.update_data(
                combat_message_id=query.message.message_id,
                combat_chat_id=query.message.chat.id,
                combat_ui_is_photo=False,
            )
        else:
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=text,
                reply_markup=kb,
                target_message=query.message,
                photo_path=None,
            )
            data = await state.get_data()
            mid = data.get(GAME_UI_MESSAGE_ID)
            cid = data.get(GAME_UI_CHAT_ID)
            if mid is not None and cid is not None:
                await state.update_data(
                    combat_message_id=int(mid),
                    combat_chat_id=int(cid),
                    combat_ui_is_photo=False,
                )
        if query.from_user is not None:
            await combat_idle_service.arm_combat_idle_after_player_turn(
                bot=query.bot,
                state=state,
                telegram_user_id=int(query.from_user.id),
            )
        await query.answer("Учебный бой!")
        return True
    except Exception:
        logger.exception("start_tutorial_combat: UI после входа в учебный бой")
        await state.clear()
        if query.from_user is not None:
            combat_idle_service.cancel_combat_idle_timer(int(query.from_user.id))
        try:
            await query.answer(
                "Не удалось начать учебный бой. Открой этаж снова (/floor).",
                show_alert=True,
            )
        except Exception:
            pass
        return False


async def _apply_tower_progress_after_victory(
    session: AsyncSession,
    character: Character,
    spawn: FloorMonsterSpawn,
) -> str:
    """
    Учёт посещений, флаги боссов, слоты поверженных врагов.
    Когда побеждены все цели этажа — подъём на следующий (кроме финала 100).
    """
    cur = int(character.floor_number)
    row = await floor_progress_repo.ensure_floor_row(session, character.id, cur)
    row.visits = int(row.visits) + 1

    if spawn.is_major_boss:
        row.boss_defeated = True
    if spawn.is_mini_boss:
        row.mini_boss_defeated = True

    extra = dict(row.extra or {})
    cleared: list[str] = list(extra.get("slots_cleared", []))

    # Этаж 8: бой-исследование инкрементирует счётчик (не добавляется в slots_cleared как обычный слот)
    if spawn.slot_code == explore_floor_mod.SLOT_ENCOUNTER:
        extra = explore_floor_mod.increment_explore_count(extra)
        extra["slots_cleared"] = cleared
        row.extra = extra
        await session.flush()
        return ""

    if spawn.slot_code not in cleared:
        cleared.append(spawn.slot_code)
    extra["slots_cleared"] = cleared
    row.extra = extra

    all_spawns = long_floor_mod.spawns_for_tower_progress(character, cur)
    needed = {s.slot_code for s in all_spawns}
    # needed.issubset(cleared) == True только когда ВСЕ нужные слоты зачищены.
    # Старый вариант (set(cleared) < needed) давал False при любом «чужом» слоте
    # (напр. "gg" золотого гоблина), что ошибочно триггерило подъём на следующий этаж.
    if not needed.issubset(set(cleared)):
        return ""

    if cur >= 100:
        character.highest_floor_reached = max(int(character.highest_floor_reached), 100)
        extra["slots_cleared"] = []
        row.extra = extra
        return "\n👁️ <b>Вершина башни:</b> страж повержен."

    from game.floors.tower_ascent import set_tower_ascent_pending

    nxt = cur + 1
    set_tower_ascent_pending(character, nxt)
    character.highest_floor_reached = max(int(character.highest_floor_reached), nxt)
    extra["slots_cleared"] = []
    # Сбрасываем прогресс исследования при подъёме с 8-го этажа
    if cur == explore_floor_mod.EXPLORE_FLOOR:
        extra = explore_floor_mod.reset_explore_state(extra)
    row.extra = extra
    zone_next = floor_data.get_zone_for_floor(nxt)
    room_next = floor_data.epithet_for_floor(zone_next, nxt)
    return (
        f"\n🪜 <b>Этаж зачищен!</b>\n"
        f"Поднимись на <b>{nxt}</b> / 100 — <i>{html.escape(room_next)}</i> "
        f"(кнопка «Следующий этаж» или ⬆️ Выше).\n"
        f"<i>{html.escape(zone_next.description)}</i>"
    )


async def _flush_weapon_mastery(
    session: AsyncSession,
    character: Character,
    combat_state: dict[str, Any],
) -> None:
    if not combat_state.pop("mastery_strike_pending", False):
        return
    wt = str(combat_state.get("player_weapon_type") or "blade")
    record_strike(character, wt)
    combat_state["weapon_mastery_mult"] = damage_multiplier_for_type(character, wt)
    await session.flush()


async def _after_monster_killed_player_action(
    *,
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    character: Character,
    combat_state: dict[str, Any],
    class_ru: str,
) -> bool:
    """True если бой продолжается (2-я волна учебного боя)."""
    if query.message is None:
        return False
    await _flush_weapon_mastery(session, character, combat_state)
    if combat_state.get("is_tutorial") and int(combat_state.get("tutorial_phase", 1)) < 2:
        combat_state["tutorial_phase"] = 2
        combat_state["monster"] = _tutorial_monster_wave2()
        combat_state["monster_turn"] = 0
        combat_state["monster_special_cd"] = 0
        combat_state["monster_effects"] = []
        combat_state["monster_skip_next"] = False
        combat_state["monster_def_mod"] = 0
        combat_state["player_last_damage_to_monster"] = None
        combat_state["monster_last_damage_to_player"] = None
        combat_state["battle_taunt_html"] = _taunt_banner_html(engine.opening_taunt(combat_state))
        combat_state["ui_logs"] = [
            "⚡ <b>Вторая фаза.</b> Наставник швыряет в круг второго манекена — он бьёт сильнее!",
        ]
        if query.message:
            try:
                await _safe_edit_combat_message_text(
                    state,
                    query.message,
                    format_battle_view(combat_state, class_ru),
                    reply_markup=combat_main_keyboard(character),
                )
            except Exception:
                logger.exception("edit tutorial wave2")
        await state.update_data(combat=combat_state)
        await query.answer()
        return True
    await _victory_sequence(
        message=query.message,
        state=state,
        session=session,
        character=character,
        combat_state=combat_state,
    )
    return False


async def _victory_sequence(
    *,
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    character: Character,
    combat_state: dict[str, Any],
) -> None:
    """Анимация полосы награды и начисление."""
    if combat_state.get("is_tutorial"):
        rounds = int(combat_state.get("tutorial_player_rounds", 0))
        used_skill = bool(combat_state.get("tutorial_used_skill"))
        php = int(combat_state["player_hp"])
        phm = int(combat_state["player_hp_max"])
        _key, skill_line = apply_path_rank_from_tutorial(
            character,
            player_rounds=max(1, rounds),
            hp_end=php,
            hp_max=phm,
            used_skill=used_skill,
        )
        r = PATH_RANK_BY_KEY.get(_key)
        rank_name = html.escape(r.name_ru) if r else html.escape(_key)
        bonus_gold = 18
        bonus_xp = 12
        character_service.add_gold(character, bonus_gold)
        if message.from_user is not None:
            await anticheat_service.record_gold_gain(
                session,
                character,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                gold_delta=bonus_gold,
                bot=message.bot,
            )
        await character_service.add_experience_async(session, character, bonus_xp, bot=message.bot)
        refresh_global_passives(character)
        character.hp_current = php
        character.mp_current = int(combat_state["player_mp"])
        fl = int(character.floor_number)
        floor_rows: list[list[InlineKeyboardButton]] = [
            [
                InlineKeyboardButton(
                    text="🗺️ На этаж",
                    callback_data=f"fl:{fl}:return",
                ),
            ],
            menu_nav_button_row(),
        ]
        victory_kb = InlineKeyboardMarkup(inline_keyboard=floor_rows)
        try:
            await _safe_edit_combat_message_text(
                state,
                message,
                f"🏆 <b>Учебный бой пройден!</b>\n"
                f"{LINE_SEP}\n"
                f"🎖️ <b>Звание башни</b> (не титул): {rank_name}\n"
                f"<i>{html.escape(skill_line)}</i>\n"
                f"{LINE_SEP}\n"
                f"💰 +{bonus_gold} золота · 📈 +{bonus_xp} опыта\n"
                f"Статы звания добавлены; его пассив суммируется с классом и глобальными бонусами.\n"
                f"🏆 Отдельные <b>титулы</b> выбираются в разделе «Титулы».",
                reply_markup=victory_kb,
            )
        finally:
            if message.from_user is not None:
                combat_idle_service.cancel_combat_idle_timer(int(message.from_user.id))
            await state.clear()
        return

    await character_repo.lock_character_row(session, character.id)

    spawn = _spawn_from_state(character, combat_state)
    battle_floor = int(combat_state.get("floor", character.floor_number))
    rotten_swamps_mod.maybe_roll_leech_infection_after_swamp_win(character, battle_floor)
    await session.flush()

    gg_first = False
    if str(spawn.template.key or "") == golden_goblin_service.TEMPLATE_KEY:
        gg_first = await golden_goblin_service.try_claim_first_blood(
            session, int(combat_state.get("golden_goblin_wave") or 0)
        )

    loc_victory = get_locale(character, message.from_user.language_code if message.from_user else None)

    if gg_first:
        gross_gold = random.randint(1000, 2000)
        xp = 1000
        ranker_note = ""
        escape_xp_note = ""
        night_reward_note = ""
        star_xp_note = ""
    else:
        gross_gold = gold_reward(character.floor_number, spawn)
        xp = experience_reward(character.floor_number, spawn)
        cat_win = monster_catalog_mod.get_definition(str(spawn.template.key or ""))
        if cat_win:
            cg, cx = monster_catalog_mod.scaled_gold_exp(cat_win, battle_floor)
            if cg is not None:
                gross_gold = cg
            if cx is not None:
                xp = cx
        if combat_state.get("night_battle"):
            gross_gold = int(gross_gold * combat_night.REWARD_MULT)
            xp = int(xp * combat_night.REWARD_MULT)
        gm, xm = title_service.reward_bonus_multipliers(character)
        esc_m = sink_rules.pop_next_win_xp_multiplier(character)
        mp_xp = dict(character.meta_progress or {})
        star_xp_mult = float(mp_xp.pop("next_battle_xp_mult", 1.0) or 1.0)
        character.meta_progress = mp_xp
        gross_gold = int(gross_gold * gm)
        rank_gm, rank_xm, ranker_note_html = await leaderboard_service.victory_rank_reward_multipliers(
            session,
            character,
            locale=loc_victory,
        )
        gross_gold = int(round(gross_gold * rank_gm))
        ranker_note = ("\n" + ranker_note_html) if ranker_note_html else ""
        xp = int(xp * xm * rank_xm * esc_m * max(0.1, star_xp_mult))
        # Бонусы дома
        try:
            from services.home_service import home_gold_bonus_pct, home_xp_bonus_pct
            _hg = home_gold_bonus_pct(character)
            _hx = home_xp_bonus_pct(character)
            if _hg > 0:
                gross_gold = int(round(gross_gold * (1.0 + _hg)))
            if _hx > 0:
                xp = int(round(xp * (1.0 + _hx)))
        except Exception:
            pass
        escape_xp_note = ""
        if esc_m < 0.999:
            escape_xp_note = (
                f"\n<i>Опыт со скидкой {int(round((1.0 - esc_m) * 100))}% "
                f"(недавний побег).</i>"
            )
        night_reward_note = ""
        if combat_state.get("night_battle"):
            night_reward_note = "\n<i>🌙 Ночной бой: к золоту и опыту уже учтён бонус +40%.</i>"
        star_xp_note = ""
        if star_xp_mult >= 1.45:
            star_xp_note = "\n<i>⭐ Упавшая звезда: опыт этого боя ×1.5.</i>"

    gg_kill_note = ""
    if str(spawn.template.key or "") == golden_goblin_service.TEMPLATE_KEY:
        if gg_first:
            gg_kill_note = "\n🥇 <b>Мировой бонус:</b> ты первый, кто поймал золотого гоблина в этой волне!"
        else:
            gg_kill_note = "\n<i>Гоблин уже был обчищен другим героем — обычная добыча.</i>"

    if gg_first and message.bot is not None:
        from scheduler.tasks import broadcast_golden_goblin_slain

        asyncio.create_task(
            broadcast_golden_goblin_slain(
                message.bot,
                winner_display_name=str(character.display_name or "Герой"),
            )
        )

    net_gold, ml_debt_note = sink_rules.garnish_victory_gold_for_debt(character, gross_gold)

    character_service.add_gold(character, net_gold)
    if message.from_user is not None:
        await anticheat_service.record_gold_gain(
            session,
            character,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            gold_delta=net_gold,
            bot=message.bot,
        )
    levels_battle = await character_service.add_experience_async(session, character, xp, bot=message.bot)
    level_battle_suffix = character_service.level_up_notice_html(character, levels_battle)
    character.total_kills = int(character.total_kills) + 1
    daily_service.record_kill(character)
    # Вклад зависит от типа врага: обычный +1, элитный +3, босс +5/+10
    _clan_delta = 1
    if spawn.is_mini_boss:
        _clan_delta = 5
    elif spawn.is_major_boss:
        _clan_delta = 10
    elif spawn.is_elite:
        _clan_delta = 3
    await clan_service.on_monster_win_add_clan_xp(session, character, delta=_clan_delta)

    # Дроп клановых материалов: 🪵 с лесных/растительных, 🪨 с каменных/голем, 🌿 с болотных
    # Шансы повышены на ~35% относительно исходных
    try:
        _tkey2 = str(spawn.template.key or "")
        _mat_drop: str | None = None
        _mat_chance = 0.20  # базовый шанс: было 15% → 20%
        if spawn.is_major_boss:
            _mat_chance = 1.0   # боссы гарантированно дают
        elif spawn.is_mini_boss:
            _mat_chance = 0.65  # было 50% → 65%
        elif spawn.is_elite:
            _mat_chance = 0.40  # было 30% → 40%
        # Определяем тип материала по зоне монстра
        from game.data.monsters import KEY_TO_ZONE
        _zone = KEY_TO_ZONE.get(_tkey2, "")
        if _zone in ("forest_beginnings",) or "ent" in _tkey2 or "treant" in _tkey2 or "vine" in _tkey2:
            _mat_drop = "wood"
        elif _zone in ("shadow_caves", "volcanic_ruins") or "golem" in _tkey2 or "stone" in _tkey2 or "sentinel" in _tkey2:
            _mat_drop = "stone"
        elif _zone in ("rotten_swamps",) or "swamp" in _tkey2 or "troll" in _tkey2 or "bog" in _tkey2:
            _mat_drop = "herbs"
        # Монстры 5-го этажа (комнаты rc_*) тоже дают дерево
        elif str(spawn.slot_code or "").startswith("rc_r"):
            _mat_drop = "wood"
        if _mat_drop and random.random() < _mat_chance:
            if spawn.is_major_boss:
                _mat_amount = random.randint(5, 12)
            elif spawn.is_mini_boss:
                _mat_amount = random.randint(3, 7)
            else:
                _mat_amount = random.randint(1, 2)
            clan_service.add_material_drop(character, _mat_drop, _mat_amount)
            _mat_icons = {"wood": "🪵", "stone": "🪨", "herbs": "🌿"}
            _mat_note = f"\n{_mat_icons.get(_mat_drop, '📦')} +{_mat_amount} {_mat_drop} (клан)"
        else:
            _mat_note = ""
    except Exception:
        _mat_note = ""

    refresh_global_passives(character)

    if gg_first:
        extra_rune = ""
        dropped = False
        drop_label = ""
        extra_drop = ""
        extra_rune_item = ""
    else:
        if roll_rune_stone(spawn):
            character.rune_stones = int(character.rune_stones) + 1
            extra_rune = "\n⚗️ +1 рунный камень"
        else:
            extra_rune = ""

        dropped = False
        drop_label = ""
        _home_loot_extra = 0.0
        try:
            from services.home_service import home_loot_bonus_pct
            _home_loot_extra = home_loot_bonus_pct(character)
        except Exception:
            pass
        _luck = int(character.stat_luck or 0)
        _drop_triggered = roll_item_drop(spawn, int(character.floor_number), stat_luck=_luck) or (
            _home_loot_extra > 0 and random.random() < _home_loot_extra
        )
        if _drop_triggered:
            slot = await inventory_repo.first_free_bag_slot(session, character.id)
            if slot is not None:
                item_payload = loot_tables.roll_victory_item_payload(character.floor_number, spawn)
                await inventory_repo.add_bag_item(
                    session,
                    character.id,
                    item_payload,
                    bag_slot=slot,
                )
                dropped = True
                drop_label = str(item_payload.get("name", "Добыча"))

        extra_drop = ""
        if dropped:
            extra_drop = f"\n📦 <b>{html.escape(drop_label)}</b> — в сумку"

        extra_rune_item = ""
        boss_like = spawn.is_mini_boss or spawn.is_major_boss
        if spawn.is_elite or boss_like:
            rd = rune_items.roll_rune_drop(int(character.floor_number), boss_like)
            if rd is not None:
                slot_r = await inventory_repo.first_free_bag_slot(session, character.id)
                if slot_r is not None:
                    await inventory_repo.add_bag_item(
                        session,
                        character.id,
                        copy.deepcopy(rune_items.rune_item_payload(rd)),
                        bag_slot=slot_r,
                    )
                    extra_rune_item = f"\n💎 <b>{html.escape(rd.display_name)}</b> — в сумку"

        # Трофей босса: 5% шанс с монстров boss_* (нужен для улучшения дома 3-5 ур.)
        _tkey = str(spawn.template.key or "")
        if _tkey.startswith("boss_") and random.random() < 0.05:
            try:
                from services.forge_service import add_boss_trophy_to_bag
                await add_boss_trophy_to_bag(session, character.id, count=1)
                extra_rune_item += "\n🏆 <b>Трофей босса</b> — в сумку"
            except Exception:
                pass

    mname = html.escape(str(combat_state.get("monster", {}).get("name", "Враг")))
    floor_before = int(character.floor_number)
    old_highest_reached = int(character.highest_floor_reached)
    floor_banner = await _apply_tower_progress_after_victory(session, character, spawn)
    floor_after = int(character.floor_number)
    new_highest_reached = int(character.highest_floor_reached)
    await game_metrics_service.record_event(
        session,
        event_type="battle_win",
        floor=floor_before,
        class_key=str(character.class_key or ""),
    )
    if message.from_user is not None and floor_after != floor_before:
        await anticheat_service.record_floor_change(
            session,
            character,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            old_floor=floor_before,
            new_floor=floor_after,
            bot=message.bot,
        )
    await season_record_service.notify_if_first_to_floor_milestone_this_season(
        session,
        message.bot,
        character,
        old_highest=old_highest_reached,
        new_highest=new_highest_reached,
    )
    if spawn.slot_code in long_floor_mod.LONG_FLOOR_SLOTS:
        if spawn.slot_code == long_floor_mod.SLOT_BOSS:
            long_floor_mod.mark_completed(character)
        else:
            long_floor_mod.advance_phase_after_wave(character, spawn.slot_code)
    quest_suffix = await quest_service.apply_kill_progress(session, character)
    npc_done = await quest_service.update_kill_progress_from_spawn(session, character.id, spawn)
    if npc_done:
        quest_suffix += (
            "\n✅ <b>Задание выполнено!</b> Иди к NPC за наградой "
            "(раздел «Задания» или /quests)."
        )
    city_suffix = await city_quest_service.apply_kill_progress(session, character)
    new_titles = title_service.refresh_unlocks(character)
    title_suffix = ""
    if new_titles:
        label = "Новые титулы" if len(new_titles) > 1 else "Новый титул"
        title_suffix = f"\n🏆 <b>{label}:</b> " + html.escape(
            ", ".join(title_service.display_names(new_titles)),
        )

    pioneer_suffix = await floor10_pioneer_service.on_floor10_major_boss_victory(
        session,
        character,
        battle_floor=floor_before,
        spawn=spawn,
    )

    reward_frames = ("▓░░░░░░░░░", "▓▓▓▓▓░░░░░", "▓▓▓▓▓▓▓▓▓▓")
    is_golden_goblin = str(spawn.template.key or "") == golden_goblin_service.TEMPLATE_KEY
    fl = int(character.floor_number)
    floor_rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="🗺️ На этаж",
                callback_data=f"fl:{fl}:return",
            ),
        ],
        menu_nav_button_row(),
    ]
    victory_kb = InlineKeyboardMarkup(inline_keyboard=floor_rows)

    try:
        if is_golden_goblin:
            gold_gg = f"💰 +{net_gold} золота"
            if gross_gold != net_gold:
                gold_gg += f" <i>(до удержания долга: {gross_gold})</i>"
            gg_tail = (
                level_battle_suffix
                + quest_suffix
                + city_suffix
                + title_suffix
                + escape_xp_note
                + night_reward_note
                + star_xp_note
                + ranker_note
                + pioneer_suffix
                + gg_kill_note
                + _mat_note
            )
            gg_body = (
                "🏆 <b>Победа!</b> 💰 Золотой гоблин\n"
                "✨ Награда… ▓▓▓▓▓▓▓▓▓▓\n"
                f"{gold_gg}\n"
                f"📈 +{xp} опыта{extra_rune}{extra_drop}{extra_rune_item}"
            )
            if (floor_banner or "").strip():
                gg_body += floor_banner
            gg_body += f"{ml_debt_note}{gg_tail}"
            await _safe_edit_combat_message_text(
                state,
                message,
                gg_body,
                reply_markup=victory_kb,
            )
        else:
            await _safe_edit_combat_message_text(
                state,
                message,
                f"🏆 <b>Победа!</b> <b>{mname}</b>\n⚔️ <b>Удар!</b>",
                reply_markup=None,
            )
            await asyncio.sleep(0.6)
            await _safe_edit_combat_message_text(
                state,
                message,
                f"🏆 <b>Победа!</b> <b>{mname}</b>\n💀 <b>Монстр повержен!</b>",
                reply_markup=None,
            )
            await asyncio.sleep(0.5)

            for i, label in enumerate(reward_frames):
                is_last = i == len(reward_frames) - 1
                suffix = ""
                if is_last:
                    suffix = (
                        floor_banner
                        + level_battle_suffix
                        + quest_suffix
                        + city_suffix
                        + title_suffix
                        + escape_xp_note
                        + night_reward_note
                        + star_xp_note
                        + ranker_note
                        + pioneer_suffix
                        + gg_kill_note
                        + _mat_note
                    )
                gold_line = f"💰 +{net_gold} золота"
                if gross_gold != net_gold and is_last:
                    gold_line += f" <i>(до удержания долга: {gross_gold})</i>"
                await _safe_edit_combat_message_text(
                    state,
                    message,
                    f"🏆 <b>Победа!</b> <b>{mname}</b>\n✨ Награда… {label}\n"
                    f"{gold_line}\n"
                    f"📈 +{xp} опыта{extra_rune}{extra_drop}{extra_rune_item}"
                    f"{ml_debt_note if is_last else ''}{suffix}",
                    reply_markup=victory_kb if is_last else None,
                )
                await asyncio.sleep(0.8)
    except Exception:
        logger.exception("victory UI: анимация награды")
        # Гарантируем, что кнопки победы всегда появятся, даже если анимация упала
        try:
            await _safe_edit_combat_message_text(
                state,
                message,
                "🏆 <b>Победа!</b> Награда получена.",
                reply_markup=victory_kb,
            )
        except Exception:
            logger.debug("victory UI: резервная клавиатура не отображена")
    finally:
        await character_service.refresh_hp_mp_from_effective(session, character)
        character.hp_current = min(int(character.hp_max), int(combat_state["player_hp"]))
        character.mp_current = min(int(character.mp_max), int(combat_state["player_mp"]))
        if message.from_user is not None:
            combat_idle_service.cancel_combat_idle_timer(int(message.from_user.id))
        await state.clear()


def _spawn_from_state(character: Character, combat_state: dict[str, Any]) -> FloorMonsterSpawn:
    slot = str(combat_state.get("spawn_slot"))
    if slot == "tutorial":
        return TUTORIAL_SPAWN
    if slot == golden_goblin_service.SLOT_CODE:
        return golden_goblin_service.build_spawn()
    if slot in long_floor_mod.LONG_FLOOR_SLOTS:
        found_lf = long_floor_mod.spawn_by_slot(slot)
        if found_lf is not None:
            return found_lf
    battle_floor = int(combat_state.get("floor", character.floor_number))
    # Room-clear floors (rc_r0…rc_r4, rc_boss)
    if slot in room_clear_mod.ROOM_CLEAR_ALL_SLOTS:
        found_rc = room_clear_mod.spawn_by_slot(slot)
        if found_rc is not None:
            return found_rc
    # Wave floors (wv_w1, wv_w2, wv_w3, wv_boss)
    if slot in wave_floor_mod.WAVE_FLOOR_ALL_SLOTS:
        found_wv = wave_floor_mod.spawn_by_slot(slot)
        if found_wv is not None:
            return found_wv
    # Explore floor (exp_encounter, exp_boss)
    if slot in explore_floor_mod.EXPLORE_ALL_SLOTS:
        found_exp = explore_floor_mod.spawn_by_slot(slot)
        if found_exp is not None:
            return found_exp
    spawns = build_spawns_for_floor(battle_floor)
    found = next((s for s in spawns if s.slot_code == slot), None)
    if found is None:
        return spawns[0]
    return found


async def _defeat_sequence(
    *,
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    character: Character,
    combat_state: dict[str, Any] | None = None,
    banner_html: str = "",
) -> None:
    """Смерть: предмет, зачарование, счётчик. banner_html — префикс (AFK, фикс и т.п.)."""
    try:
        sk = state.key
        if sk is not None:
            combat_idle_service.cancel_combat_idle_timer(int(sk.user_id))
    except Exception:
        pass

    if combat_state and combat_state.get("is_tutorial"):
        await character_service.refresh_hp_mp_from_effective(session, character)
        character.hp_current = int(character.hp_max)
        character.mp_current = int(character.mp_max)
        loc = get_locale(character, None)
        fl_tut = 1
        revive_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t(loc, "combat_revive_btn"),
                        callback_data=f"fl:{fl_tut}:return",
                    ),
                ],
                menu_nav_button_row(),
            ],
        )
        tut_body = (
            (banner_html + "\n") if banner_html else ""
        ) + (
            "💠 <b>Учебный манекен</b> одержал верх — так и задумано.\n"
            "HP и MP восстановлены. Нажми кнопку ниже или снова открой "
            "<b>«Учебный бой наставника»</b> на этаже."
        )
        try:
            await _safe_edit_combat_message_text(
                state,
                message,
                tut_body,
                reply_markup=revive_kb,
            )
        finally:
            await state.clear()
        return

    await character_repo.lock_character_row(session, character.id)
    await session.refresh(character, attribute_names=["gold"])

    await character_service.refresh_hp_mp_from_effective(session, character)

    character.death_count = int(character.death_count) + 1
    title_service.refresh_unlocks(character)

    fl = int(character.floor_number)
    g = max(0, int(character.gold))
    if g <= 0:
        lost_gold = 0
    else:
        pct = float(DEATH_GOLD_LOSS_FRACTION)
        lost_gold = max(1, int(g * pct))
        lost_gold = min(lost_gold, g, int(MAX_DEATH_GOLD_LOSS))
    character.gold = max(0, g - lost_gold)

    weapon = await inventory_repo.get_equipped_weapon(session, character.id)
    enchant_msg = ""
    if weapon is not None and random.random() < 0.30:
        data = dict(weapon.item_data or {})
        ench = int(data.get("enchant", data.get("plus", 0)))
        if ench > 0:
            data["enchant"] = ench - 1
            weapon.item_data = data
            enchant_msg = f"\n⚠️ Заточка оружия снижена до +{ench - 1}."

    character.hp_current = max(1, int(character.hp_max * 0.4))
    character.mp_current = max(0, int(character.mp_max * 0.4))

    gold_line = (
        f"Потеряно золота: <b>{lost_gold}</b> 💰"
        if lost_gold > 0
        else "Золота не было — штраф только по HP/MP."
    )
    head = (banner_html + "\n") if banner_html else ""
    text = (
        f"{head}"
        "💀 Ты пал… Сброс на начало текущего этажа.\n"
        f"{gold_line}"
        f"{enchant_msg}"
    )
    loc = get_locale(character, None)
    defeat_rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=t(loc, "combat_revive_btn"),
                callback_data=f"fl:{fl}:return",
            ),
        ],
        menu_nav_button_row(),
    ]
    defeat_kb = InlineKeyboardMarkup(inline_keyboard=defeat_rows)
    try:
        await _safe_edit_combat_message_text(state, message, text, reply_markup=defeat_kb)
    finally:
        await state.clear()


async def _bag_combat_consumables(session: AsyncSession, character_id: int) -> list[InventoryItem]:
    """Предметы из сумки, применимые в бою."""
    bag = await inventory_repo.list_bag_items(session, character_id)
    out: list[InventoryItem] = []
    for it in bag:
        data = consumables.item_data_as_dict(it.item_data)
        if consumables.normalize_combat_use_tag(data) in consumables.COMBAT_USE_TAGS:
            out.append(it)
    out.sort(key=lambda x: (x.bag_slot is None, x.bag_slot or 0))
    return out


async def _apply_combat_item(
    session: AsyncSession,
    character: Character,
    combat_state: dict[str, Any],
    item_id: int,
) -> tuple[bool, str | None, list[str]]:
    item = await inventory_repo.get_item_for_character(session, character.id, item_id)
    if item is None or item.is_equipped or item.bag_slot is None:
        return False, "Предмета нет в сумке.", []
    data = consumables.item_data_as_dict(item.item_data)
    tag = consumables.normalize_combat_use_tag(data)
    if tag == "stamina_flat":
        return False, "Пайок ешь после боя.", []
    if tag not in consumables.COMBAT_USE_TAGS:
        return False, "Нельзя использовать в бою.", []
    try:
        logs = consumables.apply_consumable(combat_state, data)
    except ValueError:
        return False, "Предмет испорчен.", []
    await inventory_repo.delete_inventory_item(session, item)
    await session.flush()
    return True, None, logs


async def handle_combat_callback(
    *,
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    character: Character,
    action: str,
    skill_index: int | None,
    item_id: int | None = None,
) -> None:
    """Маршрутизация действий боя."""
    data = await state.get_data()
    combat_state: dict[str, Any] | None = data.get("combat")
    if combat_state is None:
        await query.answer("Нет активного боя.", show_alert=True)
        await state.clear()
        if query.from_user is not None:
            combat_idle_service.cancel_combat_idle_timer(int(query.from_user.id))
        return

    if query.message is None:
        await query.answer()
        return

    cls = get_class_or_none(character.class_key)
    class_ru = cls.name_ru if cls else character.class_key

    if action == "ret":
        await query.message.edit_reply_markup(reply_markup=combat_main_keyboard(character))
        if query.from_user is not None:
            await combat_idle_service.arm_combat_idle_after_player_turn(
                bot=query.bot,
                state=state,
                telegram_user_id=int(query.from_user.id),
            )
        await query.answer()
        return

    if action == "item":
        usable = await _bag_combat_consumables(session, character.id)
        if not usable:
            await query.answer("В сумке нет зелий для боя. Купи в лавке (этажи ×5 или город).", show_alert=True)
            if query.from_user is not None:
                await combat_idle_service.arm_combat_idle_after_player_turn(
                    bot=query.bot,
                    state=state,
                    telegram_user_id=int(query.from_user.id),
                )
            return
        await query.message.edit_reply_markup(reply_markup=combat_item_picker_keyboard(usable))
        if query.from_user is not None:
            await combat_idle_service.arm_combat_idle_after_player_turn(
                bot=query.bot,
                state=state,
                telegram_user_id=int(query.from_user.id),
            )
        await query.answer("Выбери предмет")
        return

    lines: list[str] = []
    failed_escape = False
    combat_state["ui_logs"] = []

    # Доты и пассивная регенерация MP в начале твоего хода
    lines.extend(engine.apply_dot_damage_player(combat_state))
    if int(combat_state["player_hp"]) <= 0:
        _append_logs(combat_state, lines)
        await _defeat_sequence(
            message=query.message,
            state=state,
            session=session,
            character=character,
            combat_state=combat_state,
        )
        await query.answer()
        return

    lines.extend(engine.regen_mp_passive(combat_state))

    outcome: engine.Outcome = "continue"
    skill_applied_outcome: engine.Outcome | None = None

    if action == "atk":
        atk_logs, outcome, phys_dmg = engine.player_attack(combat_state)
        lines.extend(atk_logs)
        if query.from_user is not None and phys_dmg > 0:
            st = combat_state["stats"]
            await anticheat_service.record_physical_damage(
                session,
                character,
                telegram_id=query.from_user.id,
                username=query.from_user.username,
                damage=int(phys_dmg),
                strength=int(st["str"]),
                weapon_atk=int(combat_state.get("weapon_attack", 0)),
                bot=query.bot,
            )
    elif action == "sk" and skill_index is not None:
        sk_logs, maybe, skill_dmg = engine.player_skill(combat_state, skill_index)
        lines.extend(sk_logs)
        skill_applied_outcome = maybe
        if maybe is None:
            outcome = "continue"
        else:
            outcome = maybe
        if skill_dmg > 0 and query.from_user is not None:
            sks = combat_state.get("combat_skills") or skills_for_class(
                str(combat_state.get("combat_skill_class_key") or character.class_key or "wanderer"),
            )
            if 0 <= skill_index < len(sks):
                sk_def = sks[skill_index]
                stt = combat_state["stats"]
                await anticheat_service.record_skill_damage(
                    session,
                    character,
                    telegram_id=query.from_user.id,
                    username=query.from_user.username,
                    damage=int(skill_dmg),
                    skill_kind=sk_def.kind,
                    skill_power=float(sk_def.power),
                    strength=int(stt["str"]),
                    intelligence=int(stt["int"]),
                    weapon_atk=int(combat_state.get("weapon_attack", 0)),
                    bot=query.bot,
                )
    elif action == "itm" and item_id is not None:
        ok, err, item_logs = await _apply_combat_item(session, character, combat_state, item_id)
        if not ok:
            await query.answer(err or "Нельзя.", show_alert=True)
            if query.from_user is not None:
                await combat_idle_service.arm_combat_idle_after_player_turn(
                    bot=query.bot,
                    state=state,
                    telegram_user_id=int(query.from_user.id),
                )
            return
        lines.extend(item_logs)
        outcome = "continue"
    elif action == "run":
        if combat_state.get("is_tutorial"):
            await query.answer("В учебном бою побег недоступен.", show_alert=True)
            if query.from_user is not None:
                await combat_idle_service.arm_combat_idle_after_player_turn(
                    bot=query.bot,
                    state=state,
                    telegram_user_id=int(query.from_user.id),
                )
            return
        if random.random() < formulas.escape_chance(int(combat_state["stats"]["dex"])):
            sink_rules.set_escape_success_xp_penalty(character)
            try:
                await _safe_edit_combat_message_text(
                    state,
                    query.message,
                    "🏃 Ты сбежал из боя. Стамина уже потрачена.\n"
                    "<i>Следующая победа даст на 10% меньше опыта.</i>",
                    reply_markup=None,
                )
            finally:
                if query.from_user is not None:
                    combat_idle_service.cancel_combat_idle_timer(int(query.from_user.id))
                await character_service.refresh_hp_mp_from_effective(session, character)
                character.hp_current = min(int(character.hp_max), int(combat_state["player_hp"]))
                character.mp_current = min(int(character.mp_max), int(combat_state["player_mp"]))
                await state.clear()
            await query.answer("Побег!")
            return
        lines.append("🏃 Побег не удался! Враг бьёт <b>дважды</b>!")
        failed_escape = True
        outcome = "continue"
    else:
        await query.answer()
        return

    if combat_state.get("is_tutorial"):
        if action == "atk":
            combat_state["tutorial_player_rounds"] = int(combat_state.get("tutorial_player_rounds", 0)) + 1
        elif action == "sk" and skill_index is not None and skill_applied_outcome is not None:
            combat_state["tutorial_player_rounds"] = int(combat_state.get("tutorial_player_rounds", 0)) + 1
            combat_state["tutorial_used_skill"] = True

    _append_logs(combat_state, lines)

    if outcome == "win":
        continued = await _after_monster_killed_player_action(
            query=query,
            session=session,
            state=state,
            character=character,
            combat_state=combat_state,
            class_ru=class_ru,
        )
        if continued and query.from_user is not None:
            await combat_idle_service.arm_combat_idle_after_player_turn(
                bot=query.bot,
                state=state,
                telegram_user_id=int(query.from_user.id),
            )
        elif not continued:
            await query.answer()
        return

    if outcome == "lose":
        await _defeat_sequence(
            message=query.message,
            state=state,
            session=session,
            character=character,
            combat_state=combat_state,
        )
        await query.answer()
        return

    m_logs = engine.apply_dot_damage_monster(combat_state)
    _append_logs(combat_state, m_logs)
    if int(combat_state["monster"]["hp"]) <= 0:
        continued = await _after_monster_killed_player_action(
            query=query,
            session=session,
            state=state,
            character=character,
            combat_state=combat_state,
            class_ru=class_ru,
        )
        if continued and query.from_user is not None:
            await combat_idle_service.arm_combat_idle_after_player_turn(
                bot=query.bot,
                state=state,
                telegram_user_id=int(query.from_user.id),
            )
        elif not continued:
            await query.answer()
        return

    mon_logs, outcome_m = engine.monster_turn(combat_state)
    _append_logs(combat_state, mon_logs)
    if failed_escape and outcome_m == "continue" and int(combat_state["player_hp"]) > 0:
        mon_logs2, outcome_m2 = engine.monster_turn(combat_state)
        _append_logs(combat_state, mon_logs2)
        if outcome_m2 == "lose":
            outcome_m = "lose"
        elif outcome_m2 == "win":
            outcome_m = "win"

    tick_logs = engine.end_round_tick(combat_state)
    _append_logs(combat_state, tick_logs)
    engine.tick_cooldowns(combat_state)

    if outcome_m == "lose":
        await _defeat_sequence(
            message=query.message,
            state=state,
            session=session,
            character=character,
            combat_state=combat_state,
        )
        await query.answer()
        return

    if outcome_m == "win":
        continued = await _after_monster_killed_player_action(
            query=query,
            session=session,
            state=state,
            character=character,
            combat_state=combat_state,
            class_ru=class_ru,
        )
        if continued and query.from_user is not None:
            await combat_idle_service.arm_combat_idle_after_player_turn(
                bot=query.bot,
                state=state,
                telegram_user_id=int(query.from_user.id),
            )
        elif not continued:
            await query.answer()
        return

    await _flush_weapon_mastery(session, character, combat_state)

    try:
        await _safe_edit_combat_message_text(
            state,
            query.message,
            format_battle_view(combat_state, class_ru),
            reply_markup=combat_main_keyboard(character),
        )
    except Exception:
        logger.exception("Не удалось обновить сообщение боя")
    await state.update_data(combat=combat_state)
    if query.from_user is not None:
        await combat_idle_service.arm_combat_idle_after_player_turn(
            bot=query.bot,
            state=state,
            telegram_user_id=int(query.from_user.id),
        )
    await query.answer()


async def defeat_from_afk_or_stuck(
    *,
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    character: Character,
    combat_state: dict[str, Any],
    banner_html: str,
) -> None:
    """Поражение из фона (AFK) или через /fixbattle — общая логика _defeat_sequence."""
    await _defeat_sequence(
        message=message,
        state=state,
        session=session,
        character=character,
        combat_state=combat_state,
        banner_html=banner_html,
    )


async def user_fixbattle_command(
    *,
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> str:
    """
    Сброс застрявшего FSM боя. Если есть данные боя — засчитывается поражение (как обычный слив).
    Возвращает текст ответа пользователю.
    """
    if message.from_user is None:
        return "Нет пользователя."
    tid = int(message.from_user.id)
    combat_idle_service.cancel_combat_idle_timer(tid)
    cur = await state.get_state()
    data = await state.get_data()
    combat_state = data.get("combat")
    if cur != CombatStates.in_battle.state:
        return "Активного боя нет — можно начинать новый на /floor."
    if not isinstance(combat_state, dict):
        await state.clear()
        return "Состояние боя сброшено. Открой /floor."

    user = await user_repo.get_by_telegram_id(session, tid)
    if user is None or user.is_banned:
        await state.clear()
        return "Нет доступа."
    char = await character_repo.get_by_user_id(session, user.id)
    if char is None:
        await state.clear()
        return "Нет персонажа."

    mid = data.get("combat_message_id")
    cid = data.get("combat_chat_id")
    if mid is not None and cid is not None and message.bot is not None:
        from datetime import UTC, datetime

        ctype = "private" if int(cid) > 0 else "supergroup"
        edit_msg = Message(
            message_id=int(mid),
            chat=Chat(id=int(cid), type=ctype),
            date=datetime.now(UTC),
            bot=message.bot,
        )
    else:
        edit_msg = message

    await _defeat_sequence(
        message=edit_msg,
        state=state,
        session=session,
        character=char,
        combat_state=combat_state,
        banner_html="🔧 <b>Фикс боя:</b> застрявший бой закрыт как <b>поражение</b>. "
        "Стамина за начатый бой не возвращается.",
    )
    return (
        "Готово. Если бой реально шёл — засчитано поражение. Открой <b>/floor</b> и начни новый бой.\n"
        "<i>Команда только при зависании интерфейса.</i>"
    )
