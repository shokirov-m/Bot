"""
Кузница: экран заточки надетого оружия, списание золота, учёт попыток, варка расходника.
"""

from __future__ import annotations

import copy
import html
import random
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.models.inventory import InventoryItem
from db.repository import inventory_repo
from game.floors import floor_data
from game.items import enchant as enchant_rules
from game.items import equipment as equip_meta
from game.items import runes as rune_sys
from game.locations import forge as forge_loc
from services import profession_service, title_service
from utils.ui import LINE_SEP, format_inventory_item_html, render_enchant_stars


def format_forge_intro_html(city_name: str, city_emoji: str) -> str:
    return (
        f"{city_emoji} <b>Кузница</b> — {html.escape(city_name)}\n"
        "Здесь кузнец усиливает <b>надетую экипировку</b> (оружие, броня, шлем и др.).\n"
        "Провал может оставить уровень как есть или снизить заточку на 1.\n"
        "⚗️ <b>Рунный камень</b> можно вложить в попытку — "
        "катастрофа не снизит заточку (останется провал без −1).\n"
    ) + LINE_SEP


def _rune_lines_for_weapon_data(data: dict[str, Any]) -> list[str]:
    rune_sys.ensure_rune_socket_list(data)
    sockets = data.get("rune_sockets") or []
    slot_n = rune_sys.max_rune_slots(str(data.get("rarity", "common")))
    rune_lines: list[str] = []
    if slot_n <= 0:
        rune_lines.append("\n💎 <b>Руны:</b> у обычного оружия нет гнёзд (нужна редкость выше).")
    else:
        parts = []
        for cell in sockets:
            if isinstance(cell, dict) and cell.get("element"):
                try:
                    rd = rune_sys.RuneData.from_dict(cell)
                    parts.append(rd.display_name)
                except (ValueError, TypeError, KeyError):
                    parts.append("?")
            else:
                parts.append("∅")
        rune_lines.append(
            f"\n💎 <b>Руны ({slot_n} гнезда):</b> " + " · ".join(html.escape(p) for p in parts),
        )
    return rune_lines


def format_equipped_slot_block_html(equip_slot: str, item: InventoryItem | None) -> str:
    label = equip_meta.SLOT_LABEL_RU.get(equip_slot, equip_slot)
    if item is None:
        return f"{label}: <i>пусто</i>"
    data = item.item_data or {}
    lv = enchant_rules.current_enchant_level(data)
    atk = data.get("attack", data.get("atk"))
    dfn = data.get("defense", data.get("armor"))
    stat_s = ""
    if atk is not None and int(atk or 0) > 0:
        eff = int(atk) + lv
        stat_s = f"\n⚔️ Атака в бою: <b>{eff}</b> (база {int(atk)} +{lv} от заточки)"
    elif dfn is not None and int(dfn or 0) > 0:
        eff = int(dfn) + lv
        stat_s = f"\n🛡️ Защита в бою: <b>{eff}</b> (база {int(dfn)} +{lv} от заточки)"
    cost = enchant_rules.enchant_attempt_cost_gold(lv)
    if lv >= enchant_rules.MAX_ENCHANT:
        next_hint = "\n✨ Заточка на максимуме (+15)."
    else:
        next_hint = f"\n💰 Следующая попытка: <b>{cost}</b> золота."
    card = format_inventory_item_html(data)
    extra_runes = (
        "".join(_rune_lines_for_weapon_data(data))
        if str(data.get("kind")) == "weapon"
        else ""
    )
    return (
        f"<b>{label}</b>\n{card}{stat_s}\n"
        f"✨ Сейчас: {html.escape(render_enchant_stars(lv))}{next_hint}"
        f"{extra_runes}"
    )


async def build_forge_message_html(session: AsyncSession, character: Character) -> str:
    city = floor_data.get_city_for_floor(character.floor_number)
    name = city.name if city else "Город"
    emoji = city.emoji if city else "🏙️"
    intro = format_forge_intro_html(name, emoji)
    equipped = await inventory_repo.list_equipped_items(session, character.id)
    by_slot = {str(it.equip_slot): it for it in equipped if it.equip_slot}
    blocks: list[str] = []
    for slot in equip_meta.EQUIP_ORDER:
        it = by_slot.get(slot)
        blocks.append(format_equipped_slot_block_html(slot, it))
    block = "\n\n".join(blocks)
    stones = int(character.rune_stones)
    gold_line = (
        f"\n{LINE_SEP}\n"
        f"💰 У тебя: <b>{int(character.gold):,}</b> золота\n"
        f"⚗️ Рунные камни: <b>{stones}</b>"
    )
    return f"{intro}\n\n{block}{gold_line}"


