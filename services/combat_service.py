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
from bot.keyboards.combat_kb import (
    combat_flee_confirm_keyboard,
    combat_item_picker_keyboard,
    combat_main_keyboard,
)
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
from game.characters.weapon_mastery import (
    damage_multiplier_for_type,
    mastery_combat_bonus,
    record_strike,
    tier_for_hits,
    weapon_type_from_item_data,
)
from game.combat import consumables, effects, engine, formulas, monster_ai, night_mode as combat_night, passive_gear
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
from game.coliseum import coliseum_combat_hooks as coliseum_hooks
from game.coliseum.coliseum_data import (
    build_coliseum_monster_bundle,
    build_coliseum_spawn,
    fighter_by_id,
)
from game.floors import floor_data
from game.floors import floor_entry_mods
from game.floors import long_floor as long_floor_mod
from game.floors import monster_catalog as monster_catalog_mod
from game.floors import rotten_swamps as rotten_swamps_mod
from game.floors import room_clear_floor as room_clear_mod
from game.floors import room_clear_floor_10 as room_clear_10_mod
from game.floors import room_clear_floor_24 as room_clear_24_mod
from game.floors import wave_floor as wave_floor_mod
from game.floors import wave_floor_27 as wave_floor_27_mod
from game.floors import explore_floor as explore_floor_mod
from game.floors import explore_floor_4 as explore_floor_4_mod
from game.floors import explore_floor_22 as explore_floor_22_mod
from utils.image_assets import combat_monster_portrait_path
from game.floors.monster_stat_formula import compute_formula_stat_bundle, monster_strike_ailment
from game.floors.monsters import FloorMonsterSpawn, MonsterTemplate, build_spawns_for_floor
from game.economy import sinks as sink_rules
from game.floors.rewards import experience_reward, gold_reward, roll_item_drop, roll_rune_stone
from game.items import enchant as enchant_rules
from game.items import durability as durability_mod
from game.items.rarity_scaling import scaled_armor_defense_value
from game.items import loot as loot_tables
from game.characters.global_passives import refresh_global_passives
from utils.game_images_prefs import game_images_enabled

from services import (
    anticheat_service,
    character_service,
    city_quest_service,
    clan_service,
    coliseum_service,
    combat_idle_service,
    daily_service,
    floor10_pioneer_service,
    game_metrics_service,
    golden_goblin_service,
    leaderboard_service,
    quest_service,
    rest_service,
    season_record_service,
    stat_bonus_service,
    title_service,
)
from services.tutorial_battle_service import apply_path_rank_from_tutorial, tutorial_battle_pending
from game.economy.stamina import spend_stamina
from services.stamina_service import can_start_combat
from services.combat_fsm_backup import clear_combat_backup, persist_combat_backup
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
        # Любая другая ошибка телеграма (например, потерянный message_id, удалённое сообщение,
        # слишком длинный caption и т. д.) НЕ должна обрывать бой. Лог + мирный возврат.
        logger.warning("combat UI: правка сообщения пропущена ({})", e)
        return False
    except Exception as e:
        logger.exception("combat UI: непредвиденная ошибка при правке сообщения боя ({})", e)
        return False


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
    if off_data and not durability_mod.item_is_broken(off_data):
        oa = int(off_data.get("attack", off_data.get("atk", 0)) or 0)
        if oa > 0:
            off_atk = character_service.weapon_attack_value_from_item_data(off_data, level=lv, floor_number=fl)

    main_data: dict | None = None
    main_atk = 0
    if weapon is not None:
        wd = dict(weapon.item_data or {})
        if not durability_mod.item_is_broken(wd):
            main_data = wd
            main_atk = character_service.weapon_attack_value_from_item_data(wd, level=lv, floor_number=fl)

    if main_data is None and off_atk > 0 and off_data is not None:
        wtype = weapon_type_from_item_data(off_data)
        return off_atk, wtype, damage_multiplier_for_type(character, wtype), off_data

    if main_data is None:
        atk = character_service.weapon_attack_value_from_item_data(None, level=lv, floor_number=fl)
        wtype = "unarmed"
        return atk, wtype, damage_multiplier_for_type(character, wtype), None

    atk = main_atk + off_atk
    wtype = weapon_type_from_item_data(main_data)
    return atk, wtype, damage_multiplier_for_type(character, wtype), main_data


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
        if durability_mod.item_is_broken(dict(data)):
            continue
        base_def = int(data.get("defense", data.get("armor", 0)) or 0)
        def_val = scaled_armor_defense_value(base_def, data)
        ench = enchant_rules.current_enchant_level(data)
        mult = enchant_rules.enchant_stat_multiplier(ench)
        total += max(0, int(round(def_val * mult)))
    return total


async def _equipped_gear_fire_damage_bonus_pct(session: AsyncSession, character_id: int) -> int:
    """Бонус % к элементальному компоненту физ. урона (кольца алхимика и т.п.)."""
    items = await inventory_repo.list_equipped_items(session, character_id)
    total = 0
    for it in items:
        data = dict(it.item_data or {})
        if durability_mod.item_is_broken(data):
            continue
        total += max(0, int(data.get("fire_damage_bonus_pct", 0) or 0))
    return min(120, total)


async def _equipped_gear_resist_pct_sum(session: AsyncSession, character_id: int, field: str, cap: int = 75) -> int:
    """Сумма процента сопротивления стихии по полю item_data (алхимия и др.)."""
    items = await inventory_repo.list_equipped_items(session, character_id)
    total = 0
    for it in items:
        data = dict(it.item_data or {})
        if durability_mod.item_is_broken(data):
            continue
        total += max(0, int(data.get(field, 0) or 0))
    return min(cap, total)


async def _equipped_gear_fire_resist_pct(session: AsyncSession, character_id: int) -> int:
    return await _equipped_gear_resist_pct_sum(session, character_id, "fire_resist_pct", 75)


