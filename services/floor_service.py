"""
Сборка текста экрана этажа и списка целей (монстры) для персонажа.
"""

from __future__ import annotations

import asyncio
import copy
import html
import random
from dataclasses import dataclass

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale
from bot.keyboards.floor_kb import floor_screen_keyboard, long_floor_screen_keyboard
from bot.utils.game_ui import push_game_ui, remember_game_ui_anchor
from db.models.character import Character
from db.models.floor_progress import FloorProgress
from db.repository import floor_progress_repo, inventory_repo
from game.characters import pets as pets_mod
from game.combat import night_mode as combat_night
from game.floors import floor_data
from game.locations import cities as city_locations
from game.floors import long_floor as long_floor_mod
from game.floors import forest_beginnings as forest_beginnings_mod
from game.floors import rotten_swamps as rotten_swamps_mod
from game.floors import wandering_npcs as wandering_npcs_mod
from game.floors.tower_ascent import (
    clear_tower_ascent_pending,
    ensure_peaceful_city_hub_ascent,
    tower_next_floor_pending,
)
from services.rest_service import apply_completed_rest_if_needed
from game.items.equipment import (
    SECRET_GEAR_DROP_CHANCE,
    SECRET_GEAR_EARLY_MAX_FLOOR,
    UI_PLACEHOLDER_IMAGE_URL,
    try_roll_secret_gear_payload,
)
from game.floors.monsters import FloorMonsterSpawn, build_spawns_for_floor
from services import character_service, title_service
from utils.game_images_prefs import game_images_enabled
from services.tutorial_battle_service import tutorial_battle_pending
from utils.image_assets import location_image_for_floor
from utils.ui import LINE_SEP, LINE_SEP_CITY


def get_spawns_for_character(character: Character) -> list[FloorMonsterSpawn]:
    """Варианты врагов на текущем этаже персонажа."""
    return build_spawns_for_floor(character.floor_number)


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
) -> InlineKeyboardMarkup:
    """Клавиатура этажа с отметками ✅ у побеждённых целей."""
    long_floor_mod.ensure_long_floor_started(character)
    if long_floor_mod.is_long_floor_active(character):
        return long_floor_screen_keyboard(character)
    spawns = get_spawns_for_character(character)
    defeated = await defeated_slot_codes_for_floor(session, character.id, character.floor_number)
    return floor_screen_keyboard(character, spawns, defeated_slots=defeated)


def format_city_hub_message(character: Character) -> str:
    """Текст входа в город (кнопка «Город» на этаже)."""
    n = character.floor_number
    city = floor_data.get_city_for_floor(n)
    if city is None:
        return ""
    rich = city_locations.format_city_hub_rich_html(city)
    loc = get_locale(character, None)
    if int(n) == 3:
        hub = (
            "🛠️ <b>Сервисы:</b> кузница, таверна, <b>рынок</b> (лавка, скупщик, сейф банка, храм призыва питомца), "
            "NPC с лёгкими поручениями и стражник."
        )
        pet_hint = (
            "🐾 <b>Питомцы:</b> на этом ярусе первый дар — в <b>храме призыва</b> на рынке "
            "(один ритуал и до трёх перебросов); дальше — как обычно в городах башни."
        )
        return f"{rich}\n{LINE_SEP_CITY}\n{pet_hint}\n{LINE_SEP_CITY}\n{hub}"
    hub = (
        "🛠️ <b>Сервисы:</b> кузница, таверна, лавка, поручение стражи, "
        "раздел <b>«Экономика»</b> (лотерея, ростовщик, сейф банка). "
        "Квесты странника — на боевых этажах (кнопка «К этажу»)."
    )
    pet_hint = pets_mod.format_city_hub_pets_hint_html(locale=loc)
    return f"{rich}\n{LINE_SEP_CITY}\n{pet_hint}\n{LINE_SEP_CITY}\n{hub}"