async def list_enchant_slot_button_rows(
    session: AsyncSession,
    character_id: int,
) -> list[tuple[str, str]]:
    """(equip_slot, короткая подпись для кнопки)."""
    rows: list[tuple[str, str]] = []
    equipped = await inventory_repo.list_equipped_items(session, character_id)
    by_slot = {str(it.equip_slot): it for it in equipped if it.equip_slot}
    for slot in equip_meta.EQUIP_ORDER:
        it = by_slot.get(slot)
        if it is None:
            continue
        data = it.item_data or {}
        lv = enchant_rules.current_enchant_level(data)
        short_name = str(data.get("name", "?"))
        if len(short_name) > 14:
            short_name = short_name[:11] + "…"
        label = f"{equip_meta.SLOT_LABEL_RU.get(slot, slot)} · {short_name} +{lv}"
        rows.append((slot, label[:44]))
    return rows


async def try_enchant_equipped_in_slot(
    session: AsyncSession,
    character: Character,
    equip_slot: str,
    *,
    rune_ward: bool = False,
) -> tuple[bool, list[str]]:
    """
    Одна попытка заточки надетого предмета в слоте.
    rune_ward: списать 1 рунный камень; исход downgrade заменяется на fail.
    """
    if not forge_loc.forge_available_on_floor(character.floor_number):
        return False, ["Кузница только в городах-хабах башни."]

    if equip_slot not in equip_meta.EQUIP_ORDER:
        return False, ["Неизвестный слот экипировки."]

    item = await inventory_repo.get_equipped_in_slot(session, character.id, equip_slot)
    if item is None:
        lab = equip_meta.SLOT_LABEL_RU.get(equip_slot, equip_slot)
        return False, [f"Слот пуст: {lab}. Надень предмет в /inv."]

    data = dict(item.item_data or {})
    cur = enchant_rules.current_enchant_level(data)

    if cur >= enchant_rules.MAX_ENCHANT:
        return False, [f"Уже максимальная заточка (+{enchant_rules.MAX_ENCHANT})."]

    cost = enchant_rules.enchant_attempt_cost_gold(cur)
    if int(character.gold) < cost:
        return False, [f"Недостаточно золота. Нужно {cost}, у тебя {int(character.gold):,}."]

    if rune_ward:
        if int(character.rune_stones) < 1:
            return False, ["Нужен 1 рунный камень для рунной подстраховки."]

    character.gold = int(character.gold) - cost
    character.enchant_attempts = int(character.enchant_attempts) + 1
    if rune_ward:
        character.rune_stones = int(character.rune_stones) - 1
    title_service.refresh_unlocks(character)
    profession_service.refresh_unlocks(character)

    rolled = enchant_rules.roll_enchant_outcome(
        cur,
        success_chance_bonus=profession_service.enchant_success_bonus_active(character),
    )
    outcome = rolled
    ward_absorbed = False
    if rune_ward and rolled == "downgrade":
        outcome = "fail"
        ward_absorbed = True

    new_data, _ = enchant_rules.apply_enchant_change(data, outcome)
    item.item_data = new_data

    slot_lab = html.escape(equip_meta.SLOT_LABEL_RU.get(equip_slot, equip_slot))
    lines: list[str] = []
    if outcome == "success":
        lines.append(
            f"✨ <b>Успех!</b> ({slot_lab}) "
            f"{render_enchant_stars(cur)} → {render_enchant_stars(cur + 1)}",
        )
    elif outcome == "downgrade":
        lines.append(
            f"💔 <b>Катастрофа!</b> ({slot_lab}) "
            f"{render_enchant_stars(cur)} → {render_enchant_stars(max(0, cur - 1))}",
        )
    else:
        lines.append(f"😬 <b>Провал.</b> ({slot_lab}) Заточка осталась {render_enchant_stars(cur)}.")

    if ward_absorbed:
        lines.append("⚗️ <b>Руна сдержала поломку</b> — уровень заточки не упал.")

    lines.append(f"−{cost} золота.")
    if rune_ward:
        lines.append("−1 рунный камень.")
    return True, lines