async def _merge_equipment_chance_mods_into_combat(
    session: AsyncSession,
    character: Character,
    combat_state: dict[str, Any],
) -> None:
    """Шансы с предметов (как в профиле) → passive_mods боя."""
    gc = await stat_bonus_service.aggregate_chance_bonuses(session, character.id)
    combat_state["passive_mods"] = stat_bonus_service.merge_equipment_chances_into_passive_mods(
        combat_state.get("passive_mods") or {},
        gc,
    )


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
        "combat_skill_class_key": character.class_key,
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
        "player_fire_resist_pct": 0,
        "player_ice_resist_pct": 0,
        "player_lightning_resist_pct": 0,
        "player_poison_resist_pct": 0,
        "player_dark_resist_pct": 0,
        "weapon_rune_flat_elemental": 0,
        "rune_crit_damage_bonus_percent": 0,
        "rune_armor_mult": 1.0,
        "weapon_rune_payloads": [],
        "rune_synergy_name": "",
        "player_character_element": (
            str(character.element).strip().lower() if (character.element and str(character.element).strip()) else None
        ),
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

    from game.floors.aura import apply_aura_to_combat_state
    apply_aura_to_combat_state(state)

    # Elixirs
    buffs_elixir = (character.meta_progress or {}).get("active_elixirs", {})
    if buffs_elixir:
        from services.home_service import ELIXIRS
        for k_el, dur_el in buffs_elixir.items():
            if dur_el > 0:
                edef_el = ELIXIRS.get(k_el)
                if edef_el and "buff" in edef_el:
                    for b_k, b_v in edef_el["buff"].items():
                        mods[b_k] = mods.get(b_k, 1.0) * b_v
    return state


def _low_hp_entry_warning_html(character: Character) -> str:
    """Предупреждение при входе в бой с низким HP (<25% от максимума)."""
    hp_max = max(1, int(character.hp_max or 1))
    hp_cur = max(0, int(character.hp_current or 0))
    if hp_cur * 100 > hp_max * 25:
        return ""
    return (
        "⚠️ <b>Мало HP</b> — меньше <b>25%</b> от максимума.\n"
        "<i>Сходи в город или используй расходники — бой очень рискованный.</i>\n\n"
    )


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
        log_block = f"{log_lines}\n\n{taunt_line}"
    elif log_lines:
        log_block = log_lines
    elif taunt_line:
        log_block = taunt_line
    else:
        log_block = "<i>—</i>"

    fln = int(state.get("floor", 0))
    sep = LINE_SEP_BATTLE
    night_note = ""
    if state.get("night_battle"):
        night_note = (
            "<i>🌑 Ночь UTC: враг +20% HP/ATK, победа +40% золото и опыт.</i>\n"
        )

    title = f"⚔️ <b>— ЭТАЖ {fln} —</b>"
    if state.get("night_battle"):
        title += " 🌑"

    return (
        f"{sep}\n"
        f"{title}\n"
        f"{sep}\n"
        f"{night_note}"
        f"<b>▸ ВРАГ</b>\n"
        f"{enemy_line}\n"
        f"{hp_mon}\n"
        f"{buff_line}"
        f"\n"
        f"<b>▸ ИГРОК</b>\n"
        f"{php_line}\n"
        f"\n"
        f"{mp_line}\n"
        f"{shield_p}"
        f"{pet_p}"
        f"{sep}\n"
        f"📜 Лог хода:\n"
        f"{log_block}\n"
        f"{sep}"
    )


def _append_logs(state: dict[str, Any], lines: list[str]) -> None:
    """Добавить строки в лог текущего хода (перед новым ходом список обнуляется в handle_combat_callback)."""
    if not lines:
        return
    buf = list(state.get("ui_logs", []) or [])
    buf.extend(lines)
    state["ui_logs"] = buf


async def start_coliseum_combat(
    *,
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    character: Character,
    fighter_id: int,
) -> bool:
    """Начать бой Колизея. Стамина: как обычный бой (1)."""
    ok_access, err_msg = coliseum_service.can_start_fight(character, fighter_id)
    if not ok_access:
        await query.answer(err_msg or "Нельзя начать бой.", show_alert=True)
        return False

    from config import is_admin as _is_admin

    _admin_bypass = _is_admin(query.from_user.id if query.from_user else None)
    if not _admin_bypass:
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

    if await state.get_state() == CombatStates.in_battle.state:
        await query.answer("Ты уже в бою.", show_alert=True)
        return False

    if not _admin_bypass:
        spent = await spend_stamina(session, int(character.id))
        if not spent:
            await query.answer("Не удалось списать стамину. Попробуй ещё раз.", show_alert=True)
            return False
    await session.refresh(character)
    if pets_mod.repair_pet_meta_if_needed(character):
        await session.flush()

    if query.from_user is not None:
        await anticheat_service.record_fight_start(
            session,
            character,
            telegram_id=query.from_user.id,
            username=query.from_user.username,
            bot=query.bot,
        )

    fdef = fighter_by_id(int(fighter_id))
    if fdef is None:
        await query.answer("Боец не найден.", show_alert=True)
        return False

    monster = build_coliseum_monster_bundle(fdef)
    spawn = build_coliseum_spawn(int(fighter_id))

    await character_service.refresh_hp_mp_from_effective(session, character)
    await session.flush()

    eff_stats = await stat_bonus_service.effective_primary_stats(session, character)
    combat_state = _build_combat_dict(character, spawn, monster, primary_stats=eff_stats)
    combat_state["is_coliseum"] = True
    combat_state["night_battle"] = False
    _append_logs(combat_state, coliseum_hooks.init_coliseum_fight(combat_state, character, int(fighter_id)))

    wa, wtype, wmult, w_item = await _weapon_profile(session, character)
    combat_state["weapon_attack"] = wa
    combat_state["player_weapon_type"] = wtype
    combat_state["weapon_mastery_mult"] = wmult
    _apply_mastery_combat_bonuses(character, combat_state)
    combat_state["player_equipment_defense"] = await _equipped_gear_defense_total(session, character.id)
    _eqs = await inventory_repo.list_equipped_items(session, character.id)
    _gear_passive = [
        e.item_data for e in _eqs
        if not durability_mod.item_is_broken(dict(e.item_data or {}))
    ]
    _glogs = passive_gear.apply_to_combat_state(
        combat_state,
        _gear_passive,
    )
    if _glogs:
        _append_logs(combat_state, _glogs)
    await _merge_equipment_chance_mods_into_combat(session, character, combat_state)
    _tree_ls = float(combat_state.get("passive_mods", {}).get("lifesteal_percent", 0) or 0)
    if _tree_ls > 0:
        combat_state["gear_lifesteal_percent"] = float(combat_state.get("gear_lifesteal_percent", 0.0)) + _tree_ls
    _apply_weapon_runes_to_state(combat_state, character, w_item)
    _fb = await _equipped_gear_fire_damage_bonus_pct(session, character.id)
    if _fb:
        combat_state["weapon_rune_bonus_pct"] = int(combat_state.get("weapon_rune_bonus_pct", 0)) + int(_fb)
    combat_state["player_fire_resist_pct"] = int(
        await _equipped_gear_fire_resist_pct(session, character.id),
    )
    combat_state["player_ice_resist_pct"] = int(
        await _equipped_gear_resist_pct_sum(session, character.id, "ice_resist_pct", 75),
    )
    combat_state["player_lightning_resist_pct"] = int(
        await _equipped_gear_resist_pct_sum(session, character.id, "lightning_resist_pct", 75),
    )
    combat_state["player_poison_resist_pct"] = int(
        await _equipped_gear_resist_pct_sum(session, character.id, "poison_resist_pct", 75),
    )
    combat_state["player_dark_resist_pct"] = int(
        await _equipped_gear_resist_pct_sum(session, character.id, "dark_resist_pct", 75),
    )

    taunt = engine.opening_taunt(combat_state)
    combat_state["battle_taunt_html"] = _taunt_banner_html(taunt)

    await game_metrics_service.record_event(
        session,
        event_type="coliseum_combat_start",
        floor=int(character.floor_number),
        class_key=str(character.class_key or ""),
    )

    await state.set_state(CombatStates.in_battle)
    await state.update_data(combat=combat_state)
    persist_combat_backup(character, combat_state)
    await session.flush()

    cls = get_class_or_none(character.class_key)
    class_ru = cls.name_ru if cls else character.class_key
    text = format_battle_view(combat_state, class_ru)
    text = _low_hp_entry_warning_html(character) + text
    kb = combat_main_keyboard(character)

    if query.message is None:
        clear_combat_backup(character)
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
                    character=character,
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
                logger.exception("start_coliseum_combat: портрет — откат на текст")
        if not opened_with_portrait:
            try:
                ok = await _safe_edit_combat_message_text(state, query.message, text, reply_markup=kb)
            except TelegramBadRequest:
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
                    character=character,
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
        logger.exception("start_coliseum_combat: UI после входа в бой")
        clear_combat_backup(character)
        try:
            await session.flush()
        except Exception:
            pass
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
                "Не удалось открыть экран боя. Стамина возвращена.",
                show_alert=True,
            )
        except Exception:
            pass
        return False


