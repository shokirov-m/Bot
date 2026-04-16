"""Валидация имени, применение промокода."""

from __future__ import annotations

import copy
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.repository import inventory_repo, promo_offer_repo, promo_repo
from game.characters.global_passives import refresh_global_passives
from game.promos import bag_payloads_for_code, reward_for_code
from services import character_service

if TYPE_CHECKING:
    from db.models.character import Character
    from db.models.user import User

_NAME_RE = re.compile(r"^[\w\-\s\u0400-\u04FF·]{2,32}$", re.UNICODE)


def normalize_display_name(raw: str) -> str:
    return " ".join(raw.strip().split())


def validate_display_name(raw: str) -> tuple[str | None, str | None]:
    """
    (имя, ключ_ошибки_i18n) — при успехе (name, None).
    """
    name = normalize_display_name(raw)
    if len(name) < 2:
        return None, "settings_name_short"
    if len(name) > 32:
        return None, "settings_name_long"
    if "<" in name or ">" in name or "&" in name:
        return None, "settings_name_chars"
    if not _NAME_RE.match(name):
        return None, "settings_name_chars"
    return name, None


def try_paid_rename(character: Character, raw: str) -> tuple[bool, str | None]:
    """
    Смена отображаемого имени за золото.
    Возвращает (успех, ключ ошибки i18n или None).
    """
    name, err_key = validate_display_name(raw)
    if err_key is not None or name is None:
        return False, err_key
    cost = int(settings.DISPLAY_NAME_CHANGE_GOLD)
    if not character_service.try_spend_gold(character, cost):
        return False, "settings_rename_no_gold"
    character.display_name = name[:64]
    return True, None


async def _apply_promo_rewards_async(
    session: AsyncSession,
    character: Character,
    g: int,
    x: int,
    rs: int,
    *,
    bot: object | None,
) -> int:
    levels_up = 0
    if g:
        character_service.add_gold(character, g)
    if x:
        levels_up = await character_service.add_experience_async(session, character, x, bot=bot)
    if rs:
        character.rune_stones = int(character.rune_stones) + rs
    refresh_global_passives(character)
    return levels_up


async def _free_bag_slots_count(session: AsyncSession, character_id: int) -> int:
    """Грубая оценка «запаса» для промо: при отсутствии лимита сумки возвращаем большое число."""
    items = await inventory_repo.list_bag_items(session, character_id)
    used = len({i.bag_slot for i in items if i.bag_slot is not None})
    return max(0, 1_000_000 - used)


async def _grant_promo_bag_items(
    session: AsyncSession,
    character_id: int,
    payloads: tuple[dict[str, Any], ...],
) -> list[str]:
    """Добавить вещи в сумку; место уже проверено. Имена — для текста игроку."""
    names: list[str] = []
    for raw in payloads:
        data = copy.deepcopy(raw)
        slot = await inventory_repo.first_free_bag_slot(session, character_id)
        if slot is None:
            break
        await inventory_repo.add_bag_item(session, character_id, data, bag_slot=slot)
        names.append(str(data.get("name", "?")))
    return names


async def redeem_promo(
    session: AsyncSession,
    *,
    user: User,
    character: Character,
    raw_code: str,
    bot: object | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """
    Активировать промокод.
    Сначала ищется запись в БД (админка), иначе — статический список game/promos.py.
    Возвращает (успех, ключ i18n, словарь для format: gold/xp/rune/levels, опционально item_names).
    """
    code = raw_code.strip().upper()
    if len(code) < 3 or len(code) > 40:
        return False, "settings_promo_bad_format", {}

    if await promo_repo.has_redeemed(session, int(user.id), code):
        return False, "settings_promo_used", {}

    offer = await promo_offer_repo.get_by_code(session, code)
    if offer is not None:
        now = datetime.now(UTC)
        if not offer.is_active:
            return False, "settings_promo_disabled", {}
        if now < offer.valid_from:
            return False, "settings_promo_not_started", {}
        if offer.valid_until is not None and now > offer.valid_until:
            return False, "settings_promo_expired", {}

        ok_inc = await promo_offer_repo.try_take_one_use(session, offer.id)
        if not ok_inc:
            return False, "settings_promo_exhausted", {}

        await promo_repo.record_redemption(session, int(user.id), code)
        g, x, rs = int(offer.gold), int(offer.xp), int(offer.rune_stones)
        levels_up = await _apply_promo_rewards_async(session, character, g, x, rs, bot=bot)
        await session.flush()
        return True, "settings_promo_ok", {"gold": g, "xp": x, "rune": rs, "levels": levels_up}

    reward = reward_for_code(code)
    if reward is None:
        return False, "settings_promo_unknown", {}

    bag_payloads = bag_payloads_for_code(code)
    need = len(bag_payloads) if bag_payloads else 0
    if need and await _free_bag_slots_count(session, int(character.id)) < need:
        return False, "settings_promo_bag_full", {}

    await promo_repo.record_redemption(session, int(user.id), code)
    g, x, rs = int(reward.gold), int(reward.xp), int(reward.rune_stones)
    levels_up = await _apply_promo_rewards_async(session, character, g, x, rs, bot=bot)
    out: dict[str, Any] = {"gold": g, "xp": x, "rune": rs, "levels": levels_up}
    if bag_payloads:
        names = await _grant_promo_bag_items(session, int(character.id), bag_payloads)
        out["item_names"] = ", ".join(names)
    await session.flush()
    return True, "settings_promo_ok", out
