"""
One-time migration: reset Tier-2 characters (level < 50) back to their Tier-1 parent class.
Runs once at bot startup; each character is marked so the notification is never sent twice.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_session_factory
from db.models.character import Character
from db.models.user import User
from game.archetypes import manager as arch_manager
import services.progression.character_service as character_service

if TYPE_CHECKING:
    from aiogram import Bot

_TIER2_KEYS = frozenset({
    "guardian", "berserker",
    "pyromancer", "cryomancer",
    "assassin", "ranger",
    "paladin", "prophet",
})

_TIER2_PARENT: dict[str, str] = {
    "guardian": "warrior",
    "berserker": "warrior",
    "pyromancer": "mage",
    "cryomancer": "mage",
    "assassin": "scout",
    "ranger": "scout",
    "paladin": "acolyte",
    "prophet": "acolyte",
}

_MIGRATION_FLAG = "tier2_reset_v1_notified"


@dataclass
class _ResetResult:
    telegram_id: int
    display_name: str
    old_class_name: str
    new_class_name: str


async def run_tier2_reset(bot: "Bot") -> None:
    """Find all Tier-2 characters with level < 50, reset them to Tier-1 parent and notify."""
    results: list[_ResetResult] = []

    async with get_session_factory()() as session:
        rows = await session.execute(
            select(Character, User)
            .join(User, User.id == Character.user_id)
            .where(Character.class_key.in_(list(_TIER2_KEYS)))
            .where(Character.level < 50)
        )
        pairs = rows.all()

        for char, user in pairs:
            mp = dict(char.meta_progress or {})
            if mp.get(_MIGRATION_FLAG):
                continue  # already notified

            old_class_key = str(char.class_key)
            parent_key = _TIER2_PARENT.get(old_class_key, "wanderer")

            old_arch = arch_manager.get_archetype(old_class_key)
            new_arch = arch_manager.get_archetype(parent_key)
            if not new_arch:
                logger.warning("tier2_migration: unknown parent '{}' for '{}'", parent_key, old_class_key)
                continue

            old_name = old_arch.name_ru if old_arch else old_class_key
            new_name = new_arch.name_ru

            from game.archetypes.grimoires import migrate_tree_to_grimoires

            migrate_tree_to_grimoires(char)
            char.class_key = parent_key
            mp = dict(char.meta_progress or {})
            mp["equipped_skill_keys"] = []
            mp.pop("unlocked_nodes", None)
            mp.pop("unspent_sp", None)
            learned = [k for k in (mp.get("learned_grimoires_v1") or []) if not str(k).startswith("supreme_")]
            mp["learned_grimoires_v1"] = learned
            mp[_MIGRATION_FLAG] = True
            char.meta_progress = mp

            # recalculate HP/MP
            char.hp_max = character_service._compute_hp_max(
                char.stat_vitality, char.stat_strength, new_arch
            )
            char.mp_max = character_service._compute_mp_max(char.stat_intelligence, new_arch)
            char.hp_current = char.hp_max
            char.mp_current = char.mp_max

            results.append(_ResetResult(
                telegram_id=int(user.telegram_id),
                display_name=str(char.display_name),
                old_class_name=old_name,
                new_class_name=new_name,
            ))

        if results:
            await session.commit()
            logger.info("tier2_migration: reset {} character(s) to Tier-1.", len(results))
        else:
            logger.info("tier2_migration: no characters to reset.")

    # Send notifications outside the DB session
    for r in results:
        try:
            await bot.send_message(
                chat_id=r.telegram_id,
                text=(
                    f"⚔️ <b>Смена специализации</b>\n\n"
                    f"Привет, <b>{r.display_name}</b>!\n\n"
                    f"Мы переработали специализации 2-го Пути и теперь они открываются с <b>50 уровня</b> (ранее 30). "
                    f"Их бонусы значительно усилены — это стоит того!\n\n"
                    f"Твоя специализация <b>{r.old_class_name}</b> была сброшена обратно до <b>{r.new_class_name}</b>.\n"
                    f"Все очки навыков возвращены.\n\n"
                    f"Когда достигнешь <b>50 уровня</b>, зайди в профиль → «Специализация» и выбери новый Путь снова. "
                    f"Тебя ждут куда более мощные силы! 🔥"
                ),
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning("tier2_migration: cannot notify {} — {}", r.telegram_id, exc)