async def start_combat(
    *,
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    character: Character,
    spawn: FloorMonsterSpawn,
    free_stamina: bool = False,
) -> bool:
    """Начать бой. True если бой начат.
    free_stamina=True — не списывать стамину (бой в рамках той же комнаты/серии).
    """
    from config import is_admin as _is_admin
    _admin_bypass = _is_admin(query.from_user.id if query.from_user else None)
    if not free_stamina and not _admin_bypass:
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

    if not free_stamina and not _admin_bypass:
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
    mod_logs = floor_entry_mods.consume_floor_mod_to_combat_state(character, combat_state)
    if mod_logs:
        _append_logs(combat_state, mod_logs)
        await session.flush()
    combat_state["night_battle"] = night_on
    if str(spawn.slot_code) == golden_goblin_service.SLOT_CODE:
        combat_state["golden_goblin_wave"] = await golden_goblin_service.current_wave(session)
    wa, wtype, wmult, w_item = await _weapon_profile(session, character)
    combat_state["weapon_attack"] = wa
    combat_state["player_weapon_type"] = wtype
    combat_state["weapon_mastery_mult"] = wmult
    _apply_mastery_combat_bonuses(character, combat_state)
    combat_state["player_equipment_defense"] = await _equipped_gear_defense_total(session, character.id)
    _eqs = await inventory_repo.list_equipped_items(session, character.id)
    _gear_passive = [
        e.item_data for e in _eqs
        if not durability_mod.item_is_broken(dict(e.item_data or {}))
    ]
    _glogs = passive_gear.apply_to_combat_state(
        combat_state,
        _gear_passive,
    )
    if _glogs:
        _append_logs(combat_state, _glogs)
    await _merge_equipment_chance_mods_into_combat(session, character, combat_state)
    # Lifesteal from skill tree passive nodes goes into gear_lifesteal_percent
    _tree_ls = float(combat_state.get("passive_mods", {}).get("lifesteal_percent", 0) or 0)
    if _tree_ls > 0:
        combat_state["gear_lifesteal_percent"] = float(combat_state.get("gear_lifesteal_percent", 0.0)) + _tree_ls
    _apply_weapon_runes_to_state(combat_state, character, w_item)
    _fb = await _equipped_gear_fire_damage_bonus_pct(session, character.id)
    if _fb:
        combat_state["weapon_rune_bonus_pct"] = int(combat_state.get("weapon_rune_bonus_pct", 0)) + int(_fb)
    combat_state["player_fire_resist_pct"] = int(
        await _equipped_gear_fire_resist_pct(session, character.id),
    )
    combat_state["player_ice_resist_pct"] = int(
        await _equipped_gear_resist_pct_sum(session, character.id, "ice_resist_pct", 75),
    )
    combat_state["player_lightning_resist_pct"] = int(
        await _equipped_gear_resist_pct_sum(session, character.id, "lightning_resist_pct", 75),
    )
    combat_state["player_poison_resist_pct"] = int(
        await _equipped_gear_resist_pct_sum(session, character.id, "poison_resist_pct", 75),
    )
    combat_state["player_dark_resist_pct"] = int(
        await _equipped_gear_resist_pct_sum(session, character.id, "dark_resist_pct", 75),
    )

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
    persist_combat_backup(character, combat_state)
    await session.flush()

    cls = get_class_or_none(character.class_key)
    class_ru = cls.name_ru if cls else character.class_key
    text = format_battle_view(combat_state, class_ru)
    text = _low_hp_entry_warning_html(character) + text
    kb = combat_main_keyboard(character)

    if query.message is None:
        clear_combat_backup(character)
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
                    character=character,
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
                    character=character,
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
        clear_combat_backup(character)
        try:
            await session.flush()
        except Exception:
            pass
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
    if int(character.floor_number) != 2:
        await query.answer("Обучение у наставника доступно на 2 этаже.", show_alert=True)
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
    _apply_mastery_combat_bonuses(character, combat_state)
    _apply_weapon_runes_to_state(combat_state, character, w_item)
    _fbt = await _equipped_gear_fire_damage_bonus_pct(session, character.id)
    if _fbt:
        combat_state["weapon_rune_bonus_pct"] = int(combat_state.get("weapon_rune_bonus_pct", 0)) + int(_fbt)
    combat_state["player_fire_resist_pct"] = int(
        await _equipped_gear_fire_resist_pct(session, character.id),
    )
    combat_state["player_ice_resist_pct"] = int(
        await _equipped_gear_resist_pct_sum(session, character.id, "ice_resist_pct", 75),
    )
    combat_state["player_lightning_resist_pct"] = int(
        await _equipped_gear_resist_pct_sum(session, character.id, "lightning_resist_pct", 75),
    )
    combat_state["player_poison_resist_pct"] = int(
        await _equipped_gear_resist_pct_sum(session, character.id, "poison_resist_pct", 75),
    )
    combat_state["player_dark_resist_pct"] = int(
        await _equipped_gear_resist_pct_sum(session, character.id, "dark_resist_pct", 75),
    )
    combat_state["player_equipment_defense"] = await _equipped_gear_defense_total(session, character.id)
    _teq = await inventory_repo.list_equipped_items(session, character.id)
    _tgear_passive = [
        e.item_data for e in _teq
        if not durability_mod.item_is_broken(dict(e.item_data or {}))
    ]
    _tlg = passive_gear.apply_to_combat_state(
        combat_state,
        _tgear_passive,
    )
    if _tlg:
        _append_logs(combat_state, _tlg)
    await _merge_equipment_chance_mods_into_combat(session, character, combat_state)
    _tree_ls_tut = float((combat_state.get("passive_mods") or {}).get("lifesteal_percent", 0) or 0)
    if _tree_ls_tut > 0:
        combat_state["gear_lifesteal_percent"] = float(combat_state.get("gear_lifesteal_percent", 0.0)) + _tree_ls_tut
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
    persist_combat_backup(character, combat_state)
    await session.flush()

    cls = get_class_or_none(character.class_key)
    class_ru = cls.name_ru if cls else character.class_key
    text = format_battle_view(combat_state, class_ru)
    text = _low_hp_entry_warning_html(character) + text
    kb = combat_main_keyboard(character)

    if query.message is None:
        clear_combat_backup(character)
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
                character=character,
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
        clear_combat_backup(character)
        try:
            await session.flush()
        except Exception:
            pass
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

    # Этаж 4: бой-исследование леса инкрементирует счётчик
    if spawn.slot_code == explore_floor_4_mod.SLOT_ENCOUNTER:
        extra = explore_floor_4_mod.increment_explore_count(extra)
        extra["slots_cleared"] = cleared
        row.extra = extra
        await session.flush()
        return ""

    # Этаж 8: бой-исследование пещеры инкрементирует счётчик (не добавляется в slots_cleared)
    if spawn.slot_code == explore_floor_mod.SLOT_ENCOUNTER:
        extra = explore_floor_mod.increment_explore_count(extra)
        extra["slots_cleared"] = cleared
        row.extra = extra
        await session.flush()

    # Этаж 22: бой-исследование Пещеры Теней инкрементирует счётчик
    if spawn.slot_code == explore_floor_22_mod.SLOT_ENCOUNTER:
        extra = explore_floor_22_mod.increment_explore_count(extra)
        extra["slots_cleared"] = cleared
        row.extra = extra
        await session.flush()
        return ""

    if spawn.slot_code not in cleared:
        cleared.append(spawn.slot_code)
    extra["slots_cleared"] = cleared
    row.extra = extra
    # Сразу фиксируем изменение, чтобы следующий запрос в той же транзакции
    # и следующий callback увидели актуальный slots_cleared.
    await session.flush()

    all_spawns = long_floor_mod.spawns_for_tower_progress(character, cur)
    needed = {s.slot_code for s in all_spawns}
    # needed.issubset(cleared) == True только когда ВСЕ нужные слоты зачищены.
    if not needed.issubset(set(cleared)):
        return ""

    if cur >= 135:
        character.highest_floor_reached = max(int(character.highest_floor_reached), 135)
        extra["slots_cleared"] = []
        row.extra = extra
        return "\n👁️ <b>Вершина башни:</b> страж повержен."

    from game.floors.tower_ascent import set_tower_ascent_pending

    nxt = cur + 1
    set_tower_ascent_pending(character, nxt)
    character.highest_floor_reached = max(int(character.highest_floor_reached), nxt)
    extra["slots_cleared"] = []
    # Сбрасываем прогресс исследования при подъёме с 4-го и 8-го этажей
    if cur == explore_floor_4_mod.EXPLORE_FLOOR_4:
        extra = explore_floor_4_mod.reset_explore_state(extra)
    if cur == explore_floor_mod.EXPLORE_FLOOR:
        extra = explore_floor_mod.reset_explore_state(extra)
    if cur == explore_floor_22_mod.EXPLORE_FLOOR_22:
        extra = explore_floor_22_mod.reset_explore_state(extra)
    row.extra = extra
    zone_next = floor_data.get_zone_for_floor(nxt)
    room_next = floor_data.epithet_for_floor(zone_next, nxt)
    return (
        f"\n🪜 <b>Этаж зачищен!</b>\n"
        f"Поднимись на <b>{nxt}</b> / 135 — <i>{html.escape(room_next)}</i> "
        f"(кнопка «Следующий этаж» или ⬆️ Выше).\n"
        f"<i>{html.escape(zone_next.description)}</i>"
    )