def _format_floor3_city_only(character: Character) -> str:
    """Этаж 3: только город, без монстров / тайника / привала на карте."""
    n = int(character.floor_number)
    zone = floor_data.get_zone_for_floor(n)
    room = floor_data.epithet_for_floor(zone, n)
    city = floor_data.get_city_for_floor(n)
    lines: list[str] = []
    if combat_night.is_night_utc():
        lines.append(
            "🌑 <b>[НОЧЬ UTC]</b> <i>На боевых ярусах враги сильнее; здесь — безопасная зона.</i>",
        )
    lines.append(f"{zone.emoji} <b>{html.escape(zone.name)}</b> · этаж <b>{n}</b>/100")
    lines.append(f"📍 <i>{html.escape(room)}</i>")
    if city:
        lines.append(
            f"{city.emoji} <b>{html.escape(city.name)}</b> — <b>мирный хаб</b>: без боёв на площади. "
            "Зайди в <b>Город</b> — кузница, таверна, <b>рынок</b> (лавка, скупщик, банк, храм призыва), NPC.",
        )
    lines.append("🌲 Дальше по башне (4–10) — обычные цели, привал и тайники по правилам леса.")
    hi = int(character.highest_floor_reached)
    lines.append(f"🧭 Открыто 1–{hi} · ⬆️⬇️ · на этом ярусе нет врагов для боя.")
    pend = tower_next_floor_pending(character)
    if pend is not None:
        lines.append(
            f"✅ <b>Можно подняться</b> на этаж <b>{pend}</b> — кнопка «Этаж {pend}» или «⬆️ Выше».",
        )
    else:
        lines.append("⬆️ Когда будешь готов к лесу — поднимись на следующий ярус.")
    lines.append("<i>Боёв на этом экране нет (−0 ⚡).</i>")
    return "\n".join(lines)


