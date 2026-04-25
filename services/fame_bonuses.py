"""
Бонусы от Славы (fame) — пороги из плана: ежедневки, лавка, лут, титул/рамка, арена, квест 2500.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from services.fame_service import get_fame

# Пороги
F_DAILY_QUEST_SLOT4 = 25
F_NPC_SHOP_DISCOUNT = 75
F_WANDERER_ACCESS = 150
F_LOOT_RARE_BONUS = 300  # +5% к шансу предмета в сумку
F_UNIK_TITLE_FRAME = 600
F_ARENA_EXTRA_FIGHT = 1200
F_LEGENDARY_NPC = 2500

META_FAME_600_REWARD = "fame_600_rewards_v1"  # {"granted": bool}
META_F2500_QUEST = "fame_2500_legend_v1"  # {"done": bool}
META_WANDERER_STUB = "wanderer_stubs_v1"  # {"date": "...", "claimed_tips": bool} — заглушка

LOOT_FAME_BONUS_PCT = 0.05  # при F_LOOT_RARE_BONUS+


def daily_quest_slots_count(character: Character) -> int:
    """3 или 4 (четвёртое — при славе ≥ 25)."""
    return 4 if get_fame(character) >= F_DAILY_QUEST_SLOT4 else 3


def npc_merchant_price_multiplier(character: Character) -> float:
    """−10% у NPC-лавки при славе ≥ 75 (умножаем цену на 0.9)."""
    return 0.9 if get_fame(character) >= F_NPC_SHOP_DISCOUNT else 1.0


def wanderer_content_unlocked(character: Character) -> bool:
    """Доступ к ветке «Странник» (заглушка квестов)."""
    return get_fame(character) >= F_WANDERER_ACCESS


def loot_item_drop_fame_multiplier(character: Character) -> float:
    """
    Множитель к (базовой + удача) вероятности дропа: при славе ≥ 300 — +5% к шансу (×1.05).
    """
    if get_fame(character) < F_LOOT_RARE_BONUS:
        return 1.0
    return 1.0 + LOOT_FAME_BONUS_PCT


def fame_600_rewards_applied(meta: dict[str, Any] | None) -> bool:
    block = (meta or {}).get(META_FAME_600_REWARD)
    if not isinstance(block, dict):
        return False
    return bool(block.get("granted"))


def grant_fame_600_rewards_if_needed(character: Character) -> bool:
    """
    Выдать титул + рамку (мета) при первом достижении 600 славы. Возвращает True если что-то выдали.
    """
    if get_fame(character) < F_UNIK_TITLE_FRAME:
        return False
    meta = dict(character.meta_progress or {})
    block = dict(meta.get(META_FAME_600_REWARD) or {})
    if block.get("granted"):
        return False
    block["granted"] = True
    block["title"] = "Имя в летописях"
    block["frame"] = "gold_orbit"
    meta[META_FAME_600_REWARD] = block
    character.meta_progress = meta
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(character, "meta_progress")
    return True


def title_and_frame_600_display(character: Character) -> tuple[str, str] | None:
    """(title_ru, frame_id) для профиля или (None) если нет награды."""
    meta = character.meta_progress or {}
    block = meta.get(META_FAME_600_REWARD)
    if not isinstance(block, dict) or not block.get("granted"):
        return None
    return (str(block.get("title", "—")), str(block.get("frame", "")))


def arena_extra_match_unlocked(character: Character) -> bool:
    return get_fame(character) >= F_ARENA_EXTRA_FIGHT


def max_arena_matches_per_day(character: Character) -> int:
    # База = arena_service.ARENA_MATCHES_PER_DAY (10), не импортируем вверх (цикл импортов).
    n = 10
    if arena_extra_match_unlocked(character):
        n += 1
    return n


def legendary_2500_quest_done(character: Character) -> bool:
    meta = character.meta_progress or {}
    b = meta.get(META_F2500_QUEST)
    if not isinstance(b, dict):
        return False
    return bool(b.get("done"))


def can_show_legendary_2500_quest(character: Character) -> bool:
    return get_fame(character) >= F_LEGENDARY_NPC and not legendary_2500_quest_done(character)


async def complete_legendary_2500_quest(
    session: AsyncSession,
    character: Character,
) -> tuple[bool, str]:
    if not can_show_legendary_2500_quest(character):
        if get_fame(character) < F_LEGENDARY_NPC:
            return False, "Нужна слава 2500+."
        return False, "Награда уже получена."
    from services import character_service

    mark_legendary_2500_done(character)
    character_service.add_gold(character, 2000)
    await character_service.add_experience_async(session, character, 800, bot=None)
    return True, (
        "🌟 <b>Легендарный завет</b>\n"
        "Ты слышишь голос Башни. +2000 💰, +800 опыта. Этот путь больше не откроется."
    )


def mark_legendary_2500_done(character: Character) -> None:
    meta = dict(character.meta_progress or {})
    block = dict(meta.get(META_F2500_QUEST) or {})
    block["done"] = True
    meta[META_F2500_QUEST] = block
    character.meta_progress = meta
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(character, "meta_progress")


# ── Странник: мелкая награда 1/сутки (заглушка «особых миссий») ──

META_WANDERER_DAILY = "wanderer_tip_d_v1"


def _utc_day() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).date().isoformat()


def wanderer_daily_tip_available(character: Character) -> bool:
    if not wanderer_content_unlocked(character):
        return False
    b = (character.meta_progress or {}).get(META_WANDERER_DAILY)
    if not isinstance(b, dict):
        return True
    return str(b.get("d") or "") != _utc_day()


def claim_wanderer_daily_tip(character: Character) -> tuple[bool, str]:
    if not wanderer_content_unlocked(character):
        return False, "Нужна слава 150+."
    if not wanderer_daily_tip_available(character):
        return False, "Уже получал сегодня."
    from services import character_service

    gold = 35
    character_service.add_gold(character, gold)
    meta = dict(character.meta_progress or {})
    meta[META_WANDERER_DAILY] = {"d": _utc_day()}
    character.meta_progress = meta
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(character, "meta_progress")
    return True, f"Странник кивает: +{gold} 💰. <i>Цепь особых миссий скоро расширится.</i>"