def _add_faction_reputation(character: Character, floor_number: int, amount: int = 10) -> str:
    """Добавляет репутацию фракции после победы на этаже Войны Фракций."""
    from game.floors.floor_data import get_zone_floor_type, get_zone_raw, get_zone_for_floor
    if get_zone_floor_type(floor_number) != "faction_war":
        return ""
    zone = get_zone_for_floor(floor_number)
    zone_raw = get_zone_raw(floor_number)
    factions = zone_raw.get("factions", {})
    mp = dict(character.meta_progress or {})
    chosen = mp.get(f"faction_choice_{zone.key}")
    if not chosen or chosen not in factions:
        return ""
    fac = factions[chosen]
    rep_key = f"faction_rep_{zone.key}"
    rep_data = dict(mp.get(rep_key) or {})
    old_rep = int(rep_data.get(chosen, 0))
    new_rep = old_rep + amount
    rep_data[chosen] = new_rep
    mp[rep_key] = rep_data
    character.meta_progress = mp
    req = int(zone_raw.get("reputation_required", 1000))
    if old_rep < req <= new_rep:
        return (
            f"\n⚔️ <b>Репутация {fac['emoji']} {fac['name']}:</b> {new_rep}/{req} ✅ "
            f"Генерал готов к бою!"
        )
    return f"\n⚔️ <b>Репутация {fac['emoji']}:</b> {new_rep}/{req}"


def _apply_mastery_combat_bonuses(character: Character, combat_state: dict[str, Any]) -> None:
    """Слить бонусы тиров мастерства (крит/–промах/стан) в passive_mods боевого стейта."""
    wt = str(combat_state.get("player_weapon_type") or "blade")
    tier = tier_for_hits(
        int(((character.meta_progress or {}).get("weapon_mastery_v1") or {}).get(wt, {}).get("hits", 0))
    )
    bonuses = mastery_combat_bonus(tier)
    mods = combat_state.get("passive_mods") or {}
    if not isinstance(mods, dict):
        mods = {}
    mods["crit_bonus"] = float(mods.get("crit_bonus", 0.0)) + float(bonuses.get("crit_bonus", 0.0))
    # У промаха подставка отрицательная: уменьшаем шанс промаха через extra_miss_chance.
    if bonuses.get("miss_reduction", 0.0) > 0:
        cur = float(mods.get("extra_miss_chance", 0.0))
        mods["extra_miss_chance"] = cur - float(bonuses["miss_reduction"])
    mods["stun_chance"] = float(mods.get("stun_chance", 0.0)) + float(bonuses.get("stun_chance", 0.0))
    combat_state["passive_mods"] = mods


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
    _apply_mastery_combat_bonuses(character, combat_state)
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
        persist_combat_backup(character, combat_state)
        await session.flush()
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


