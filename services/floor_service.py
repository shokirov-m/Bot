"""
Сборка текста экрана этажа и списка целей (монстры) для персонажа.
"""

from __future__ import annotations

import asyncio
import copy
import html
import json
import random

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from bot.i18n import get_locale
from bot.keyboards.floor_kb import (
    explore_floor_4_keyboard,
    explore_floor_4_event_keyboard,
    explore_floor_keyboard,
    explore_floor_22_keyboard,
    explore_floor_22_event_keyboard,
    floor_screen_keyboard,
    long_floor_screen_keyboard,
    room_clear_floor_keyboard,
    room_clear_floor_10_keyboard,
    room_clear_floor_24_keyboard,
    room_clear_floor_30_keyboard,
    room_clear_floor_40_keyboard,
    room_clear_floor_26_cleared_keyboard,
    room_clear_floor_26_keyboard,
    wave_floor_screen_keyboard,
    wave_floor_27_keyboard,
)
from bot.utils.game_ui import push_game_ui, remember_game_ui_anchor
from db.models.character import Character
from db.models.floor_progress import FloorProgress
from config import is_admin as config_is_admin
from db.repository import floor_progress_repo, inventory_repo
from game.characters import pets as pets_mod
from game.combat import night_mode as combat_night
from game.floors import floor_data
from game.locations import cities as city_locations
from game.floors import floor_entry_mods
from game.floors import long_floor as long_floor_mod
from game.items import materials
from game.floors import forest_beginnings as forest_beginnings_mod
from game.floors import room_clear_floor as rc_mod
from game.floors import room_clear_floor_10 as rc10_mod
from game.floors import room_clear_floor_24 as rc24_mod
from game.floors import room_clear_floor_30 as rc30_mod
from game.floors import room_clear_floor_40 as rc40_mod
from game.floors import room_clear_floor_26 as rc26_mod
from game.floors import rotten_swamps as rotten_swamps_mod
from game.floors import wave_floor as wv_mod
from game.floors import wave_floor_27 as wv27_mod
from game.floors import wandering_npcs as wandering_npcs_mod
from game.floors import explore_floor as exp_mod
from game.floors import explore_floor_4 as exp4_mod
from game.floors import explore_floor_22 as exp22_mod
from game.floors.tower_ascent import (
    clear_tower_ascent_pending,
    tower_next_floor_pending,
)
from services.rest_service import apply_completed_rest_if_needed
from game.items.equipment import UI_PLACEHOLDER_IMAGE_URL
from game.floors.monsters import FloorMonsterSpawn, build_spawns_for_floor
from services import golden_goblin_service
from services import character_service
from services.secret_chest_service import (
    SecretSearchOutcome,
    open_secret_chest,
    present_secret_chest,
)
from utils.game_images_prefs import game_images_enabled
from services.tutorial_battle_service import tutorial_battle_pending
from utils.image_assets import location_image_for_floor
from utils.ui import LINE_SEP, LINE_SEP_CITY


def get_spawns_for_character(character: Character) -> list[FloorMonsterSpawn]:
    """Варианты врагов на текущем этаже персонажа."""
    return build_spawns_for_floor(character.floor_number)


async def get_spawns_for_character_session(
    session: AsyncSession,
    character: Character,
) -> list[FloorMonsterSpawn]:
    """Спавны этажа + золотой гоблин (если мировое событие активно здесь)."""
    from game.mercenaries.shadow_market_meta import floor_26_shadow_cleared

    if int(character.floor_number) == 26 and floor_26_shadow_cleared(character):
        return []
    base = build_spawns_for_floor(character.floor_number)
    return await golden_goblin_service.merge_spawns_if_active(session, character, base)


def floor_navigation_ceiling_for_user(character: Character, telegram_user_id: int | None) -> int | None:
    """
    Для Telegram-админа навигация «Выше» до 135-го яруса; для остальных — по highest_floor_reached.
    None: в клавиатуре используется highest_floor_reached персонажа.
    """
    if telegram_user_id is None:
        return None
    return 135 if config_is_admin(telegram_user_id) else None


async def defeated_slot_codes_for_floor(
    session: AsyncSession,
    character_id: int,
    floor_number: int,
) -> frozenset[str]:
    """Слоты целей, уже побеждённых на этом этаже (для галочки в кнопке)."""
    row = await floor_progress_repo.ensure_floor_row(session, character_id, floor_number)
    extra = dict(row.extra or {})
    raw = extra.get("slots_cleared", [])
    if not isinstance(raw, list):
        return frozenset()
    return frozenset(str(x) for x in raw)