async def try_enchant_equipped_weapon(
    session: AsyncSession,
    character: Character,
    *,
    rune_ward: bool = False,
) -> tuple[bool, list[str]]:
    """Совместимость: заточка слота оружия."""
    return await try_enchant_equipped_in_slot(
        session,
        character,
        "weapon",
        rune_ward=rune_ward,
    )


def brew_elixir_cost_gold(floor_number: int) -> int:
    f = max(1, min(100, int(floor_number)))
    return 20 + min(f, 60) // 3


async def try_brew_city_elixir(
    session: AsyncSession,
    character: Character,
) -> tuple[bool, list[str]]:
    """Сварить слабый эликсир HP за золото (только в городе с кузницей)."""
    if not forge_loc.forge_available_on_floor(character.floor_number):
        return False, ["Варка доступна только в кузнице города-хаба башни."]

    cost = brew_elixir_cost_gold(character.floor_number)
    if int(character.gold) < cost:
        return False, [f"Нужно {cost} золота, у тебя {int(character.gold):,}."]

    free = await inventory_repo.first_free_bag_slot(session, character.id)
    if free is None:
        return False, ["В сумке нет свободной ячейки."]

    character.gold = int(character.gold) - cost
    payload = {
        "name": "Настой кузницы",
        "kind": "consumable",
        "rarity": "common",
        "summary": "Сварен у наковальни: в бою +25% к макс. HP.",
        "use_tag": "heal_hp_pct",
        "use_value": 25,
    }
    await inventory_repo.add_bag_item(session, character.id, copy.deepcopy(payload), bag_slot=free)
    await session.flush()
    return True, [
        f"🧪 Готово: <b>{html.escape(payload['name'])}</b> → сумка, ячейка {free}.",
        f"−{cost} 💰",
    ]


async def socket_rune_into_equipped_weapon(
    session: AsyncSession,
    character: Character,
    *,
    rune_bag_item_id: int,
) -> tuple[bool, str]:
    """
    Вставить руну из сумки в первое свободное гнездо <b>надетого</b> оружия.
    """
    if not forge_loc.forge_available_on_floor(character.floor_number):
        return False, "Руны — только в кузнице города."

    weapon = await inventory_repo.get_equipped_weapon(session, character.id)
    if weapon is None:
        return False, "Нет надетого оружия."

    rune_row = await inventory_repo.get_item_for_character(
        session,
        character.id,
        rune_bag_item_id,
    )
    if rune_row is None or rune_row.bag_slot is None:
        return False, "Руны нет в сумке."

    rd = rune_sys.extract_rune_from_item(dict(rune_row.item_data or {}))
    if rd is None:
        return False, "Это не руна."

    wdata = dict(weapon.item_data or {})
    if str(wdata.get("kind")) != "weapon":
        return False, "В слоте не оружие."

    rune_sys.ensure_rune_socket_list(wdata)
    sockets: list[Any] = list(wdata["rune_sockets"])
    try:
        free_i = sockets.index(None)
    except ValueError:
        return False, "Все гнёзда заняты."

    sockets[free_i] = rd.as_dict()
    wdata["rune_sockets"] = sockets
    weapon.item_data = wdata
    await inventory_repo.delete_inventory_item(session, rune_row)
    character.runes_socketed = int(character.runes_socketed) + 1
    title_service.refresh_unlocks(character)
    await session.flush()
    return True, f"💎 Руна вставлена: {html.escape(rd.display_name)} (гнездо {free_i + 1})."