async def _victory_sequence_coliseum(
    *,
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    character: Character,
    combat_state: dict[str, Any],
) -> None:
    await character_repo.lock_character_row(session, character.id)
    fid = int(combat_state.get("coliseum_fighter_id") or 0)
    xp_raw, gold_raw = coliseum_service.reward_multipliers(fid)
    gm, xm = title_service.reward_bonus_multipliers(character)
    gross_gold = int(gold_raw * gm)
    xp = int(xp_raw * xm)
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

    net_gold, _debt_note = sink_rules.garnish_victory_gold_for_debt(character, gross_gold)

    await character_service.add_gold_async(
        session,
        character,
        net_gold,
        source="coliseum_win",
        bot=message.bot,
        telegram_id=message.from_user.id if message.from_user else None,
        username=message.from_user.username if message.from_user else None,
    )
    levels_battle = await character_service.add_experience_async(session, character, xp, bot=message.bot)
    level_battle_suffix = character_service.level_up_notice_html(character, levels_battle)
    character.total_kills = int(character.total_kills) + 1

    await coliseum_service.record_victory(session, character, fid)
    loot_ent = coliseum_service.loot_entry_for_fighter(fid)
    loot_lines = await coliseum_service.grant_loot(session, character, loot_ent)

    daily_service.record_kill(character)
    try:
        pets_mod.record_pet_xp_on_battle_win(character, is_boss=False)
    except Exception:
        pass
    refresh_global_passives(character)
    character.hp_current = min(int(character.hp_max), int(combat_state["player_hp"]))
    character.mp_current = min(int(character.mp_max), int(combat_state["player_mp"]))

    title_service.refresh_unlocks(character)
    extra_loot = "\n".join(loot_lines) if loot_lines else ""
    body = (
        f"🏛️ <b>Победа в Колизее!</b>\n"
        f"{LINE_SEP}\n"
        f"💰 +{net_gold} золота · 📈 +{xp} опыта\n"
        f"{level_battle_suffix}"
        + (f"\n{extra_loot}" if extra_loot else "")
    )
    fl = int(character.floor_number)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏛️ Колизей", callback_data="col:menu")],
            [
                InlineKeyboardButton(text="🗺️ На этаж", callback_data=f"fl:{fl}:return"),
            ],
            menu_nav_button_row(),
        ],
    )
    try:
        await _safe_edit_combat_message_text(state, message, body, reply_markup=kb)
    finally:
        if message.from_user is not None:
            combat_idle_service.cancel_combat_idle_timer(int(message.from_user.id))
        clear_combat_backup(character)
        try:
            await session.flush()
        except Exception:
            pass
        await state.clear()


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
            clear_combat_backup(character)
            try:
                await session.flush()
            except Exception:
                pass
            await state.clear()
        return

    if combat_state.get("is_coliseum") and combat_state.get("coliseum_fighter_id"):
        await _victory_sequence_coliseum(
            message=message,
            state=state,
            session=session,
            character=character,
            combat_state=combat_state,
        )
        return

    await character_repo.lock_character_row(session, character.id)

    spawn = _spawn_from_state(character, combat_state)
    if spawn is None:
        await state.clear()
        await message.answer("⚠️ Сессия боя устарела (spawn lost). Награды не начислены. Пожалуйста, зайдите на этаж заново.")
        return
    battle_floor = int(combat_state.get("floor", character.floor_number))
    rotten_swamps_mod.maybe_roll_leech_infection_after_swamp_win(character, battle_floor)
    await session.flush()

    gg_first = False
    if str(spawn.template.key or "") == golden_goblin_service.TEMPLATE_KEY:
        gg_wave = int(combat_state.get("golden_goblin_wave") or 0)
        if gg_wave <= 0:
            gg_wave = await golden_goblin_service.current_wave(session)
        gg_first = await golden_goblin_service.try_claim_first_blood(session, gg_wave)

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
        fgm = float(combat_state.get("floor_event_gold_mult") or 1.0)
        if fgm > 1.01:
            gross_gold = int(round(gross_gold * fgm))

        # Ауры этажей (21–30 и далее): могут давать бафф/дебафф наград.
        try:
            aura = combat_state.get("floor_aura") or {}
            rgm = float(aura.get("reward_gold_mult") or 1.0)
            rxm = float(aura.get("reward_xp_mult") or 1.0)
            if rgm > 0.01 and abs(rgm - 1.0) > 0.001:
                gross_gold = int(round(gross_gold * rgm))
            if rxm > 0.01 and abs(rxm - 1.0) > 0.001:
                xp = int(round(xp * rxm))
        except Exception:
            pass
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

    await character_service.add_gold_async(
        session,
        character,
        net_gold,
        source="battle_win",
        bot=message.bot,
        telegram_id=message.from_user.id if message.from_user else None,
        username=message.from_user.username if message.from_user else None,
    )
    levels_battle = await character_service.add_experience_async(session, character, xp, bot=message.bot)
    level_battle_suffix = character_service.level_up_notice_html(character, levels_battle)
    character.total_kills = int(character.total_kills) + 1

    # Сюжетный квест Эйрис: убийства волков на этажах 2–5 (ключ или русское имя).
    try:
        _sq_floor = int(combat_state.get("floor", character.floor_number))
        _sq_tkey = str(spawn.template.key or "").lower()
        _sq_nm = str(spawn.template.name or "").lower()
        if 2 <= _sq_floor <= 5 and ("wolf" in _sq_tkey or "волк" in _sq_nm):
            from game.quests.story_quests import increment_kill_counter
            increment_kill_counter(character, "sq_eyris_wolves")
        # Сюжетный квест Кассандры: победы над элитными.
        if bool(getattr(spawn.template, "is_elite", False)):
            from game.quests.story_quests import increment_kill_counter
            increment_kill_counter(character, "sq_cassandra_elite")
    except Exception:
        pass

    try:
        pets_mod.record_pet_xp_on_battle_win(
            character,
            is_boss=bool(spawn.is_mini_boss) or bool(spawn.is_major_boss),
        )
    except Exception:
        pass
    daily_service.record_kill(character)
    durability_note = await durability_mod.wear_equipped_items_after_battle(session, character.id)

    # Decrement elixirs
    mp_win = dict(character.meta_progress or {})
    buffs_win = dict(mp_win.get("active_elixirs") or {})
    if buffs_win:
        new_buffs_win = {}
        for k_win, v_win in buffs_win.items():
            if v_win > 1:
                new_buffs_win[k_win] = v_win - 1
        mp_win["active_elixirs"] = new_buffs_win
        character.meta_progress = mp_win
    # Обновляем прогресс ежедневных заданий
    from services import daily_quest_service as dqs
    dqs.record_battle_result(
        character,
        is_elite=bool(spawn.is_elite),
        is_mini_boss=bool(spawn.is_mini_boss),
        is_major_boss=bool(spawn.is_major_boss),
        gold_gained=int(net_gold),
    )
    # Обновляем прогресс заданий путников (этажи 1–20)
    from services import wandering_npc_quest_service as wnpc_qs
    wnpc_qs.record_battle(
        character,
        is_elite=bool(spawn.is_elite),
        is_mini_boss=bool(spawn.is_mini_boss),
        is_major_boss=bool(spawn.is_major_boss),
        gold_gained=int(net_gold),
    )
    # Обновляем прогресс цепочек кузнеца и скупщика (по всем хабам)
    from services import forge_quest_service as fqs, tavern_buyer_service as bqs
    from game.quests.forge_quests import HUB_FLOORS as _HUB_FLOORS
    for _hub in _HUB_FLOORS:
        fqs.record_battle(
            character, _hub,
            is_elite=bool(spawn.is_elite),
            is_mini_boss=bool(spawn.is_mini_boss),
            is_major_boss=bool(spawn.is_major_boss),
            gold_gained=int(net_gold),
        )
        bqs.record_battle(
            character, _hub,
            is_elite=bool(spawn.is_elite),
            is_mini_boss=bool(spawn.is_mini_boss),
            is_major_boss=bool(spawn.is_major_boss),
            gold_gained=int(net_gold),
        )
    # Вклад зависит от типа врага: обычный +1, элитный +3, босс +5/+10
    _clan_delta = 1
    if spawn.is_mini_boss:
        _clan_delta = 5
    elif spawn.is_major_boss:
        _clan_delta = 10
    elif spawn.is_elite:
        _clan_delta = 3
    # Бонус за топ кланов: +10% к очкам клана за боссов на 1-м месте.
    if spawn.is_mini_boss or spawn.is_major_boss:
        try:
            from services import leaderboard_bonuses as _lbn

            _ranks = await _lbn.per_board_ranks(session, character)
            _clan_delta = max(_clan_delta, int(round(_clan_delta * _lbn.clan_boss_score_multiplier(_ranks))))
        except Exception:
            pass
    await clan_service.on_monster_win_add_clan_xp(session, character, delta=_clan_delta)
    try:
        await clan_service.add_war_points(session, character, _clan_delta)
    except Exception:
        logger.exception("clan war points after win")

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
        # Бонус за топ "этаж (рекорд)": +5% к шансу выпадения материалов на 1-м месте.
        try:
            from services import leaderboard_bonuses as _lbn

            _ranks = await _lbn.per_board_ranks(session, character)
            _mat_chance = min(1.0, _mat_chance * _lbn.material_drop_multiplier(_ranks))
        except Exception:
            pass
        # Определяем тип материала по зоне монстра
        from game.data.monsters import KEY_TO_ZONE
        _zone = KEY_TO_ZONE.get(_tkey2, "")
        _floor_n = int(combat_state.get("floor", character.floor_number))
        if _zone in ("forest_beginnings",) or "ent" in _tkey2 or "treant" in _tkey2 or "vine" in _tkey2:
            _mat_drop = "wood"
        elif _zone in ("shadow_caves", "volcanic_ruins") or "golem" in _tkey2 or "stone" in _tkey2 or "sentinel" in _tkey2:
            _mat_drop = "stone"
        elif _zone in ("rotten_swamps",) or "swamp" in _tkey2 or "troll" in _tkey2 or "bog" in _tkey2:
            _mat_drop = "herbs"
        # Монстры 5-го этажа (комнаты rc_*) тоже дают дерево
        elif str(spawn.slot_code or "").startswith("rc_r"):
            _mat_drop = "wood"
        # Дерево выпадает на всех лесных/природных этажах (10–40) если тип ещё не определён
        if _mat_drop is None and 10 <= _floor_n <= 40:
            if _zone in ("tower_ascent", "forest_beginnings") or "wolf" in _tkey2 or "beast" in _tkey2 or "bandit" in _tkey2:
                _mat_drop = "wood"
        if _mat_drop and random.random() < _mat_chance:
            if spawn.is_major_boss:
                _mat_amount = random.randint(2, 5)
            elif spawn.is_mini_boss:
                _mat_amount = random.randint(3, 7)
            else:
                _mat_amount = random.randint(1, 2)
            clan_service.add_material_drop(character, _mat_drop, _mat_amount)
            # Сюжетный квест Совы: засчитываем материалы
            try:
                from game.quests.story_quests import increment_material_counter
                increment_material_counter(character, "sq_owl_materials", _mat_amount)
            except Exception:
                pass
            _mat_icons = {"wood": "🪵", "stone": "🪨", "herbs": "🌿"}
            _mat_ru = {"wood": "дерево", "stone": "камень", "herbs": "травы"}
            _mat_note = f"\n{_mat_icons.get(_mat_drop, '📦')} +{_mat_amount} {_mat_ru.get(_mat_drop, _mat_drop)}"
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
        from services.fame_bonuses import loot_item_drop_fame_multiplier

        _fam = loot_item_drop_fame_multiplier(character)
        _elixir_drop_mult = 1.0
        from services.home_service import ELIXIRS as _HOME_ELIXIRS

        for _ek, _ev in dict((character.meta_progress or {}).get("active_elixirs") or {}).items():
            if int(_ev or 0) <= 0:
                continue
            _edef = _HOME_ELIXIRS.get(str(_ek))
            if _edef is not None:
                _elixir_drop_mult *= float((_edef.get("buff") or {}).get("drop_mult", 1.0))
        _drop_triggered = roll_item_drop(
            spawn,
            int(character.floor_number),
            stat_luck=_luck,
            fame_loot_mult=_fam * _elixir_drop_mult,
        ) or (
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

        # Runes and Trophies
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

        # Boss Trophies Drop (Guaranteed)
        if boss_like:
            from game.items import materials
            trophy_count = 1
            slot_t = await inventory_repo.first_free_bag_slot(session, character.id)
            if slot_t is not None:
                await inventory_repo.add_bag_item(
                    session,
                    character.id,
                    materials.boss_trophy_payload(trophy_count),
                    bag_slot=slot_t,
                )
                extra_drop += f"\n🏆 <b>Трофей босса</b> ({trophy_count} шт.) — в сумку"
            try:
                from services import workshop_blueprint_hooks

                bp_line = await workshop_blueprint_hooks.roll_blueprint_after_boss(
                    session,
                    character,
                    spawn,
                )
                if bp_line:
                    extra_drop += f"\n{bp_line}"
            except Exception:
                pass

    mname = html.escape(str(combat_state.get("monster", {}).get("name", "Враг")))
    floor_before = int(character.floor_number)
    old_highest_reached = int(character.highest_floor_reached)
    faction_rep_note = _add_faction_reputation(character, floor_before)
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
    # Этажи 5 и 10: если победили монстра в комнате и следующий монстр есть — вместо
    # «На этаж» показываем кнопку «Следующий противник» (игрок не уходит с экрана боя).
    _next_rc_slot: str | None = None
    _next_rc_mod = None  # ссылка на нужный модуль (floor 5 или floor 10)
    if spawn.slot_code in room_clear_mod.SLOT_ROOMS:
        _next_rc_slot = room_clear_mod.next_slot_after_defeat(spawn.slot_code)
        _next_rc_mod = room_clear_mod
    elif spawn.slot_code in room_clear_10_mod.SLOT_ROOMS:
        _next_rc_slot = room_clear_10_mod.next_slot_after_defeat(spawn.slot_code)
        _next_rc_mod = room_clear_10_mod
    elif spawn.slot_code in room_clear_24_mod.SLOT_ROOMS:
        _next_rc_slot = room_clear_24_mod.next_slot_after_defeat(spawn.slot_code)
        _next_rc_mod = room_clear_24_mod
    if _next_rc_slot is not None and _next_rc_mod is not None:
        _next_rc_spawn = _next_rc_mod.spawn_by_slot(_next_rc_slot)
        _next_name = _next_rc_spawn.display_name if _next_rc_spawn else "Следующий"
        _room_info = _next_rc_mod.slot_room_and_monster_index(spawn.slot_code)
        _room_idx, _mon_idx = _room_info if _room_info else (0, 0)
        _total_in_room = len(_next_rc_mod.ROOM_GROUPS[_room_idx])
        _next_label = f"⚔️ {_next_name} ({_mon_idx + 2}/{_total_in_room})"
        floor_rows: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton(text=_next_label[:36], callback_data=f"fl:{fl}:{_next_rc_slot}")],
            menu_nav_button_row(),
        ]
    else:
        floor_rows = [
            [InlineKeyboardButton(text="🗺️ На этаж", callback_data=f"fl:{fl}:return")],
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
                + durability_note
            )
            gg_body = (
                "🏆 <b>Победа!</b> 💰 Золотой гоблин\n"
                "✨ Награда… ▓▓▓▓▓▓▓▓▓▓\n"
                f"{gold_gg}\n"
                f"📈 +{xp} опыта{extra_rune}{extra_drop}{extra_rune_item}"
            )
            if (floor_banner or "").strip():
                gg_body += floor_banner
            if faction_rep_note:
                gg_body += faction_rep_note
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
                        + faction_rep_note
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
                        + durability_note
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
        clear_combat_backup(character)
        await character_service.refresh_hp_mp_from_effective(session, character)
        _okh = int(combat_state.get("gear_on_kill_heal", 0) or 0)
        _pe = min(
            int(character.hp_max),
            int(combat_state["player_hp"]) + (_okh if _okh > 0 else 0),
        )
        character.hp_current = _pe
        character.mp_current = min(int(character.mp_max), int(combat_state["player_mp"]))
        if message.from_user is not None:
            combat_idle_service.cancel_combat_idle_timer(int(message.from_user.id))
        try:
            await session.flush()
        except Exception:
            pass
        await state.clear()


