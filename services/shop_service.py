"""
Покупка товаров у торговца: золото → предмет в сумку; походный паёк вне боя.
"""

from __future__ import annotations

import copy
import html

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models.character import Character
from db.repository import inventory_repo
from game.combat import consumables as combat_consumables
from game.economy import shop as shop_data
from utils.ui import LINE_SEP


def format_shop_welcome_html(character: Character, *, from_city: bool) -> str:
    fln = int(character.floor_number)
    if from_city:
        place = "в городе"
    elif fln == 3:
        place = "на <b>3 этаже</b> (лавка нижнего яруса)"
    else:
        place = "у придорожного лотка"
    if from_city:
        where_ru = "ты открыл лавку <b>из города</b> (те же цены и товар, что у лотка на этом этаже)"
    else:
        where_ru = "ты у торговца <b>на боевом этаже</b> (не через экран города)"
    lines = [
        f"🏪 <b>Лавка торговца</b> {place}",
        f"<i>Ассортимент и наценка считаются по этажу героя: <b>{fln}</b>. Сейчас {where_ru}.</i>",
        "<i>«Всё лучшее с нижних колец башни… наличные только золотом.»</i>",
        LINE_SEP,
        f"💰 Золото: <b>{int(character.gold):,}</b>",
        LINE_SEP,
        "<b>Товар:</b>",
    ]
    fl = int(character.floor_number)
    for g in shop_data.shop_goods_for_floor(fl):
        p = shop_data.effective_good_price(g.price, fl)
        lines.append(
            f"{g.emoji} <b>{html.escape(g.name)}</b> — {p} 💰"
            f"{f' <i>(база {g.price})</i>' if p != g.price else ''}\n"
            f"<i>{html.escape(g.blurb)}</i>",
        )
    return "\n".join(lines)


async def try_buy_good(
    session: AsyncSession,
    character: Character,
    good_key: str,
    *,
    expected_floor: int,
) -> tuple[bool, str]:
    """
    Покупка в сумку. (False, plain) для alert или (True, HTML блок результата).
    """
    if character.floor_number != expected_floor:
        return False, "Ты не на этом этаже."

    if not shop_data.shop_available_on_floor(character.floor_number):
        return False, "Здесь нет торговца."

    good = shop_data.good_by_key(good_key, floor_number=int(character.floor_number))
    if good is None:
        return False, "Такого товара нет."

    price = shop_data.effective_good_price(good.price, character.floor_number)
    mp = dict(character.meta_progress or {})
    disc_left = int(mp.get("merchant_discount_charges") or 0)
    used_discount = False
    if disc_left > 0:
        price = max(1, int(round(price * 0.7)))
        used_discount = True
    if int(character.gold) < price:
        return False, f"Нужно {price} золота."

    free = await inventory_repo.first_free_bag_slot(session, character.id)
    if free is None:
        return False, "Не удалось найти свободный слот в сумке."

    character.gold = int(character.gold) - price
    if used_discount:
        mp["merchant_discount_charges"] = disc_left - 1
        character.meta_progress = mp
    payload = copy.deepcopy(good.item_data)
    await inventory_repo.add_bag_item(session, character.id, payload, bag_slot=free)
    await session.flush()

    name = html.escape(str(payload.get("name", good.name)))
    note = ""
    if used_discount:
        left = int((character.meta_progress or {}).get("merchant_discount_charges") or 0)
        note = f"\n<i>🏪 Скидка торговца: осталось ходов со скидкой — {left}.</i>"
    return True, f"−{price} 💰\nКуплено: <b>{name}</b> (ячейка сумки {free}).{note}"


async def try_use_bag_ration_by_id(
    session: AsyncSession,
    character: Character,
    item_id: int,
) -> tuple[bool, str]:
    """Съесть конкретный паёк из сумки (+стамина). Plain text для alert и HTML для сообщения."""
    item = await inventory_repo.get_item_for_character(session, character.id, item_id)
    if item is None or item.is_equipped:
        return False, "Предмет не найден."
    if item.bag_slot is None:
        return False, "Предмет не в сумке."
    data = combat_consumables.item_data_as_dict(item.item_data)
    if combat_consumables.normalize_combat_use_tag(data) != "stamina_flat":
        return False, "Это не походный паёк."

    mx = settings.MAX_STAMINA
    before = int(character.stamina)
    if before >= mx:
        return False, "Стамина уже полная."

    add = int(data.get("use_value", 2))
    character.stamina = min(mx, before + add)
    await inventory_repo.delete_inventory_item(session, item)
    await session.flush()
    gained = int(character.stamina) - before
    return True, f"🥖 Сыт! Стамина <b>+{gained}</b> ({character.stamina}/{mx})."


async def try_use_bag_bread_by_id(
    session: AsyncSession,
    character: Character,
    item_id: int,
) -> tuple[bool, str]:
    """Съесть хлеб из сумки (+HP). HTML для сообщения."""
    item = await inventory_repo.get_item_for_character(session, character.id, item_id)
    if item is None or item.is_equipped:
        return False, "Предмет не найден."
    if item.bag_slot is None:
        return False, "Предмет не в сумке."
    data = combat_consumables.item_data_as_dict(item.item_data)
    if combat_consumables.normalize_combat_use_tag(data) != "heal_hp_flat":
        return False, "Это не хлеб."

    mx = int(character.hp_max)
    cur = int(character.hp_current)
    if cur >= mx:
        return False, "HP уже полные."

    heal = max(1, int(data.get("use_value", 1)))
    new_hp = min(mx, cur + heal)
    character.hp_current = new_hp
    await inventory_repo.delete_inventory_item(session, item)
    await session.flush()
    gained = new_hp - cur
    name = html.escape(str(data.get("name", "Хлеб")))
    return True, f"🍞 {name}: <b>+{gained}</b> HP ({character.hp_current}/{mx})."


async def try_use_first_bag_ration(session: AsyncSession, character: Character) -> tuple[bool, str]:
    """Первый паёк в сумке (кнопка в лавке)."""
    items = await inventory_repo.list_bag_items(session, character.id)
    for it in sorted(items, key=lambda x: (x.bag_slot is None, x.bag_slot or 0)):
        d = combat_consumables.item_data_as_dict(it.item_data)
        if combat_consumables.normalize_combat_use_tag(d) == "stamina_flat":
            return await try_use_bag_ration_by_id(session, character, it.id)
    return False, "В сумке нет походного пайка."
