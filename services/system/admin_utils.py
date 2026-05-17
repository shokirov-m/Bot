"""
Утилиты для администратора: авто-пополнение ресурсов и выдача предметов.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models.character import Character
from db.repository import inventory_repo

ADMIN_MIN_GOLD = 10_000
ADMIN_MIN_RUNES = 10_000
ADMIN_CLAN_MIN_MATERIALS = 10_000
ADMIN_CLAN_MIN_GOLD = 10_000


async def ensure_admin_resources(session: AsyncSession, character: Character) -> None:
    """
    Автоматически пополняет ресурсы администратора до минимального порога.
    Вызывается при каждом открытии этажа / профиля.
    """
    changed = False

    if int(character.gold) < ADMIN_MIN_GOLD:
        character.gold = ADMIN_MIN_GOLD
        changed = True

    if int(character.rune_stones) < ADMIN_MIN_RUNES:
        character.rune_stones = ADMIN_MIN_RUNES
        changed = True

    if int(character.stamina) < settings.MAX_STAMINA:
        character.stamina = settings.MAX_STAMINA
        changed = True

    # Клановые ресурсы
    try:
        from db.repository import clan_repo as _cr
        m = await _cr.get_membership(session, int(character.id))
        if m is not None:
            clan = await _cr.get_clan(session, int(m.clan_id))
            if clan is not None:
                payload = dict(clan.payload or {})
                mats = dict(payload.get("materials") or {})
                needs_mat_update = False
                for mat in ("wood", "stone", "herbs"):
                    if int(mats.get(mat, 0)) < ADMIN_CLAN_MIN_MATERIALS:
                        mats[mat] = ADMIN_CLAN_MIN_MATERIALS
                        needs_mat_update = True
                if int(payload.get("treasury_gold", 0)) < ADMIN_CLAN_MIN_GOLD:
                    payload["treasury_gold"] = ADMIN_CLAN_MIN_GOLD
                    needs_mat_update = True
                if needs_mat_update:
                    payload["materials"] = mats
                    await _cr.update_payload(session, clan, payload)
    except Exception:
        pass

    if changed:
        await session.flush()


async def give_admin_all_items(session: AsyncSession, character: Character) -> int:
    """
    Выдаёт администратору по 5 штук каждого расходника из магазина.
    Возвращает количество добавленных позиций.
    """
    from game.economy.shop import SHOP_GOODS

    added = 0
    for good in SHOP_GOODS:
        idata = dict(good.item_data)
        if idata.get("virtual_shop"):
            continue
        idata["count"] = 5
        await inventory_repo.add_bag_item(session, int(character.id), idata)
        added += 1

    return added