def _spawn_from_state(character: Character, combat_state: dict[str, Any]) -> FloorMonsterSpawn | None:
    slot = str(combat_state.get("spawn_slot"))
    if slot == "tutorial":
        return TUTORIAL_SPAWN
    if slot.startswith("col:f"):
        tail = slot.split(":")[-1].removeprefix("f")
        try:
            n = int(tail)
        except ValueError:
            n = 0
        if 1 <= n <= 50:
            return build_coliseum_spawn(n)
    if slot == golden_goblin_service.SLOT_CODE:
        return golden_goblin_service.build_spawn()
    if slot in long_floor_mod.LONG_FLOOR_SLOTS:
        found_lf = long_floor_mod.spawn_by_slot(slot)
        if found_lf is not None:
            return found_lf
    battle_floor = int(combat_state.get("floor", character.floor_number))
    # Room-clear floor 5 (rc_r0…rc_r4, rc_boss)
    if slot in room_clear_mod.ROOM_CLEAR_ALL_SLOTS:
        found_rc = room_clear_mod.spawn_by_slot(slot)
        if found_rc is not None:
            return found_rc
    # Room-clear floor 10 (r10_r0…r10_r4, r10_boss)
    if slot in room_clear_10_mod.ROOM_CLEAR_10_ALL_SLOTS:
        found_rc10 = room_clear_10_mod.spawn_by_slot(slot)
        if found_rc10 is not None:
            return found_rc10
    # Room-clear floor 24 (r24_r0…r24_r4, r24_boss)
    if slot in room_clear_24_mod.ROOM_CLEAR_24_ALL_SLOTS:
        found_rc24 = room_clear_24_mod.spawn_by_slot(slot)
        if found_rc24 is not None:
            return found_rc24
    # Wave floor 27 (wv27_w1, wv27_w2, wv27_w3, wv27_boss)
    if slot in wave_floor_27_mod.WAVE_FLOOR_27_ALL_SLOTS:
        found_wv27 = wave_floor_27_mod.spawn_by_slot(slot)
        if found_wv27 is not None:
            return found_wv27
    # Wave floors (wv_w1, wv_w2, wv_w3, wv_boss)
    if slot in wave_floor_mod.WAVE_FLOOR_ALL_SLOTS:
        found_wv = wave_floor_mod.spawn_by_slot(slot)
        if found_wv is not None:
            return found_wv
    # Explore floor 4 (e4_encounter, e4_boss)
    if slot in explore_floor_4_mod.EXPLORE_4_ALL_SLOTS:
        found_e4 = explore_floor_4_mod.spawn_by_slot(slot)
        if found_e4 is not None:
            return found_e4
    # Explore floor 8 (exp_encounter, exp_boss)
    if slot in explore_floor_mod.EXPLORE_ALL_SLOTS:
        found_exp = explore_floor_mod.spawn_by_slot(slot)
        if found_exp is not None:
            return found_exp
    # Explore floor 22 (e22_encounter, e22_boss)
    if slot in explore_floor_22_mod.EXPLORE_22_ALL_SLOTS:
        found_e22 = explore_floor_22_mod.spawn_by_slot(slot)
        if found_e22 is not None:
            return found_e22
    spawns = build_spawns_for_floor(battle_floor)
    found = next((s for s in spawns if s.slot_code == slot), None)
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
            clear_combat_backup(character)
            await session.flush()
            await state.clear()
        return

    if combat_state and combat_state.get("is_coliseum"):
        await character_service.refresh_hp_mp_from_effective(session, character)
        character.hp_current = max(1, int(character.hp_max) // 2)
        character.mp_current = max(0, int(character.mp_max) // 2)
        loc = get_locale(character, None)
        defeat_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏛️ Колизей", callback_data="col:menu")],
                [
                    InlineKeyboardButton(
                        text=t(loc, "combat_revive_btn"),
                        callback_data=f"fl:{int(character.floor_number)}:return",
                    ),
                ],
                menu_nav_button_row(),
            ],
        )
        cbody = (
            (banner_html + "\n") if banner_html else ""
        ) + (
            "⚔️ <b>Поражение в Колизее.</b>\n"
            "Без штрафов к золоту и заточке — можно сразиться снова."
        )
        try:
            await _safe_edit_combat_message_text(
                state,
                message,
                cbody,
                reply_markup=defeat_kb,
            )
        finally:
            clear_combat_backup(character)
            await session.flush()
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
    character_service.add_gold(character, -lost_gold)

    weapon = await inventory_repo.get_equipped_weapon(session, character.id)
    enchant_msg = ""
    if weapon is not None and random.random() < 0.30:
        data = dict(weapon.item_data or {})
        ench = int(data.get("enchant", data.get("plus", 0)))
        if ench > 0:
            data["enchant"] = ench - 1
            weapon.item_data = data
            enchant_msg = f"\n⚠️ Заточка оружия снижена до +{ench - 1}."

    dur_note = await durability_mod.wear_equipped_items_after_battle(session, character.id)

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
        f"{dur_note}"
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
        clear_combat_backup(character)
        await session.flush()
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
    await inventory_repo.consume_one_from_stack(session, item)
    await session.flush()
    return True, None, logs