async def floor_keyboard_for_character(
    session: AsyncSession,
    character: Character,
    telegram_user_id: int | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа с отметками ✅ у побеждённых целей."""
    n = int(character.floor_number)
    # Город на 1 этаже не даёт боя — следующий ярус доступен без зачистки (кнопка «Выше»).
    if n == 1 and int(character.highest_floor_reached) < 2:
        character.highest_floor_reached = 2
        await session.flush()
    nav_ceiling = floor_navigation_ceiling_for_user(character, telegram_user_id)

    # Этаж 4 — исследование леса
    if exp4_mod.is_explore_floor_4(n):
        row = await floor_progress_repo.ensure_floor_row(session, character.id, n)
        _extra = dict(row.extra or {})
        return explore_floor_4_keyboard(character, extra=_extra, nav_ceiling=nav_ceiling)

    # Этаж 5 — зачистка комнат
    if rc_mod.is_room_clear_floor(n):
        rc_mod.ensure_started(character)
        defeated = await defeated_slot_codes_for_floor(session, character.id, n)
        return room_clear_floor_keyboard(character, defeated_slots=defeated, nav_ceiling=nav_ceiling)

    # Этаж 8 — исследование пещеры
    if exp_mod.is_explore_floor(n):
        row = await floor_progress_repo.ensure_floor_row(session, character.id, n)
        _extra = dict(row.extra or {})
        return explore_floor_keyboard(character, extra=_extra, nav_ceiling=nav_ceiling)

    # Этаж 10 — тёмные катакомбы (зачистка комнат)
    if rc10_mod.is_room_clear_floor_10(n):
        rc10_mod.ensure_started(character)
        defeated = await defeated_slot_codes_for_floor(session, character.id, n)
        return room_clear_floor_10_keyboard(character, defeated_slots=defeated, nav_ceiling=nav_ceiling)

    # Этаж 22 — исследование Пещеры Теней
    if exp22_mod.is_explore_floor_22(n):
        row = await floor_progress_repo.ensure_floor_row(session, character.id, n)
        _extra = dict(row.extra or {})
        return explore_floor_22_keyboard(character, extra=_extra, nav_ceiling=nav_ceiling)

    # Этаж 24 — зачистка комнат Пещер Теней
    if rc24_mod.is_room_clear_floor_24(n):
        rc24_mod.ensure_started(character)
        defeated = await defeated_slot_codes_for_floor(session, character.id, n)
        return room_clear_floor_24_keyboard(character, defeated_slots=defeated, nav_ceiling=nav_ceiling)

    # Этаж 30 — залы тьмы, затем босс зоны
    if rc30_mod.is_room_clear_floor_30(n):
        rc30_mod.ensure_started(character)
        defeated = await defeated_slot_codes_for_floor(session, character.id, n)
        return room_clear_floor_30_keyboard(character, defeated_slots=defeated, nav_ceiling=nav_ceiling)

    # Этаж 26 — зал сомнений / чёрный рынок после зачистки
    if rc26_mod.is_room_clear_floor_26(n):
        from game.mercenaries.shadow_market_meta import floor_26_shadow_cleared

        if floor_26_shadow_cleared(character):
            return room_clear_floor_26_cleared_keyboard(character, nav_ceiling=nav_ceiling)
        rc26_mod.ensure_started(character)
        defeated = await defeated_slot_codes_for_floor(session, character.id, n)
        return room_clear_floor_26_keyboard(character, defeated_slots=defeated, nav_ceiling=nav_ceiling)

    # Этаж 40 — ледяные залы, затем босс зоны
    if rc40_mod.is_room_clear_floor_40(n):
        rc40_mod.ensure_started(character)
        defeated = await defeated_slot_codes_for_floor(session, character.id, n)
        return room_clear_floor_40_keyboard(character, defeated_slots=defeated, nav_ceiling=nav_ceiling)

    # Этаж 27 — волны теней
    if wv27_mod.is_wave_floor_27(n):
        wv27_mod.ensure_started(character)
        defeated = await defeated_slot_codes_for_floor(session, character.id, n)
        return wave_floor_27_keyboard(character, defeated_slots=defeated, nav_ceiling=nav_ceiling)

    long_floor_mod.ensure_long_floor_started(character)
    if long_floor_mod.is_long_floor_active(character):
        return long_floor_screen_keyboard(character, nav_ceiling=nav_ceiling)
    spawns = await get_spawns_for_character_session(session, character)
    defeated = await defeated_slot_codes_for_floor(session, character.id, character.floor_number)
    return floor_screen_keyboard(character, spawns, defeated_slots=defeated, nav_ceiling=nav_ceiling)


def format_city_hub_message(character: Character) -> str:
    """Текст входа в город (кнопка «Город» на этаже)."""
    n = character.floor_number
    city = floor_data.get_city_for_floor(n)
    if city is None:
        return ""
    rich = city_locations.format_city_hub_rich_html(city)
    loc = get_locale(character, None)
    if int(n) == 1:
        hub = (
            "🛠️ <b>Сервисы:</b> кузница, таверна, <b>рынок</b> (лавка, скупщик, сейф банка, храм призыва питомца), "
            "NPC с лёгкими поручениями и стражник."
        )
        pet_hint = (
            "🐾 <b>Питомцы:</b> на этом ярусе первый дар — в <b>храме призыва</b> на рынке "
            "(один ритуал и до трёх перебросов)."
        )
        return f"{rich}\n{LINE_SEP_CITY}\n{pet_hint}\n{LINE_SEP_CITY}\n{hub}"
    hub = (
        "🛠️ <b>Сервисы:</b> кузница, таверна, лавка, поручение стражи, "
        "раздел <b>«Экономика»</b> (лотерея, ростовщик, сейф банка). "
        "Квесты странника — на боевых этажах (кнопка «К этажу»)."
    )
    pet_hint = pets_mod.format_city_hub_pets_hint_html(locale=loc)
    return f"{rich}\n{LINE_SEP_CITY}\n{pet_hint}\n{LINE_SEP_CITY}\n{hub}"


def _format_floor1_city_only(character: Character) -> str:
    """Этаж 1: только город (Тихий Ручей), без монстров / тайника / привала на карте."""
    n = int(character.floor_number)
    zone = floor_data.get_zone_for_floor(n)
    room = floor_data.epithet_for_floor(zone, n)
    city = floor_data.get_city_for_floor(n)
    lines: list[str] = []
    if combat_night.is_night_utc():
        lines.append(
            "🌑 <b>[НОЧЬ UTC]</b> <i>На боевых ярусах враги сильнее; здесь — безопасная зона.</i>",
        )
    lines.append(f"🗼 <b>ЭТАЖ {n}</b> / 135  {zone.emoji} <b>{html.escape(zone.name)}</b>")
    lines.append(f"📍 <i>{html.escape(room)}</i>")
    if city:
        lines.append(
            f"{city.emoji} <b>{html.escape(city.name)}</b> — мирный хаб. "
            "Зайди в «Город»: кузница, таверна, рынок (лавка, скупщик, банк, храм призыва).",
        )
    lines.append("📜 <b>Сюжетные NPC</b> — несколько необычных жителей ждут тебя здесь.")
    hi = int(character.highest_floor_reached)
    lines.append(f"🧭 Открыто 1–{hi}")
    pend = tower_next_floor_pending(character)
    if pend is not None:
        lines.append(f"✅ <b>Можно подняться</b> на этаж <b>{pend}</b>.")
    return "\n".join(lines)


def _format_explore_floor_4_message(character: Character) -> str:
    """Этаж 4 — короткое описание для экрана исследования леса."""
    n = character.floor_number
    zone = floor_data.get_zone_for_floor(n)
    room = floor_data.epithet_for_floor(zone, n)
    lines: list[str] = []
    if combat_night.is_night_utc():
        lines.append(
            "🌑 <b>[НОЧЬ UTC]</b> <i>Враги сильнее (<b>+20% HP/ATK</b>), "
            "после победы — <b>+40% золото и опыт</b>.</i>",
        )
    lines.append(f"🗼 <b>ЭТАЖ {n}</b> / 135  🌿 <b>Лес Начал</b>")
    lines.append(f"📍 <i>{html.escape(room)}</i>")
    lines.append(
        "<i>Густой лес хранит тайны. Исследуй чащу, находи добычу и сразись "
        "с Хранителем Рощи, чтобы открыть путь выше.</i>"
    )
    hi = int(character.highest_floor_reached)
    lines.append(f"🧭 Открыто 1–{hi} · ⬆️⬇️")
    pend = tower_next_floor_pending(character)
    if pend is not None:
        lines.append(f"✅ <b>Хранитель Рощи повержен.</b> Поднимись на этаж <b>{pend}</b>.")
    return "\n".join(lines)


def _format_explore_floor_message(character: Character) -> str:
    """Этаж 8 — короткое описание для экрана исследования (без стандартного мусора)."""
    n = character.floor_number
    zone = floor_data.get_zone_for_floor(n)
    room = floor_data.epithet_for_floor(zone, n)
    lines: list[str] = []
    if combat_night.is_night_utc():
        lines.append(
            "🌑 <b>[НОЧЬ UTC]</b> <i>Враги сильнее (<b>+20% HP/ATK</b>), "
            "после победы — <b>+40% золото и опыт</b>.</i>",
        )
    lines.append(f"🗼 <b>ЭТАЖ {n}</b> / 135  🗻 <b>Пещера Первородных</b>")
    lines.append(f"📍 <i>{html.escape(room)}</i>")
    lines.append(
        "<i>Тёмная пещера скрывает множество тайн. Исследуй каждый угол, "
        "чтобы пробудить Хранителя и открыть путь выше.</i>"
    )
    hi = int(character.highest_floor_reached)
    lines.append(f"🧭 Открыто 1–{hi} · ⬆️⬇️")
    pend = tower_next_floor_pending(character)
    if pend is not None:
        lines.append(f"✅ <b>Хранитель повержен.</b> Поднимись на этаж <b>{pend}</b>.")
    return "\n".join(lines)


def _format_explore_floor_22_message(character: Character) -> str:
    """Этаж 22 — описание для экрана исследования Пещеры Теней."""
    n = character.floor_number
    zone = floor_data.get_zone_for_floor(n)
    room = floor_data.epithet_for_floor(zone, n)
    lines: list[str] = []
    if combat_night.is_night_utc():
        lines.append(
            "🌑 <b>[НОЧЬ UTC]</b> <i>Враги сильнее (<b>+20% HP/ATK</b>), "
            "после победы — <b>+40% золото и опыт</b>.</i>",
        )
    lines.append(f"🗼 <b>ЭТАЖ {n}</b> / 135  🕳️ <b>Пещеры Теней</b>")
    lines.append(f"📍 <i>{html.escape(room)}</i>")
    lines.append(
        "<i>Тьма здесь живая. Каждый шаг — риск. Исследуй пещеру, "
        "уничтожь Ткача Теней и открой путь выше.</i>"
    )
    hi = int(character.highest_floor_reached)
    lines.append(f"🧭 Открыто 1–{hi} · ⬆️⬇️")
    pend = tower_next_floor_pending(character)
    if pend is not None:
        lines.append(f"✅ <b>Ткач Теней повержен.</b> Поднимись на этаж <b>{pend}</b>.")
    return "\n".join(lines)


def format_floor_message(character: Character, *, defeated_slots: frozenset[str] | None = None) -> str:
    """Текстовое описание текущего этажа (HTML) — коротко, без воды."""
    long_floor_mod.ensure_long_floor_started(character)
    n = character.floor_number
    if int(n) == 1 and not long_floor_mod.is_long_floor_active(character):
        return _format_floor1_city_only(character)
    # Этаж 4 — специальный экран исследования леса
    if exp4_mod.is_explore_floor_4(int(n)):
        return _format_explore_floor_4_message(character)
    # Этаж 8 — специальный экран исследования пещеры
    if exp_mod.is_explore_floor(int(n)):
        return _format_explore_floor_message(character)
    # Этаж 22 — исследование Пещеры Теней
    if exp22_mod.is_explore_floor_22(int(n)):
        return _format_explore_floor_22_message(character)
    zone = floor_data.get_zone_for_floor(n)
    room = floor_data.epithet_for_floor(zone, n)
    city = floor_data.get_city_for_floor(n)

    lines: list[str] = []
    if combat_night.is_night_utc():
        lines.append(
            "🌑 <b>[НОЧЬ UTC]</b> <i>Враги сильнее (<b>+20% HP/ATK</b>), "
            "после победы — <b>+40% золото и опыт</b>. Играй с оглядкой.</i>",
        )
    lines.append(f"🗼 <b>ЭТАЖ {n}</b> / 135  {zone.emoji} <b>{html.escape(zone.name)}</b>")
    lines.append(f"📍 <i>{html.escape(room)}</i>")
    if not long_floor_mod.is_long_floor_active(character):
        zd = zone.description
        short = zd if len(zd) <= 80 else zd[:77] + "…"
        lines.append(f"<i>{html.escape(short)}</i>")

    if long_floor_mod.is_long_floor_active(character):
        lines.append(long_floor_mod.format_long_floor_banner_html())

    if rc_mod.is_room_clear_floor(int(n)):
        _ds = defeated_slots if defeated_slots is not None else frozenset()
        lines.append(rc_mod.format_room_clear_banner_html(_ds))

    if rc10_mod.is_room_clear_floor_10(int(n)):
        _ds = defeated_slots if defeated_slots is not None else frozenset()
        lines.append(rc10_mod.format_room_clear_banner_html(_ds))

    if rc24_mod.is_room_clear_floor_24(int(n)):
        _ds = defeated_slots if defeated_slots is not None else frozenset()
        lines.append(rc24_mod.format_room_clear_banner_html(_ds))

    if rc30_mod.is_room_clear_floor_30(int(n)):
        _ds = defeated_slots if defeated_slots is not None else frozenset()
        lines.append(rc30_mod.format_room_clear_banner_html(_ds))

    if rc26_mod.is_room_clear_floor_26(int(n)):
        from game.mercenaries.shadow_market_meta import floor_26_shadow_cleared

        _ds = defeated_slots if defeated_slots is not None else frozenset()
        if floor_26_shadow_cleared(character):
            lines.append(
                "🌑 <b>Зал пуст.</b> Монстры не вернутся. <b>Тёмный проход</b> ведёт к рынку «Тени Башни».",
            )
        else:
            lines.append(rc26_mod.format_room_clear_banner_html(_ds))

    if rc40_mod.is_room_clear_floor_40(int(n)):
        _ds = defeated_slots if defeated_slots is not None else frozenset()
        lines.append(rc40_mod.format_room_clear_banner_html(_ds))

    if wv27_mod.is_wave_floor_27(int(n)):
        _ds = defeated_slots if defeated_slots is not None else frozenset()
        lines.append(wv27_mod.format_wave_floor_27_banner_html(_ds))

    # Волновой баннер только если этаж 10 НЕ переопределён room_clear_10
    if wv_mod.is_wave_floor(int(n)) and not rc10_mod.is_room_clear_floor_10(int(n)):
        _ds = defeated_slots if defeated_slots is not None else frozenset()
        lines.append(wv_mod.format_wave_floor_banner_html(_ds))

    if city:
        lines.append(f"{city.emoji} <b>{html.escape(city.name)}</b> — зайди в «Город».")

    tags: list[str] = []
    if floor_data.is_mini_boss_floor(n):
        tags.append("⚔️ Мини-босс")
    if floor_data.is_major_boss_floor(n):
        tags.append("👑 Босс этажа")
    if tags:
        lines.append(" · ".join(tags))

    wn = wandering_npcs_mod.wandering_npc_for_floor(int(character.id), n)
    if wn:
        lines.append(f"🎭 <b>{html.escape(wn['title'])}</b> — кнопка «{html.escape(wn['button'])}».")

    if tutorial_battle_pending(character) and n == 2:
        lines.append("🎓 <b>Учебный бой</b> наставника — кнопка ниже.")
    else:
        try:
            from services import tutorial_service

            tutorial_service.advance_step_if_needed(character)
            step = tutorial_service.current_step(character)
            if step == tutorial_service.STEP_EQUIP:
                lines.append("🧩 <b>Шаг 2:</b> зайди в <b>Инвентарь</b> и надень оружие/броню.")
            elif step == tutorial_service.STEP_UNLOCKS and int(character.level or 1) < 5:
                lines.append("🧩 <b>Шаг 3:</b> побеждай в боях — на <b>5 ур.</b> откроются новые разделы.")
        except Exception:
            pass

    if rotten_swamps_mod.is_rotten_swamps_zone(n):
        lines.append("🌿 <b>Болота:</b> туман −5 HP перед боем · пиявки · лагерь (кнопка).")

    # События-ауры этажей (дебаффы/баффы), начиная с 21-го.
    try:
        from game.floors.aura import get_floor_aura

        aura = get_floor_aura(int(n))
        if isinstance(aura, dict) and aura.get("name") and aura.get("emoji"):
            desc = str(aura.get("desc") or "").strip()
            if desc:
                lines.append(f"{aura['emoji']} <b>{html.escape(str(aura['name']))}</b>: <i>{html.escape(desc)}</i>")
            else:
                lines.append(f"{aura['emoji']} <b>{html.escape(str(aura['name']))}</b>")
    except Exception:
        pass

    # Survival floor banner (frozen_wastes, floors 111-120)
    floor_type = floor_data.get_zone_floor_type(n)
    if floor_type == "survival":
        zone_raw = floor_data.get_zone_raw(n)
        debuff = zone_raw.get("debuff", {})
        prot_name = debuff.get("protection_item_name", "защитный предмет")
        hp_loss = debuff.get("hp_per_min", 50)
        mp = dict(character.meta_progress or {})
        has_protection = bool(mp.get(f"survival_prot_{zone.key}"))
        if has_protection:
            lines.append(f"🧊 <b>Выживание:</b> защита активна ✅ (−{hp_loss} HP/мин без неё).")
        else:
            lines.append(
                f"🥶 <b>⚠️ ВЫЖИВАНИЕ:</b> каждую минуту −{hp_loss} HP от холода! "
                f"Скрафти <b>{html.escape(prot_name)}</b> у алхимика, чтобы защититься."
            )

    # Faction war floor banner (faction_war_plains, floors 121-134)
    if floor_type == "faction_war":
        zone_raw = floor_data.get_zone_raw(n)
        factions = zone_raw.get("factions", {})
        req = zone_raw.get("reputation_required", 1000)
        mp = dict(character.meta_progress or {})
        chosen = mp.get(f"faction_choice_{zone.key}")
        rep_data = mp.get(f"faction_rep_{zone.key}", {})
        if chosen and chosen in factions:
            fac = factions[chosen]
            rep = int(rep_data.get(chosen, 0))
            enemy_fac = factions.get(fac.get("enemy_key", ""), {})
            enemy_name = enemy_fac.get("name", "враг")
            if rep >= req:
                lines.append(
                    f"⚔️ <b>Война Фракций</b> — {fac['emoji']} {fac['name']}: "
                    f"репутация <b>{rep}/{req}</b> ✅ Генерал доступен! (босс-кнопка)"
                )
            else:
                lines.append(
                    f"⚔️ <b>Война Фракций</b> — {fac['emoji']} {fac['name']}: "
                    f"репутация <b>{rep}/{req}</b> · убивай {html.escape(enemy_name)}."
                )
        else:
            fac_list = " / ".join(f"{v['emoji']} {v['name']}" for v in factions.values())
            lines.append(
                f"⚔️ <b>Война Фракций:</b> выбери сторону — {fac_list}. "
                f"(кнопка «Выбрать фракцию»)"
            )

    hi = int(character.highest_floor_reached)
    lines.append(f"🧭 Открыто 1–{hi}")

    pend = tower_next_floor_pending(character)
    if pend is not None:
        lines.append(f"✅ <b>Ярус зачищен.</b> Поднимись на <b>{pend}</b> этаж.")
    return "\n".join(lines)


def format_floor_message_photo_caption(character: Character) -> str:
    """
    Короткий текст под фото этажа (лимит подписи Telegram ~1024 символа).
    Без длинного описания зоны — полный текст по-прежнему без фото или в логике без картинки.
    """
    long_floor_mod.ensure_long_floor_started(character)
    n = character.floor_number
    if int(n) == 1 and not long_floor_mod.is_long_floor_active(character):
        zone = floor_data.get_zone_for_floor(n)
        room = floor_data.epithet_for_floor(zone, n)
        city = floor_data.get_city_for_floor(n)
        pend = tower_next_floor_pending(character)
        bits = [
            f"{zone.emoji} <b>{html.escape(zone.name)}</b> · <b>1</b>/135",
            f"📍 <i>{html.escape(room)}</i>",
            f"{city.emoji} <b>{html.escape(city.name)}</b> — мирный хаб, рынок в городе",
            "Без боёв на карте · тайник и привал — со 2-го",
        ]
        if pend is not None:
            bits.append(f"✅ Подъём на <b>{pend}</b>")
        return "\n".join(bits)
    # Этаж 8 — исследование
    if exp_mod.is_explore_floor(int(n)):
        zone = floor_data.get_zone_for_floor(n)
        room = floor_data.epithet_for_floor(zone, n)
        pend = tower_next_floor_pending(character)
        bits = [
            f"🗻 <b>Пещера Первородных</b> · <b>{n}</b>/100",
            f"📍 <i>{html.escape(room)}</i>",
            "🔍 Исследование · нажми кнопку ниже",
        ]
        if pend is not None:
            bits.append(f"✅ Подъём на <b>{pend}</b>")
        return "\n".join(bits)
    zone = floor_data.get_zone_for_floor(n)
    room = floor_data.epithet_for_floor(zone, n)
    city = floor_data.get_city_for_floor(n)

    lines: list[str] = []
    if combat_night.is_night_utc():
        lines.append("🌑 <b>[НОЧЬ]</b> <i>+20% твари · +40% награда</i>")
    lines.append(f"🗼 <b>ЭТАЖ {n}</b>  {zone.emoji} <b>{html.escape(zone.name)}</b>")
    lines.append(f"📍 <i>{html.escape(room)}</i>")
    if long_floor_mod.is_long_floor_active(character):
        b = long_floor_mod.format_long_floor_banner_html()
        lines.append(b if len(b) <= 120 else b[:117] + "…")
    if rc_mod.is_room_clear_floor(int(n)):
        b = rc_mod.format_room_clear_banner_html(frozenset())
        lines.append(b if len(b) <= 120 else b[:117] + "…")
    if rc10_mod.is_room_clear_floor_10(int(n)):
        b = rc10_mod.format_room_clear_banner_html(frozenset())
        lines.append(b if len(b) <= 120 else b[:117] + "…")
    if rc24_mod.is_room_clear_floor_24(int(n)):
        b = rc24_mod.format_room_clear_banner_html(frozenset())
        lines.append(b if len(b) <= 120 else b[:117] + "…")
    if rc30_mod.is_room_clear_floor_30(int(n)):
        b = rc30_mod.format_room_clear_banner_html(frozenset())
        lines.append(b if len(b) <= 120 else b[:117] + "…")
    if rc26_mod.is_room_clear_floor_26(int(n)):
        from game.mercenaries.shadow_market_meta import floor_26_shadow_cleared

        if floor_26_shadow_cleared(character):
            lines.append("🌑 Зал пуст · Тёмный проход к рынку")
        else:
            b = rc26_mod.format_room_clear_banner_html(frozenset())
            lines.append(b if len(b) <= 120 else b[:117] + "…")
    if rc40_mod.is_room_clear_floor_40(int(n)):
        b = rc40_mod.format_room_clear_banner_html(frozenset())
        lines.append(b if len(b) <= 120 else b[:117] + "…")
    if exp4_mod.is_explore_floor_4(int(n)):
        lines.append("🔍 Исследование леса · нажми кнопку ниже")
    if exp_mod.is_explore_floor(int(n)):
        lines.append("🔍 Исследование · нажми кнопку ниже")
    if exp22_mod.is_explore_floor_22(int(n)):
        lines.append("🕯️ Исследование пещеры · нажми кнопку ниже")
    if wv27_mod.is_wave_floor_27(int(n)):
        b = wv27_mod.format_wave_floor_27_banner_html(frozenset())
        lines.append(b if len(b) <= 120 else b[:117] + "…")
    if wv_mod.is_wave_floor(int(n)) and not rc10_mod.is_room_clear_floor_10(int(n)):
        b = wv_mod.format_wave_floor_banner_html(frozenset())
        lines.append(b if len(b) <= 120 else b[:117] + "…")
    if city:
        lines.append(f"{city.emoji} <b>{html.escape(city.name)}</b> — город")
    tags: list[str] = []
    if floor_data.is_mini_boss_floor(n):
        tags.append("⚔️ Мини-босс")
    if floor_data.is_major_boss_floor(n):
        tags.append("👑 Босс")
    if tags:
        lines.append(" · ".join(tags))
    wn = wandering_npcs_mod.wandering_npc_for_floor(int(character.id), n)
    if wn:
        lines.append(html.escape(f"🎭 {wn['title']} — кнопка «{wn['button']}»"))
    if tutorial_battle_pending(character) and n == 1:
        lines.append("🎓 Учебный бой — внизу")
    if rotten_swamps_mod.is_rotten_swamps_zone(n):
        lines.append("🌿 Болота: туман −5 HP · пиявки · лагерь")
    hi = int(character.highest_floor_reached)
    lines.append(f"🧭 1–{hi}")
    pend = tower_next_floor_pending(character)
    if pend is not None:
        lines.append(f"✅ Подъём на <b>{pend}</b>")
    return "\n".join(lines)


def _clamp_telegram_caption(html: str, max_len: int = 1020) -> str:
    if len(html) <= max_len:
        return html
    return html[: max_len - 1] + "…"


async def maybe_roll_floor_entry_event(
    session: AsyncSession,
    character: Character,
    row: FloorProgress,
) -> str:
    """
    Один бросок при первом «заходе» на этаж (visits == 0): ~20% особое событие.
    Не срабатывает на длинном этаже-сценарии. Расширяемый набор: звезда, лавка,
    ловушка, благословение; туман, проклятие, склад, дух-дуэль, молния.
    """
    if long_floor_mod.is_long_floor_active(character):
        return ""
    if int(row.visits) != 0:
        return ""
    ex = dict(row.extra or {})
    if ex.get("_entry_rand_v0"):
        return ""
    ex["_entry_rand_v0"] = True
    row.extra = ex
    if random.random() >= float(floor_entry_mods.FLOOR_ENTRY_EVENT_CHANCE):
        await session.flush()
        return ""

    # База + мир: чуть реже вредные, чтобы не срывать сессии.
    roll = random.choices(
        (
            "star",
            "merchant",
            "trap",
            "bless",
            "fog",
            "cursed",
            "warehouse",
            "spirit",
            "lightning",
        ),
        weights=(1, 1, 0.75, 1, 0.9, 0.65, 0.8, 0.55, 0.7),
        k=1,
    )[0]
    kind = str(roll)
    mp = dict(character.meta_progress or {})
    frag = ""
    if kind == "star":
        mp["next_battle_xp_mult"] = max(float(mp.get("next_battle_xp_mult") or 1.0), 1.5)
        frag = (
            f"{LINE_SEP}\n⭐ <b>Случайное событие — упавшая звезда!</b>\n"
            "<i>Следующий бой даст на <b>50%</b> больше опыта.</i>"
        )
    elif kind == "merchant":
        mp["merchant_discount_charges"] = int(mp.get("merchant_discount_charges") or 0) + 3
        frag = (
            f"{LINE_SEP}\n🏪 <b>Случайное событие — бродячий торговец!</b>\n"
            "<i>Следующие <b>три</b> покупки в лавке: цена <b>−30%</b>.</i>"
        )
    elif kind == "trap":
        nh = max(1, int(int(character.hp_current) * 0.85))
        character.hp_current = nh
        frag = (
            f"{LINE_SEP}\n⚠️ <b>Случайное событие — ловушка!</b>\n"
            f"<i>Ты теряешь <b>~15%</b> HP (осталось {nh}/{int(character.hp_max)}).</i>"
        )
    elif kind == "fog":
        mp[floor_entry_mods.FLOOR_MOD_META_KEY] = {
            "fog_taken_mult": 0.8,
            "gold_mult": 1.3,
        }
        frag = (
            f"{LINE_SEP}\n🌫️ <b>Густой туман</b> окутывает коридор!\n"
            "<i>Следующий бой: <b>−20%</b> получаемого от врага урона, <b>+30%</b> к золоту с победы.</i>"
        )
    elif kind == "cursed":
        mp[floor_entry_mods.FLOOR_MOD_META_KEY] = {"cursed": True, "cursed_dmg": 5}
        frag = (
            f"{LINE_SEP}\n🕯️ <b>Проклятие</b> висит в воздухе…\n"
            "<i>Следующий бой: каждые 2 твоих хода — <b>−5 HP</b> (зональный урон).</i>"
        )
    elif kind == "warehouse":
        wh_note = ""
        free = await inventory_repo.first_free_bag_slot(session, character.id)
        if free is not None:
            pl = materials.material_payload("uncommon", random.randint(1, 3))
            await inventory_repo.add_bag_item(
                session, character.id, copy.deepcopy(pl), bag_slot=free
            )
            wn = html.escape(str(pl.get("name", "Материал")))
            wh_note = f" <b>{wn}</b> ({int(pl.get('count', 1))}×) в сумку."
        else:
            wh_note = " <i>сумка полна</i> — приходи с местом, чтобы взять припасы."
        frag = (
            f"{LINE_SEP}\n📦 <b>Покинутый склад</b> на стороне пути!{wh_note}"
        )
    elif kind == "spirit":
        k = floor_entry_mods.SPIRIT_ARENA_FIGHTS_KEY
        mp[k] = int(mp.get(k) or 0) + 1
        frag = (
            f"{LINE_SEP}\n👻 <b>Дух вызывает на дуэль</b> — в награду даёт <b>запасной бой на арене</b>.\n"
            "<i>Один матч <b>без расхода дневного лимита</b> (тратится при награде/учёте боя).</i>"
        )
    elif kind == "lightning":
        mp[floor_entry_mods.FLOOR_MOD_META_KEY] = {"lightning_exec": 0.15}
        frag = (
            f"{LINE_SEP}\n⚡ <b>Грохочет дальняя буря!</b>\n"
            "<i>Следующий бой: враг ниже <b>15% HP</b> — мгновенная <b>казнь молнией</b> (после твоей атаки/скилла).</i>"
        )
    else:  # bless
        character.hp_current = int(character.hp_max)
        character.mp_current = int(character.mp_max)
        frag = (
            f"{LINE_SEP}\n✨ <b>Случайное событие — благословение!</b>\n"
            "<i>HP и MP полностью восстановлены.</i>"
        )
    character.meta_progress = mp
    await session.flush()
    return frag


async def push_floor_screen_ui(
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    *,
    chat_id: int,
    character: Character,
    reply_markup: InlineKeyboardMarkup,
    target_message: Message | None = None,
    fallback_message: Message | None = None,
    text_suffix: str = "",
) -> None:
    """Экран этажа: случайное событие (10%), заставка при первом заходе (visits==0), затем полный текст."""
    if apply_completed_rest_if_needed(character):
        await session.flush()
    n = int(character.floor_number)
    row = await floor_progress_repo.ensure_floor_row(session, character.id, n)
    event_html = await maybe_roll_floor_entry_event(session, character, row)
    gg_banner = await golden_goblin_service.html_banner_for_floor(session, n)
    gg_photo = await golden_goblin_service.html_banner_photo_caption(session, n)
    zone = floor_data.get_zone_for_floor(n)
    room = floor_data.epithet_for_floor(zone, n)
    ex = dict(row.extra or {})
    splash_needed = int(row.visits) == 0 and not ex.get("_floor_intro_anim_v0")
    # Для баннеров с прогрессом — читаем cleared slots
    _cleared_slots: frozenset[str] = frozenset()
    if (rc_mod.is_room_clear_floor(n) or rc10_mod.is_room_clear_floor_10(n)
            or rc24_mod.is_room_clear_floor_24(n) or rc30_mod.is_room_clear_floor_30(n)
            or rc26_mod.is_room_clear_floor_26(n) or rc40_mod.is_room_clear_floor_40(n)
            or wv_mod.is_wave_floor(n) or wv27_mod.is_wave_floor_27(n)):
        _raw_cleared = list((ex.get("slots_cleared") or []))
        _cleared_slots = frozenset(str(x) for x in _raw_cleared)
    # Баннер прогресса исследования (этаж 4 — лес, этаж 8 — пещера, этаж 22 — тени)
    _explore_banner = ""
    if exp4_mod.is_explore_floor_4(n):
        _explore_banner = "\n" + exp4_mod.format_explore_banner_html(ex)
    elif exp_mod.is_explore_floor(n):
        _explore_banner = "\n" + exp_mod.format_explore_banner_html(ex)
    elif exp22_mod.is_explore_floor_22(n):
        _explore_banner = "\n" + exp22_mod.format_explore_banner_html(ex)
    full_body = format_floor_message(character, defeated_slots=_cleared_slots) + _explore_banner + gg_banner + event_html + text_suffix
    photo = location_image_for_floor(n) if game_images_enabled(character) else None
    if photo is None and game_images_enabled(character):
        photo = UI_PLACEHOLDER_IMAGE_URL
    body_for_ui = (
        _clamp_telegram_caption(
            format_floor_message_photo_caption(character) + gg_photo + event_html + text_suffix
        )
        if photo is not None
        else full_body
    )

    if splash_needed and photo is None:
        ex["_floor_intro_anim_v0"] = True
        row.extra = ex
        await session.flush()
        splash = f"🗼 <b>ЭТАЖ {n}</b> — <i>{html.escape(room)}</i>"
        if target_message is not None and target_message.chat.id == chat_id:
            if not target_message.photo:
                try:
                    await target_message.edit_text(splash, parse_mode=ParseMode.HTML, reply_markup=None)
                    await asyncio.sleep(0.5)
                except Exception:
                    pass
            await push_game_ui(
                state,
                bot,
                chat_id=chat_id,
                text=full_body,
                reply_markup=reply_markup,
                target_message=target_message,
                fallback_message=fallback_message,
                photo_path=None,
                character=character,
            )
            return
        if fallback_message is not None and fallback_message.chat.id == chat_id:
            try:
                intro = await fallback_message.answer(splash, parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.5)
                await intro.edit_text(
                    full_body,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                )
                await remember_game_ui_anchor(state, intro)
                return
            except Exception:
                pass
    elif splash_needed and photo is not None:
        ex["_floor_intro_anim_v0"] = True
        row.extra = ex
        await session.flush()

    await push_game_ui(
        state,
        bot,
        chat_id=chat_id,
        text=body_for_ui,
        reply_markup=reply_markup,
        target_message=target_message,
        fallback_message=fallback_message,
        photo_path=photo,
        character=character,
    )


def _floor_progress_extra_as_dict(raw: object) -> dict[str, object]:
    """Нормализация floor_progress.extra: JSON иногда приходит строкой — ``dict(raw)`` даёт ValueError."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return {}
        try:
            parsed = json.loads(s)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


async def travel_to_floor(
    session: AsyncSession,
    character: Character,
    target_floor: int,
    *,
    telegram_id: int | None = None,
    username: str | None = None,
    bot: Bot | None = None,
    admin_floor_bypass: bool = False,
) -> tuple[bool, str | None]:
    """Перейти на целевой этаж. Обычно 1..highest_floor_reached; админ — до 135 с автоподъёмом highest."""

    tower_top = 135
    old_floor = int(character.floor_number)

    if admin_floor_bypass:
        if target_floor < 1 or target_floor > tower_top:
            return False, f"Этаж вне допустимого диапазона (1–{tower_top})."
        if int(character.highest_floor_reached) < target_floor:
            character.highest_floor_reached = target_floor
    else:
        hi = int(character.highest_floor_reached)
        if target_floor < 1 or target_floor > hi:
            return False, "Этаж ещё не открыт или недоступен."
    if old_floor != int(target_floor):
        rotten_swamps_mod.on_travel_floor_change(character, old_floor, int(target_floor))
    if target_floor > old_floor:
        clear_tower_ascent_pending(character)
    if old_floor == 10 and target_floor == 11:
        mp = dict(character.meta_progress or {})
        mp.pop(forest_beginnings_mod.META_KEY, None)
        character.meta_progress = mp
    character.floor_number = target_floor
    await session.flush()
    if telegram_id is not None and target_floor != old_floor:
        from services import anticheat_service

        await anticheat_service.record_floor_change(
            session,
            character,
            telegram_id=telegram_id,
            username=username,
            old_floor=old_floor,
            new_floor=target_floor,
            bot=bot,
        )
    return True, None


async def travel_by_delta(
    session: AsyncSession,
    character: Character,
    delta: int,
    *,
    telegram_id: int | None = None,
    username: str | None = None,
    bot: Bot | None = None,
    admin_floor_bypass: bool = False,
) -> tuple[bool, str | None]:
    """Сдвиг текущего этажа на ±1 (или иной delta) в рамках открытых."""
    nxt = int(character.floor_number) + delta
    return await travel_to_floor(
        session,
        character,
        nxt,
        telegram_id=telegram_id,
        username=username,
        bot=bot,
        admin_floor_bypass=admin_floor_bypass,
    )


async def try_secret_search(
    session: AsyncSession,
    character: Character,
) -> SecretSearchOutcome:
    """Шаг 1 тайника: показать закрытый сундук (подробности в secret_chest_service)."""
    return await present_secret_chest(session, character)