def format_floor_message(character: Character) -> str:
    """Текстовое описание текущего этажа (HTML) — коротко, без воды."""
    long_floor_mod.ensure_long_floor_started(character)
    n = character.floor_number
    if int(n) == 3 and not long_floor_mod.is_long_floor_active(character):
        return _format_floor3_city_only(character)
    zone = floor_data.get_zone_for_floor(n)
    room = floor_data.epithet_for_floor(zone, n)
    city = floor_data.get_city_for_floor(n)

    lines: list[str] = []
    if combat_night.is_night_utc():
        lines.append(
            "🌑 <b>[НОЧЬ UTC]</b> <i>Враги сильнее (<b>+20% HP/ATK</b>), "
            "после победы — <b>+40% золото и опыт</b>. Играй с оглядкой.</i>",
        )
    lines.append(f"{zone.emoji} <b>{html.escape(zone.name)}</b> · этаж <b>{n}</b>/100")
    lines.append(f"📍 <i>{html.escape(room)}</i>")
    if not long_floor_mod.is_long_floor_active(character):
        zd = zone.description
        if combat_night.is_night_utc():
            zd = f"🌑 Ночь в башне: {zd}"
        short = zd if len(zd) <= 140 else zd[:137] + "…"
        lines.append(f"<i>{html.escape(short)}</i>")

    if long_floor_mod.is_long_floor_active(character):
        lines.append(long_floor_mod.format_long_floor_banner_html())

    if city:
        lines.append(f"{city.emoji} <b>{html.escape(city.name)}</b> — «Город»: кузница, лавка, таверна.")

    tags: list[str] = []
    if floor_data.has_quest_npc(n) and int(n) != 3:
        tags.append("📜 Квесты")
    if floor_data.has_trader(n):
        tags.append("🏛️ Рынок / лавка — в городе" if int(n) == 3 else "🏪 Лавка — в городе")
    if floor_data.is_mini_boss_floor(n):
        tags.append("⚔️ Мини-босс")
    if floor_data.is_major_boss_floor(n):
        tags.append("👑 Босс этажа")
    if tags:
        lines.append(" · ".join(tags))

    wn = wandering_npcs_mod.wandering_npc_for_floor(int(character.id), n)
    if wn:
        lines.append(
            f"🎭 <b>{html.escape(wn['title'])}</b> — <i>{html.escape(wn['hint'])}</i> "
            f"(кнопка «{html.escape(wn['button'])}»).",
        )

    if tutorial_battle_pending(character) and n == 1:
        lines.append("🎓 <b>Учебный бой</b> наставника — кнопка ниже.")

    sec = f"🔮 Тайник после боя ~{int(floor_data.SECRET_ROOM_CHANCE * 100)}%"
    if n <= SECRET_GEAR_EARLY_MAX_FLOOR:
        sec += ", иногда экипировка"
    else:
        sec += f", экип ~{int(SECRET_GEAR_DROP_CHANCE * 100)}%"
    lines.append(sec + ".")

    if n in pets_mod.pet_gacha_floors_for_pet_switch():
        lines.append(
            "🐾 <b>Питомцы:</b> призыв в «Город» (лавка). Пассив в бою — у <b>одного</b> активного; "
            "смена здесь кнопкой или в статусе.",
        )
    elif int(n) == 3:
        lines.append(
            "🐾 <b>Питомцы:</b> на 3 ярусе — храм призыва в городе на <b>рынке</b>; "
            "пассив в бою у <b>одного</b> активного.",
        )

    hi = int(character.highest_floor_reached)
    lines.append(f"🧭 Открыто 1–{hi} · ⬆️⬇️ · при входе цели сбрасываются.")

    if n < 100 and not long_floor_mod.is_long_floor_active(character):
        lines.append("🗝️ Новый ярус: зачисти все цели, затем кнопка «Этаж N» или ⬆️ Выше.")
    if forest_beginnings_mod.is_forest_beginnings_zone(n) and int(n) != 3:
        lines.append(
            "🌲 <b>Лес Начал (1–10)</b> — обучение: "
            "<i>грибы</i> (шанс перед боем с обычной целью), <i>дух</i> (1× за проход зоны); "
            "кнопка «Привал» — полное HP/MP без стамины (1× за проход).",
        )
    if rotten_swamps_mod.is_rotten_swamps_zone(n):
        lines.append(
            "🌿 <b>Гнилые Болота (11–20)</b>: "
            "<i>токсичный туман</i> (−5 HP перед каждым боем, нет урона при <b>защите снаряжения ≥5</b>); "
            "<i>пиявки</i> — после боя шанс яда на <b>следующем этаже</b>; "
            "<i>густой туман</i> скрывает обычных монстров на списке целей; "
            "кнопка «Заброшенный лагерь» — случайный предмет <b>или</b> ловушка (1× за проход зоны).",
        )
    pend = tower_next_floor_pending(character)
    if pend is not None:
        lines.append(f"✅ <b>Ярус зачищен.</b> Поднимись на этаж <b>{pend}</b> кнопкой выше или «⬆️ Выше».")
    if long_floor_mod.is_long_floor_active(character):
        lines.append("Сценарий этажа — шаги кнопками (−1 ⚡ за бой).")
    else:
        lines.append("<b>Цель</b> — пошаговый бой (−1 ⚡).")
    return "\n".join(lines)