def _rehydrate_skills_and_cooldowns(combat_state: dict[str, Any], character: Character) -> None:
    """
    Бэкап боя в meta — JSON; SkillDef в combat_skills превращаются в строки.
    Без пересборки engine.player_skill падает (ловится в combat.py как «Ошибка боя»).
    """
    combat_state["combat_skills"] = battle_skills_tuple(character)
    sc = combat_state.get("skill_cd")
    if not isinstance(sc, dict):
        combat_state["skill_cd"] = {"0": 0, "1": 0, "2": 0}
    else:
        for k in ("0", "1", "2"):
            sc.setdefault(k, 0)


_combat_callback_locks: dict[int, asyncio.Lock] = {}


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
    """Маршрутизация действий боя (сериализация колбэков на игрока — без двойной выдачи награды)."""
    if query.message is None:
        await query.answer()
        return
    if query.from_user is None:
        await query.answer()
        return
    uid = int(query.from_user.id)
    lock = _combat_callback_locks.setdefault(uid, asyncio.Lock())
    async with lock:
        data = await state.get_data()
        combat_state = data.get("combat")
        if combat_state is None:
            await query.answer("Нет активного боя.", show_alert=True)
            clear_combat_backup(character)
            try:
                await session.flush()
            except Exception:
                pass
            await state.clear()
            combat_idle_service.cancel_combat_idle_timer(uid)
            return
        _rehydrate_skills_and_cooldowns(combat_state, character)
        cls = get_class_or_none(character.class_key)
        class_ru = cls.name_ru if cls else character.class_key
        await _handle_combat_callback_body(
            query=query,
            session=session,
            state=state,
            character=character,
            combat_state=combat_state,
            class_ru=class_ru,
            action=action,
            skill_index=skill_index,
            item_id=item_id,
        )