async def remove_rune_from_equipped_weapon(
    session: AsyncSession,
    character: Character,
    *,
    socket_index: int,
) -> tuple[bool, str, dict | None]:
    """
    Извлечь руну из гнезда. 50% вернуть в сумку, 50% уничтожить.
    """
    if not forge_loc.forge_available_on_floor(character.floor_number):
        return False, "Только в кузнице города.", None

    weapon = await inventory_repo.get_equipped_weapon(session, character.id)
    if weapon is None:
        return False, "Нет оружия.", None

    wdata = dict(weapon.item_data or {})
    rune_sys.ensure_rune_socket_list(wdata)
    sockets: list[Any] = list(wdata.get("rune_sockets") or [])
    if socket_index < 0 or socket_index >= len(sockets):
        return False, "Нет такого гнезда.", None
    cell = sockets[socket_index]
    if not isinstance(cell, dict) or not cell.get("element"):
        return False, "Гнездо пустое.", None

    try:
        rd = rune_sys.RuneData.from_dict(cell)
    except (ValueError, TypeError, KeyError):
        return False, "Битые данные руны.", None

    sockets[socket_index] = None
    wdata["rune_sockets"] = sockets
    weapon.item_data = wdata

    saved: dict | None = None
    if random.random() < 0.5:
        free = await inventory_repo.first_free_bag_slot(session, character.id)
        if free is None:
            return False, "Сумка полна — некуда вернуть руну.", None
        payload = rune_sys.rune_item_payload(rd)
        await inventory_repo.add_bag_item(session, character.id, copy.deepcopy(payload), bag_slot=free)
        saved = payload
        msg = f"✅ Руна извлечена: {html.escape(rd.display_name)} → сумка."
    else:
        msg = f"💔 Руна {html.escape(rd.display_name)} рассыпалась при извлечении…"

    await session.flush()
    return True, msg, saved


async def craft_rune_merge(
    session: AsyncSession,
    character: Character,
    *,
    element: str,
    target_rank: int,
) -> tuple[bool, str]:
    """
    Скрафтить руну ранга N из двух рун ранга N−1 той же стихии. Стоимость 500 * N золота.
    """
    if not forge_loc.forge_available_on_floor(character.floor_number):
        return False, "Только в кузнице города."
    el = str(element).lower().strip()
    if el not in rune_sys.ELEMENTS:
        return False, "Неизвестная стихия."
    if target_rank < 2 or target_rank > 5:
        return False, "Целевой ранг 2–5."
    prev = target_rank - 1
    cost = 500 * target_rank
    if int(character.gold) < cost:
        return False, f"Нужно {cost} золота."

    bag = await inventory_repo.list_bag_items(session, character.id)
    found: list[Any] = []
    for it in bag:
        rd = rune_sys.extract_rune_from_item(dict(it.item_data or {}))
        if rd is None:
            continue
        if rd.element == el and rd.rank == prev:
            found.append(it)
        if len(found) >= 2:
            break

    if len(found) < 2:
        return False, f"Нужны две руны «{el}» ранга {prev} в сумке."

    free = await inventory_repo.first_free_bag_slot(session, character.id)
    if free is None:
        return False, "Нет места в сумке."

    character.gold = int(character.gold) - cost
    for it in found[:2]:
        await inventory_repo.delete_inventory_item(session, it)

    new_rune = rune_sys.RuneData(element=el, rank=target_rank)
    payload = rune_sys.rune_item_payload(new_rune)
    await inventory_repo.add_bag_item(session, character.id, copy.deepcopy(payload), bag_slot=free)
    await session.flush()
    return True, (
        f"⚗️ Получено: <b>{html.escape(new_rune.display_name)}</b> (ячея {free}).\n"
        f"−{cost} 💰, −2 руны ранга {prev}."
    )


async def craft_rune_auto_pair_rank1(
    session: AsyncSession,
    character: Character,
) -> tuple[bool, str]:
    """Авто: две руны ранга I одной стихии → ранг II (стоимость как у craft_rune_merge)."""
    bag = await inventory_repo.list_bag_items(session, character.id)
    by_el: dict[str, list[Any]] = {}
    for it in bag:
        rd = rune_sys.extract_rune_from_item(dict(it.item_data or {}))
        if rd is not None and rd.rank == 1:
            by_el.setdefault(rd.element, []).append(it)
    for el, lst in by_el.items():
        if len(lst) >= 2:
            return await craft_rune_merge(session, character, element=el, target_rank=2)
    return False, "Нет двух рун ранга I одной стихии в сумке."