def format_floor_message_photo_caption(character: Character) -> str:
    """
    Короткий текст под фото этажа (лимит подписи Telegram ~1024 символа).
    Без длинного описания зоны — полный текст по-прежнему без фото или в логике без картинки.
    """
    long_floor_mod.ensure_long_floor_started(character)
    n = character.floor_number
    if int(n) == 3 and not long_floor_mod.is_long_floor_active(character):
        zone = floor_data.get_zone_for_floor(n)
        room = floor_data.epithet_for_floor(zone, n)
        city = floor_data.get_city_for_floor(n)
        pend = tower_next_floor_pending(character)
        bits = [
            f"{zone.emoji} <b>{html.escape(zone.name)}</b> · <b>3</b>/100",
            f"📍 <i>{html.escape(room)}</i>",
            f"{city.emoji} <b>{html.escape(city.name)}</b> — мирный хаб, рынок в городе",
            "Без боёв на карте · тайник и привал — с 4-го",
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
    lines.append(f"{zone.emoji} <b>{html.escape(zone.name)}</b> · <b>{n}</b>/100")
    lines.append(f"📍 <i>{html.escape(room)}</i>")
    if long_floor_mod.is_long_floor_active(character):
        b = long_floor_mod.format_long_floor_banner_html()
        lines.append(b if len(b) <= 120 else b[:117] + "…")
    if city:
        lines.append(f"{city.emoji} <b>{html.escape(city.name)}</b> — город")
    tags: list[str] = []
    if floor_data.has_quest_npc(n) and int(n) != 3:
        tags.append("📜 Квесты")
    if floor_data.has_trader(n):
        tags.append("🏛️ Рынок в городе" if int(n) == 3 else "🏪 Лавка — в городе")
    if floor_data.is_mini_boss_floor(n):
        tags.append("⚔️ Мини-босс")
    if floor_data.is_major_boss_floor(n):
        tags.append("👑 Босс")
    if tags:
        lines.append(" · ".join(tags))
    wn = wandering_npcs_mod.wandering_npc_for_floor(int(character.id), n)
    if wn:
        raw_wn = f"🎭 {wn['title']}: {wn['hint']}"
        lines.append(html.escape(raw_wn if len(raw_wn) <= 120 else raw_wn[:117] + "…"))
    if tutorial_battle_pending(character) and n == 1:
        lines.append("🎓 Учебный бой — внизу")
    sec = f"🔮 Тайник ~{int(floor_data.SECRET_ROOM_CHANCE * 100)}%"
    if n <= SECRET_GEAR_EARLY_MAX_FLOOR:
        sec += ", экип. возможна"
    else:
        sec += f", экип ~{int(SECRET_GEAR_DROP_CHANCE * 100)}%"
    lines.append(sec)
    if n in pets_mod.pet_gacha_floors_for_pet_switch():
        lines.append("🐾 Питомцы: город / пассив · один активен")
    hi = int(character.highest_floor_reached)
    lines.append(f"🧭 1–{hi} · ⬆️⬇️ · цели сбрасываются при входе")
    if n < 100 and not long_floor_mod.is_long_floor_active(character):
        lines.append("🗝️ Зачистка → кнопка этажа / ⬆️")
    if forest_beginnings_mod.is_forest_beginnings_zone(n) and int(n) != 3:
        lines.append("🌲 Лес 1–10: грибы / дух · 🏕️ привал")
    if rotten_swamps_mod.is_rotten_swamps_zone(n):
        lines.append("🌿 Болота: туман −5 HP · пиявки · туман целей · лагерь")
    pend = tower_next_floor_pending(character)
    if pend is not None:
        lines.append(f"✅ Подъём на <b>{pend}</b> — кнопка или ⬆️")
    if long_floor_mod.is_long_floor_active(character):
        lines.append("Сценарий: −1 ⚡ за бой")
    else:
        lines.append("<b>Цель</b> — бой (−1 ⚡)")
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
    Один бросок при первом «заходе» на этаж (visits == 0): 10% особое событие.
    Не срабатывает на длинном этаже-сценарии.
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
    if random.random() >= 0.10:
        await session.flush()
        return ""

    kind = random.choice(("star", "merchant", "trap", "bless"))
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
    else:
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
    if ensure_peaceful_city_hub_ascent(character):
        await session.flush()
    n = int(character.floor_number)
    row = await floor_progress_repo.ensure_floor_row(session, character.id, n)
    event_html = await maybe_roll_floor_entry_event(session, character, row)
    zone = floor_data.get_zone_for_floor(n)
    room = floor_data.epithet_for_floor(zone, n)
    ex = dict(row.extra or {})
    splash_needed = int(row.visits) == 0 and not ex.get("_floor_intro_anim_v0")
    full_body = format_floor_message(character) + event_html + text_suffix
    photo = location_image_for_floor(n) if game_images_enabled(character) else None
    if photo is None and game_images_enabled(character):
        photo = UI_PLACEHOLDER_IMAGE_URL
    body_for_ui = (
        _clamp_telegram_caption(format_floor_message_photo_caption(character) + event_html + text_suffix)
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
    )


@dataclass(slots=True)
class SecretSearchOutcome:
    """Результат обыска: либо короткий alert, либо HTML для сообщения."""

    alert: str | None
    body_html: str | None


async def travel_to_floor(
    session: AsyncSession,
    character: Character,
    target_floor: int,
    *,
    telegram_id: int | None = None,
    username: str | None = None,
    bot: Bot | None = None,
) -> tuple[bool, str | None]:
    """Перейти на этаж в пределах 1..highest_floor_reached; сброс слотов целей на этом этаже."""
    hi = int(character.highest_floor_reached)
    if target_floor < 1 or target_floor > hi:
        return False, "Этаж ещё не открыт или недоступен."
    old_floor = int(character.floor_number)
    if old_floor != int(target_floor):
        rotten_swamps_mod.on_travel_floor_change(character, old_floor, int(target_floor))
    if target_floor > old_floor:
        clear_tower_ascent_pending(character)
    if old_floor == 10 and target_floor == 11:
        mp = dict(character.meta_progress or {})
        mp.pop(forest_beginnings_mod.META_KEY, None)
        character.meta_progress = mp
    character.floor_number = target_floor
    row = await floor_progress_repo.ensure_floor_row(session, character.id, target_floor)
    ex = dict(row.extra or {})
    ex["slots_cleared"] = []
    row.extra = ex
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
    )