async def _handle_combat_callback_body(
    *,
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    character: Character,
    combat_state: dict[str, Any],
    class_ru: str,
    action: str,
    skill_index: int | None,
    item_id: int | None = None,
) -> None:
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

    if action == "run_ask":
        if combat_state.get("is_tutorial") or combat_state.get("is_coliseum"):
            await query.answer("Побег здесь недоступен.", show_alert=True)
            if query.from_user is not None:
                await combat_idle_service.arm_combat_idle_after_player_turn(
                    bot=query.bot,
                    state=state,
                    telegram_user_id=int(query.from_user.id),
                )
            return
        await query.message.edit_reply_markup(reply_markup=combat_flee_confirm_keyboard())
        await query.answer("Подтверди побег или отмени.")
        return

    lines: list[str] = []
    failed_escape = False
    combat_state["ui_logs"] = []

    if action == "sk" and skill_index is not None:
        br = engine.player_skill_blocked_reason(combat_state, skill_index)
        if br is not None:
            await query.answer(br, show_alert=True)
            if query.from_user is not None:
                await combat_idle_service.arm_combat_idle_after_player_turn(
                    bot=query.bot,
                    state=state,
                    telegram_user_id=int(query.from_user.id),
                )
            return

    # Доты и пассивная регенерация MP в начале твоего хода
    lines.extend(engine.apply_dot_damage_player(combat_state))
    lines.extend(floor_entry_mods.floor_curse_on_player_phase_start(combat_state))
    lines.extend(passive_gear.turn_start_regen_from_gear(combat_state))
    lines.extend(coliseum_hooks.on_player_phase_start(combat_state, character))
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
        if combat_state.get("is_tutorial") or combat_state.get("is_coliseum"):
            await query.answer("Побег здесь недоступен.", show_alert=True)
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
                clear_combat_backup(character)
                await session.flush()
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
    _append_logs(combat_state, coliseum_hooks.end_round_coliseum(combat_state, character))
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
    persist_combat_backup(character, combat_state)
    await session.flush()
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

    user = await user_repo.get_by_telegram_id(session, tid)
    char_early = await character_repo.get_by_user_id(session, user.id) if user is not None else None

    if not isinstance(combat_state, dict):
        if char_early is not None:
            clear_combat_backup(char_early)
            try:
                await session.flush()
            except Exception:
                pass
        await state.clear()
        return "Состояние боя сброшено. Открой /floor."

    if user is None or user.is_banned:
        if char_early is not None:
            clear_combat_backup(char_early)
            try:
                await session.flush()
            except Exception:
                pass
        await state.clear()
        return "Нет доступа."
    char = char_early
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
