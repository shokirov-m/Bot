"""
Кузница: заточка надетой экипировки, разбор на материалы, варка расходника.
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
from game.items import durability as durability_mod
from game.items import enchant as enchant_rules
from game.items import equipment as equip_meta
from game.items import runes as rune_sys
from game.items import materials as mat_sys
from game.items.rarity_scaling import scaled_armor_defense_value, scaled_weapon_attack_value
from game.locations import forge as forge_loc
from services import character_service, home_service, title_service
from utils.ui import LINE_SEP, format_inventory_item_html, render_enchant_stars


def format_forge_intro_html(city_name: str, city_emoji: str) -> str:
    return (
        f"{city_emoji} <b>Кузница</b> — {html.escape(city_name)}\n"
        "Здесь кузнец усиливает <b>надетую экипировку</b> (оружие, броня, шлем и др.).\n"
        "После боёв снаряжение <b>теряет прочность</b>; при 0 предмет ломается — "
        "чините в разделе «Починка экипировки» за золото.\n"
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
    mult = enchant_rules.enchant_stat_multiplier(lv)
    atk_raw = data.get("attack", data.get("atk"))
    dfn_raw = data.get("defense", data.get("armor"))
    stat_s = ""
    if atk_raw is not None and int(atk_raw or 0) > 0:
        scaled = scaled_weapon_attack_value(int(atk_raw), data)
        eff = max(1, int(round(scaled * mult)))
        pct = lv * 5
        stat_s = f"\n⚔️ Атака: <b>{eff}</b> (база {scaled} +{pct}% от заточки)"
    elif dfn_raw is not None and int(dfn_raw or 0) > 0:
        scaled = scaled_armor_defense_value(int(dfn_raw), data)
        eff = max(0, int(round(scaled * mult)))
        pct = lv * 5
        stat_s = f"\n🛡️ Защита: <b>{eff}</b> (база {scaled} +{pct}% от заточки)"
    rarity = str(data.get("rarity") or "common").lower()
    if lv >= enchant_rules.MAX_ENCHANT:
        next_hint = f"\n✨ Максимальная заточка (+{enchant_rules.MAX_ENCHANT})."
    else:
        gold_cost = enchant_rules.enchant_attempt_cost_gold(lv)
        mat_cost = enchant_rules.enchant_material_cost(lv)
        mat_name = mat_sys.material_name(rarity)
        next_hint = (
            f"\n💰 Следующая: <b>{gold_cost}</b> золота + "
            f"<b>{mat_cost}</b> {html.escape(mat_name)}"
        )
    card = format_inventory_item_html(data)
    dur_line = ""
    if durability_mod.payload_supports_durability(data):
        dur_line = "\n" + durability_mod.format_durability_line_html(data)
    extra_runes = (
        "".join(_rune_lines_for_weapon_data(data))
        if str(data.get("kind")) == "weapon"
        else ""
    )
    return (
        f"<b>{label}</b>\n{card}{dur_line}{stat_s}\n"
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
    bag = await inventory_repo.list_bag_items(session, character.id)
    mat_lines: list[str] = []
    for rar in ("common", "uncommon", "rare", "epic", "legendary", "mythic"):
        cnt = mat_sys.total_materials_in_bag(bag, rar)
        if cnt > 0:
            mat_lines.append(f"{mat_sys.material_name(rar)}: <b>{cnt}</b>")
    mat_s = "\n".join(mat_lines) if mat_lines else "<i>нет материалов</i>"
    trophies = mat_sys.total_boss_trophies_in_bag(bag)
    trophy_line = f"\n🏆 Трофеев босса: <b>{trophies}</b>" if trophies > 0 else ""
    gold_line = (
        f"\n{LINE_SEP}\n"
        f"💰 У тебя: <b>{int(character.gold):,}</b> золота\n"
        f"⚗️ Рунные камни: <b>{stones}</b>\n"
        f"🔧 Материалы заточки:\n{mat_s}"
        f"{trophy_line}"
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
    rarity = str(data.get("rarity") or "common").lower()

    if cur >= enchant_rules.MAX_ENCHANT:
        return False, [f"Уже максимальная заточка (+{enchant_rules.MAX_ENCHANT})."]

    gold_cost = enchant_rules.enchant_attempt_cost_gold(cur)
    mat_cost = enchant_rules.enchant_material_cost(cur)
    mat_name = mat_sys.material_name(rarity)

    if int(character.gold) < gold_cost:
        return False, [f"Недостаточно золота. Нужно {gold_cost}, у тебя {int(character.gold):,}."]

    bag = await inventory_repo.list_bag_items(session, character.id)
    available_mats = mat_sys.total_materials_in_bag(bag, rarity)
    if available_mats < mat_cost:
        return False, [
            f"Нужно {mat_cost} {html.escape(mat_name)}, у тебя {available_mats}.\n"
            f"Получи материалы, разобрав ненужную экипировку в кузнице."
        ]

    if rune_ward:
        if int(character.rune_stones) < 1:
            return False, ["Нужен 1 рунный камень для рунной подстраховки."]

    slot_lab = html.escape(equip_meta.SLOT_LABEL_RU.get(equip_slot, equip_slot))
    character_service.add_gold(
        character,
        -gold_cost,
        spend_for=f"Кузница: заточка ({slot_lab})",
        spend_kind="forge",
    )
    character.enchant_attempts = int(character.enchant_attempts) + 1
    # списываем материалы
    await _consume_materials(session, character.id, rarity, mat_cost)
    if rune_ward:
        character.rune_stones = int(character.rune_stones) - 1
    title_service.refresh_unlocks(character)

    rolled = enchant_rules.roll_enchant_outcome(
        cur,
        success_chance_bonus=home_service.workbench_enchant_bonus(character),
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

    lines.append(f"−{gold_cost} 💰, −{mat_cost} {html.escape(mat_name)}.")
    if rune_ward:
        lines.append("−1 рунный камень.")
    return True, lines


async def _consume_materials(
    session: AsyncSession,
    character_id: int,
    rarity: str,
    count: int,
) -> None:
    """Списать ``count`` материалов нужной редкости из сумки (стаки)."""
    bag = await inventory_repo.list_bag_items(session, character_id)
    r = str(rarity or "common").lower()
    stacks = [
        it for it in bag
        if str((it.item_data or {}).get("kind")) == "material"
        and str((it.item_data or {}).get("rarity")) == r
    ]
    remaining = count
    for it in stacks:
        if remaining <= 0:
            break
        d = dict(it.item_data or {})
        cur = max(1, int(d.get("count", 1)))
        if cur <= remaining:
            remaining -= cur
            await inventory_repo.delete_inventory_item(session, it)
        else:
            d["count"] = cur - remaining
            it.item_data = d
            remaining = 0
    await session.flush()


async def add_materials_to_bag(
    session: AsyncSession,
    character_id: int,
    rarity: str,
    count: int,
) -> bool:
    """Добавить материалы в сумку — общий стак через inventory_repo.add_bag_item. False если места нет."""
    r = str(rarity or "common").lower()
    payload = mat_sys.material_payload(r, count)
    row = await inventory_repo.add_bag_item(session, character_id, payload)
    if row is None:
        return False
    await session.flush()
    return True


async def add_boss_trophy_to_bag(
    session: AsyncSession,
    character_id: int,
    count: int = 1,
) -> None:
    """Добавить трофеи босса в сумку — общий стак через inventory_repo.add_bag_item."""
    payload = mat_sys.boss_trophy_payload(count)
    await inventory_repo.add_bag_item(session, character_id, payload)
    await session.flush()


async def try_disassemble_bag_item(
    session: AsyncSession,
    character: Character,
    item_id: int,
) -> tuple[bool, str]:
    """
    Разобрать предмет из сумки → материалы заточки той же редкости.
    Расходники, руны и материалы разобрать нельзя.
    На ур.5 дома +1 доп. материал.
    """
    if not forge_loc.forge_available_on_floor(character.floor_number):
        return False, "Разбор — только в кузнице города."

    it = await inventory_repo.get_item_for_character(session, character.id, item_id)
    if it is None or it.is_equipped or it.bag_slot is None:
        return False, "Предмет не в сумке."

    data = dict(it.item_data or {})
    kind = str(data.get("kind") or "").lower()
    if kind in ("consumable", "rune", "material", "boss_trophy", "misc"):
        return False, "Этот тип предметов нельзя разобрать."

    rarity = str(data.get("rarity") or "common").lower()
    count = mat_sys.disassemble_material_count(rarity)
    # Бонус дома ур.5: +1 материал
    home_bonus = home_service.home_disassemble_bonus(character)
    count += home_bonus

    name = html.escape(str(data.get("name", "Предмет")))
    mat_name = html.escape(mat_sys.material_name(rarity))

    await inventory_repo.delete_inventory_item(session, it)
    await add_materials_to_bag(session, character.id, rarity, count)

    bonus_note = " <i>(+1 бонус дома)</i>" if home_bonus else ""
    return True, (
        f"🔨 <b>Разобрано:</b> {name}\n"
        f"+{count} {mat_name} → сумка.{bonus_note}"
    )


_RARITY_ORDER: tuple[str, ...] = ("common", "uncommon", "rare", "epic", "legendary", "mythic")


def _rarity_le(a: str, b: str) -> bool:
    a = (a or "").lower()
    b = (b or "").lower()
    if a not in _RARITY_ORDER or b not in _RARITY_ORDER:
        return False
    return _RARITY_ORDER.index(a) <= _RARITY_ORDER.index(b)


async def list_disassemblable_items(
    session: AsyncSession,
    character: Character,
    *,
    rarity_filter: str | None = None,
    kind_filter: str | None = None,
) -> list[tuple[int, str]]:
    """Список предметов для разбора с учётом фильтров. (item_id, label)."""
    bag = await inventory_repo.list_bag_items(session, character.id)
    skip_kinds = {"consumable", "rune", "material", "boss_trophy", "misc"}
    rows: list[tuple[int, str]] = []
    for it in sorted(bag, key=lambda x: x.bag_slot or 0):
        if it.is_equipped:
            continue
        d = dict(it.item_data or {})
        kind = str(d.get("kind") or "").lower()
        if kind in skip_kinds:
            continue
        rar = str(d.get("rarity") or "common").lower()
        if rarity_filter and rar != rarity_filter:
            continue
        if kind_filter and kind != kind_filter:
            continue
        nm = str(d.get("name", "Предмет"))
        rows.append((int(it.id), f"[{rar[:3]}] {nm}"))
    return rows


SWEEP_LIMIT = 32


async def try_sweep_disassemble(
    session: AsyncSession,
    character: Character,
    *,
    max_rarity: str = "uncommon",
    limit: int = SWEEP_LIMIT,
) -> tuple[bool, str]:
    """Свип-разбор: разобрать всё (≤max_rarity) пачкой, до limit предметов."""
    if not forge_loc.forge_available_on_floor(character.floor_number):
        return False, "Свип — только в кузнице города."
    bag = await inventory_repo.list_bag_items(session, character.id)
    skip_kinds = {"consumable", "rune", "material", "boss_trophy", "misc"}
    home_bonus = home_service.home_disassemble_bonus(character)
    totals: dict[str, int] = {}
    processed = 0
    for it in sorted(bag, key=lambda x: x.bag_slot or 0):
        if processed >= int(limit):
            break
        if it.is_equipped:
            continue
        d = dict(it.item_data or {})
        kind = str(d.get("kind") or "").lower()
        if kind in skip_kinds:
            continue
        rar = str(d.get("rarity") or "common").lower()
        if not _rarity_le(rar, max_rarity):
            continue
        count = mat_sys.disassemble_material_count(rar) + home_bonus
        await inventory_repo.delete_inventory_item(session, it)
        totals[rar] = totals.get(rar, 0) + count
        processed += 1
    if processed == 0:
        return False, f"Нет вещей до редкости «{max_rarity}» для свипа."
    for rar, cnt in totals.items():
        await add_materials_to_bag(session, character.id, rar, cnt)
    await session.flush()
    breakdown = ", ".join(f"+{cnt} {html.escape(mat_sys.material_name(r))}" for r, cnt in totals.items())
    return True, f"🧹 Свип-разбор: <b>{processed}</b> шт. → {breakdown}"


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
    f = max(1, min(135, int(floor_number)))
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

    character_service.add_gold(
        character,
        -cost,
        spend_for="Кузница: настой кузницы",
        spend_kind="forge",
    )
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

    character_service.add_gold(
        character,
        -cost,
        spend_for=f"Кузница: слияние руны {el} ранг {target_rank}",
        spend_kind="forge",
    )
    for it in found:
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


async def build_repair_message_html(session: AsyncSession, character: Character) -> str:
    """Экран починки: баланс, сумма «всё», список слотов с прочностью и ценой."""
    city = floor_data.get_city_for_floor(character.floor_number)
    cname = html.escape(city.name if city else "Город")
    cemoji = city.emoji if city else "🏙️"
    gold = int(character.gold)
    total_all = await durability_mod.total_repair_cost_equipped(session, character.id)
    lines: list[str] = [
        f"{cemoji} <b>Кузница</b> — {cname}",
        "",
        "🔨 <b>ПОЧИНКА</b>",
        "",
        f"💰 Ваш баланс: <b>{gold:,}</b> 🟡",
        f"💰 Стоимость починки всех предметов: <b>{total_all}</b> 💰",
        LINE_SEP,
        "",
        "<b>Экипированные предметы:</b>",
    ]
    equipped = await inventory_repo.list_equipped_items(session, character.id)
    by_slot = {str(it.equip_slot): it for it in equipped if it.equip_slot}
    for slot in equip_meta.EQUIP_ORDER:
        it = by_slot.get(slot)
        lab = equip_meta.SLOT_LABEL_RU.get(slot, slot)
        if it is None:
            lines.append("")
            lines.append(f"{html.escape(lab)}: <i>пусто</i>")
            continue
        data = dict(it.item_data or {})
        if not durability_mod.payload_supports_durability(data):
            continue
        durability_mod.ensure_gear_durability_defaults(data)
        r = str(data.get("rarity") or "common").lower()
        em = equip_meta.RARITY_EMOJI.get(r, "⚪")
        nm = html.escape(str(data.get("name", "?")))
        lines.append("")
        lines.append(f"⚙️ {em} <b>{html.escape(lab)}:</b> {nm}")
        lines.append(durability_mod.format_durability_line_html(data))
        cost = durability_mod.repair_gold_cost(data)
        lines.append(f"🔧 Починка: <b>{cost}</b> 💰")
    lines.append("")
    lines.append(
        "<i>Тариф: за каждые 2% недостающей прочности — "
        "5 / 10 / 20 / 40 / 100 💰 (обычная … легендарная).</i>",
    )
    return "\n".join(lines)


async def list_repair_slot_button_rows(
    session: AsyncSession,
    character_id: int,
) -> list[tuple[str, str]]:
    """Кнопки «починить слот»: только если есть износ и cost &gt; 0."""
    equipped = await inventory_repo.list_equipped_items(session, character_id)
    by_slot = {str(it.equip_slot): it for it in equipped if it.equip_slot}
    out: list[tuple[str, str]] = []
    for slot in equip_meta.EQUIP_ORDER:
        it = by_slot.get(slot)
        if it is None:
            continue
        data = dict(it.item_data or {})
        if not durability_mod.payload_supports_durability(data):
            continue
        durability_mod.ensure_gear_durability_defaults(data)
        c = durability_mod.repair_gold_cost(data)
        if c <= 0:
            continue
        short = str(data.get("name", "?"))
        if len(short) > 14:
            short = short[:11] + "…"
        sl = equip_meta.SLOT_LABEL_RU.get(slot, slot)
        if " " in sl:
            sl = sl.split(maxsplit=1)[1]
        lab = f"🔧 {sl[:10]} · {short} · {c}💰"
        out.append((slot, lab[:58]))
    return out


async def try_repair_equipped_slot(
    session: AsyncSession,
    character: Character,
    equip_slot: str,
) -> tuple[bool, list[str]]:
    if not forge_loc.forge_available_on_floor(character.floor_number):
        return False, ["Кузница только в городах-хабах башни."]
    if equip_slot not in equip_meta.EQUIP_ORDER:
        return False, ["Неизвестный слот экипировки."]
    item = await inventory_repo.get_equipped_in_slot(session, character.id, equip_slot)
    if item is None:
        lab = equip_meta.SLOT_LABEL_RU.get(equip_slot, equip_slot)
        return False, [f"Слот пуст: {html.escape(lab)}."]
    data = dict(item.item_data or {})
    if not durability_mod.payload_supports_durability(data):
        return False, ["Этот предмет не использует прочность."]
    durability_mod.ensure_gear_durability_defaults(data)
    cost = durability_mod.repair_gold_cost(data)
    if cost <= 0:
        return False, ["Прочность уже полная."]
    if int(character.gold) < cost:
        return False, [f"Нужно {cost} золота, у тебя {int(character.gold):,}."]

    slot_lab = html.escape(equip_meta.SLOT_LABEL_RU.get(equip_slot, equip_slot))
    character_service.add_gold(
        character,
        -cost,
        spend_for=f"Кузница: починка ({slot_lab})",
        spend_kind="forge",
    )
    dmax = int(data["durability_max"])
    data["durability"] = dmax
    item.item_data = data
    await session.flush()
    return True, [f"✅ Починено ({slot_lab}) за <b>{cost}</b> 💰."]


async def try_repair_all_equipped(session: AsyncSession, character: Character) -> tuple[bool, list[str]]:
    if not forge_loc.forge_available_on_floor(character.floor_number):
        return False, ["Кузница только в городах-хабах башни."]
    total = await durability_mod.total_repair_cost_equipped(session, character.id)
    if total <= 0:
        return False, ["Вся экипировка в полном порядке."]
    if int(character.gold) < total:
        return False, [f"Нужно {total} золота, у тебя {int(character.gold):,}."]

    character_service.add_gold(
        character,
        -total,
        spend_for="Кузница: починка всей экипировки",
        spend_kind="forge",
    )
    items = await inventory_repo.list_equipped_items(session, character.id)
    for it in items:
        data = dict(it.item_data or {})
        if not durability_mod.payload_supports_durability(data):
            continue
        durability_mod.ensure_gear_durability_defaults(data)
        dcur, dmax = durability_mod.durability_pair(data)
        if dcur < dmax:
            data["durability"] = int(data["durability_max"])
            it.item_data = data
    await session.flush()
    return True, [f"✅ Всё отремонтировано за <b>{total}</b> 💰."]