async def try_secret_search(
    session: AsyncSession,
    character: Character,
) -> SecretSearchOutcome:
    """
    Один бросок тайника на текущем «заходе» этажа (счётчик visits в floor_progress).
    """
    n = int(character.floor_number)
    if n == 3:
        return SecretSearchOutcome(
            alert="На третьем ярусе только город — тайников здесь нет.",
            body_html=None,
        )
    row = await floor_progress_repo.ensure_floor_row(session, character.id, n)
    visits = int(row.visits)
    extra = dict(row.extra or {})
    if int(extra.get("secret_attempt_visit", -1)) == visits:
        return SecretSearchOutcome(
            alert=(
                "Ты уже обыскал всё здесь после последнего боя. "
                "Победи ещё раз на этом этаже — и можно снова."
            ),
            body_html=None,
        )

    extra["secret_attempt_visit"] = visits
    row.extra = extra

    if random.random() >= floor_data.SECRET_ROOM_CHANCE:
        await session.flush()
        return SecretSearchOutcome(
            alert=None,
            body_html=(
                "🔍 <b>Ничего.</b>\n"
                "Трещина в камне оказалась бликом факела — "
                "ни сундука, ни прохода."
            ),
        )

    row.secret_rooms_found = int(row.secret_rooms_found) + 1
    gold_bonus = 8 + n * 2
    xp_bonus = 5 + n
    character_service.add_gold(character, gold_bonus)
    lv = await character_service.add_experience_async(session, character, xp_bonus, bot=None)
    title_service.refresh_unlocks(character)

    gear_html = ""
    gear_payload = try_roll_secret_gear_payload(n)
    if gear_payload is not None:
        free = await inventory_repo.first_free_bag_slot(session, character.id)
        if free is None:
            gear_html = (
                "\n⚠️ <b>Снаряжение в кисете есть</b>, но сумка полна — "
                "освободи ячейку и загляни в тайник снова после следующего боя."
            )
        else:
            await inventory_repo.add_bag_item(
                session,
                character.id,
                copy.deepcopy(gear_payload),
                bag_slot=free,
            )
            gname = html.escape(str(gear_payload.get("name", "Предмет")))
            gear_html = f"\n📦 <b>{gname}</b> — в сумку (ячейка {free})."

    await session.flush()
    body = (
        "✨ <b>Тайник!</b>\n"
        "За сдвижной плитой — кисет прошлого странника.\n"
        f"💰 +{gold_bonus} золота\n"
        f"📈 +{xp_bonus} опыта"
        f"{character_service.level_up_notice_html(character, lv)}"
        f"{gear_html}"
    )
    return SecretSearchOutcome(
        alert=None,
        body_html=body,
    )
