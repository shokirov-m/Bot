"""
Покупка товаров у торговца: золото → предмет в сумку; VIP-раздел за Telegram Stars.
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
from services import home_service
from services.fame_bonuses import npc_merchant_price_multiplier
from utils.ui import LINE_SEP


def _final_shop_gold_price(character: Character, base_price: int, fl: int) -> int:
    p = int(shop_data.effective_good_price(base_price, fl))
    m = float(npc_merchant_price_multiplier(character))
    if m < 0.999:
        p = max(1, int(round(p * m)))
    return p


def format_shop_welcome_html(character: Character, *, from_city: bool) -> str:
    fln = int(character.floor_number)
    if from_city:
        place = "в городе"
    elif fln == 3:
        place = "на <b>3 этаже</b> (лавка нижнего яруса)"
    else:
        place = "у придорожного лотка"
    if from_city:
        if fln == 3:
            where_ru = "ты у лотка на <b>рынке</b> деревни"
        else:
            where_ru = "ты открыл лавку <b>из города</b>"
    else:
        where_ru = "ты у торговца <b>на боевом этаже</b>"
    shop_title = "🏛️ <b>Рынок — лавка</b>" if (from_city and fln == 3) else "🏪 <b>Лавка торговца</b>"
    lines = [
        f"{shop_title} {place}",
        f"<i>Ассортимент и наценка по этажу героя: <b>{fln}</b>. Сейчас {where_ru}.</i>",
        "<i>«Всё лучшее с нижних колец башни… наличные только золотом.»</i>",
        LINE_SEP,
        f"💰 Золото: <b>{int(character.gold):,}</b>",
        LINE_SEP,
        "🛒 <b>Товар (обычный):</b>",
    ]
    fl = int(character.floor_number)
    fam_disc = float(npc_merchant_price_multiplier(character)) < 0.999
    for g in shop_data.shop_goods_for_floor(fl):
        p = _final_shop_gold_price(character, g.price, fl)
        p_no_scale = g.price
        p_floor = int(shop_data.effective_good_price(g.price, fl))
        eff_note = ""
        if p != p_no_scale and p == p_floor:
            eff_note = f" <i>(кат. {g.price} 💰)</i>"
        elif p != p_floor and not fam_disc:
            eff_note = f" <i>(надбавка этажа, база {g.price})</i>"
        lines.append(
            f"{g.emoji} <b>{html.escape(g.name)}</b> — {p} 💰{eff_note}\n"
            f"<i>{html.escape(g.blurb)}</i>",
        )
    if fam_disc:
        lines.append("<i>Известность: −10% к золотым ценам (слава 75+), суммируется с акцией бродячего торговца.</i>")
    return "\n".join(lines)


def format_vip_shop_html(character: Character) -> str:
    """VIP-раздел магазина: облики за Telegram Stars."""
    lines = [
        "⭐ <b>VIP-магазин</b>",
        "<i>Особые облики для профиля — покупаются за Telegram Stars.</i>",
        "<i>Звёзды — внутренняя валюта Telegram, купить можно прямо в приложении.</i>",
        LINE_SEP,
        "🖼️ <b>Облики:</b>",
    ]
    for g in shop_data.VIP_STAR_GOODS:
        pk = g.item_data.get("portrait_key", "")
        already = home_service.has_portrait_unlock(character, pk)
        status = " ✅ <i>уже куплен</i>" if already else f" — <b>{g.stars_price} ⭐</b>"
        lines.append(
            f"{g.emoji} <b>{html.escape(g.name)}</b>{status}\n"
            f"<i>{html.escape(g.blurb)}</i>"
        )
    lines.append(LINE_SEP)
    lines.append(
        "<i>💡 После оплаты облик сразу появится в "
        "<b>Дом → Гардероб</b>.</i>"
    )
    return "\n".join(lines)


async def try_buy_good(
    session: AsyncSession,
    character: Character,
    good_key: str,
    *,
    expected_floor: int,
    allow_remote_shop: bool = False,
) -> tuple[bool, str]:
    """Покупка за золото. (False, plain) или (True, HTML)."""
    if character.floor_number != expected_floor:
        return False, "Ты не на этом этаже."

    if not allow_remote_shop and not shop_data.shop_available_on_floor(character.floor_number):
        return False, "Здесь нет торговца."

    good = shop_data.good_by_key(good_key, floor_number=int(character.floor_number))
    if good is None:
        return False, "Такого товара нет."

    price = _final_shop_gold_price(character, good.price, int(character.floor_number))
    mp = dict(character.meta_progress or {})
    disc_left = int(mp.get("merchant_discount_charges") or 0)
    used_discount = False
    if disc_left > 0:
        price = max(1, int(round(price * 0.7)))
        used_discount = True
    if int(character.gold) < price:
        return False, f"Нужно {price} золота."

    if str(good.item_data.get("virtual_shop") or "") == "portrait_unlock":
        pk = str(good.item_data.get("portrait_key") or "").strip()
        if not pk:
            return False, "Ошибка описания товара."
        if home_service.has_portrait_unlock(character, pk):
            return False, "Этот облик уже открыт."
        character.gold = int(character.gold) - price
        if used_discount:
            mp["merchant_discount_charges"] = disc_left - 1
            character.meta_progress = mp
        home_service.unlock_portrait(character, pk)
        await session.flush()
        note = ""
        if used_discount:
            left = int((character.meta_progress or {}).get("merchant_discount_charges") or 0)
            note = f"\n<i>🏪 Скидка торговца: осталось ходов со скидкой — {left}.</i>"
        from utils.profile_portraits import portrait_title_ru
        disp = html.escape(portrait_title_ru(pk))
        return True, f"−{price} 💰\nОблик «{disp}» открыт в <b>Дом → Гардероб</b>.{note}"

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
        note = f"\n<i>🏪 Скидка: осталось ходов со скидкой — {left}.</i>"
    return True, f"−{price} 💰\nКуплено: <b>{name}</b> (ячейка сумки {free}).{note}"


def apply_stars_portrait_unlock(character: Character, portrait_key: str) -> tuple[bool, str]:
    """Разблокировать облик после успешной оплаты Stars (вызывается из successful_payment)."""
    pk = str(portrait_key).strip()
    if not pk:
        return False, "Некорректный ключ."
    if home_service.has_portrait_unlock(character, pk):
        return False, "Этот облик уже открыт."
    home_service.unlock_portrait(character, pk)
    from utils.profile_portraits import portrait_title_ru
    disp = portrait_title_ru(pk)
    return True, f"⭐ Облик «{html.escape(disp)}» открыт в <b>Дом → Гардероб</b>."


async def try_use_bag_ration_by_id(
    session: AsyncSession,
    character: Character,
    item_id: int,
) -> tuple[bool, str]:
    """Съесть конкретный паёк из сумки (+стамина)."""
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
    """Съесть хлеб из сумки (+HP)."""
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
