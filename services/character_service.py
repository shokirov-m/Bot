"""
Создание персонажа после выбора класса: статы, HP/MP, стартовый этаж 1.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models.character import Character
from db.models.enchant import EnchantLog
from db.models.floor_progress import FloorProgress
from db.models.inventory import InventoryItem
from db.models.quest import QuestProgress
from db.models.user import User
from db.repository import character_repo, inventory_repo
from game.characters.classes import ClassDefinition, get_class_or_none
from game.characters.progression import experience_needed_for_next_level
from game.items.equipment import starter_bread_payload, starter_weapon_payload
from utils.profile_portraits import META_PORTRAIT_KEY


def _compute_hp_max(vitality: int, strength: int, cls: ClassDefinition) -> int:
    """Базовый расчёт HP с учётом ВЫН/СИЛ и пассива класса."""
    base = 40 + vitality * 6 + strength * 2
    return max(1, int(base * cls.hp_multiplier))


def _compute_mp_max(intelligence: int, cls: ClassDefinition) -> int:
    """Базовый расчёт MP с учётом ИНТ и пассива класса."""
    base = 15 + intelligence * 5
    return max(0, int(base * cls.mp_multiplier))


async def create_character_for_user(
    session: AsyncSession,
    *,
    user: User,
    display_name: str,
    class_key: str,
    portrait_key: str | None = None,
) -> Character:
    """
    Создать персонажа для пользователя. Вызывать только если персонажа ещё нет.
    """
    cls = get_class_or_none(class_key)
    if cls is None:
        raise ValueError(f"Неизвестный класс: {class_key}")

    name = (display_name or "Странник")[:64]
    hp_max = _compute_hp_max(cls.vitality, cls.strength, cls)
    mp_max = _compute_mp_max(cls.intelligence, cls)

    now = datetime.now(UTC)
    meta: dict[str, Any] = {"tutorial_battle": "pending"}
    pk = (portrait_key or "").strip()
    if pk:
        meta[META_PORTRAIT_KEY] = pk[:48]
    char = Character(
        user_id=user.id,
        display_name=name,
        class_key=cls.key,
        stat_strength=cls.strength,
        stat_dexterity=cls.dexterity,
        stat_intelligence=cls.intelligence,
        stat_vitality=cls.vitality,
        stat_luck=cls.luck,
        hp_current=hp_max,
        hp_max=hp_max,
        mp_current=mp_max,
        mp_max=mp_max,
        stamina=settings.MAX_STAMINA,
        last_stamina_regen_at=now,
        floor_number=1,
        highest_floor_reached=1,
        class_tier=0,
        subclass_key=None,
        level=1,
        experience=0,
        gold=0,
        rune_stones=0,
        active_title=None,
        element=cls.default_element,
        unspent_stat_points=0,
        meta_progress=meta,
    )
    session.add(char)
    await session.flush()
    char.game_id = await character_repo.allocate_next_game_id(session)
    await session.flush()
    await inventory_repo.add_starter_equipped_weapon(
        session,
        char.id,
        item_data=starter_weapon_payload(cls.key),
    )
    for slot in (0, 1, 2):
        await inventory_repo.add_bag_item(
            session,
            char.id,
            copy.deepcopy(starter_bread_payload()),
            bag_slot=slot,
        )
    return char


def weapon_attack_value_from_item_data(
    item_data: dict[str, Any] | None,
    *,
    level: int,
    floor_number: int,
) -> int:
    """Базовая атака оружия (как в бою и в профиле). Без мастерства."""
    if item_data is None:
        return 5 + int(level) + int(floor_number) // 10
    base = int(item_data.get("attack", item_data.get("atk", 8)))
    ench = int(item_data.get("enchant", item_data.get("plus", 0)) or 0)
    return base + max(0, ench)


async def equipped_weapon_attack_value(session: AsyncSession, character: Character) -> int:
    weapon = await inventory_repo.get_equipped_weapon(session, character.id)
    if weapon is None:
        return weapon_attack_value_from_item_data(
            None,
            level=int(character.level),
            floor_number=int(character.floor_number),
        )
    return weapon_attack_value_from_item_data(
        dict(weapon.item_data or {}),
        level=int(character.level),
        floor_number=int(character.floor_number),
    )


def add_gold(character: Character, amount: int) -> None:
    character.gold = int(character.gold) + int(amount)


def try_spend_gold(character: Character, amount: int) -> bool:
    """Списать золото, если хватает. При amount <= 0 — True без изменений."""
    n = int(amount)
    if n <= 0:
        return True
    cur = int(character.gold)
    if cur < n:
        return False
    character.gold = cur - n
    return True


def add_experience(character: Character, amount: int) -> int:
    """Начислить опыт. Возвращает число полученных уровней за этот вызов."""
    character.experience = int(character.experience) + int(amount)
    levels = 0
    while True:
        need = experience_needed_for_next_level(character.level, character.floor_number)
        if character.experience < need:
            break
        character.experience -= need
        character.level += 1
        levels += 1
    if levels:
        character.unspent_stat_points = int(character.unspent_stat_points) + 5 * levels
    return levels


async def add_experience_async(
    session: AsyncSession,
    character: Character,
    amount: int,
    *,
    bot: Any = None,
) -> int:
    """
    Начислить опыт и при переходе приглашённого на 2+ уровень — награда пригласившему (рефералка).
    """
    old_level = int(character.level)
    gained = add_experience(character, amount)
    if old_level < 2 <= int(character.level):
        from services import referral_service

        await referral_service.try_reward_referrer_for_invitee_level_two(
            session,
            character,
            bot=bot,
        )
    return gained


def level_up_notice_html(character: Character, levels_gained: int) -> str:
    """Короткая HTML-строка для экранов награды после повышения уровня."""
    if levels_gained <= 0:
        return ""
    return (
        f"\n🎉 <b>Уровень +{levels_gained}!</b> Сейчас: <b>{character.level}</b> ур. "
        f"Свободных очков: <b>{int(character.unspent_stat_points)}</b> — команда /stats"
    )


_STAT_FIELD_BY_KEY: dict[str, str] = {
    "str": "stat_strength",
    "dex": "stat_dexterity",
    "int": "stat_intelligence",
    "vit": "stat_vitality",
    "luck": "stat_luck",
}


def refresh_hp_mp_after_stats(character: Character) -> None:
    """Пересчитать HP/MP максимумы после изменения статов; текущие полосы — пропорционально."""
    cls = get_class_or_none(character.class_key) or get_class_or_none("wanderer")
    if cls is None:
        return
    new_hp = _compute_hp_max(int(character.stat_vitality), int(character.stat_strength), cls)
    new_mp = _compute_mp_max(int(character.stat_intelligence), cls)
    old_hm = max(1, int(character.hp_max))
    old_mm = max(0, int(character.mp_max))
    character.hp_max = new_hp
    character.mp_max = new_mp
    hc = int(character.hp_current)
    mc = int(character.mp_current)
    character.hp_current = max(1, min(new_hp, int(hc * new_hp / old_hm)))
    if old_mm > 0:
        character.mp_current = max(0, min(new_mp, int(mc * new_mp / old_mm)))
    else:
        character.mp_current = max(0, min(new_mp, mc))


async def reset_all_progress_keep_identity(session: AsyncSession, character: Character) -> None:
    """
    Полный сброс игрового прогресса. Сохраняются display_name, class_key, user_id и язык (meta locale).
    Инвентарь, этажи, квесты, заточки — удаляются; персонаж как после выбора класса на 1 этаже.
    """
    # Совпадает с bot.i18n.LOCALE_KEY — сервис не тянет слой бота.
    locale_meta_key = "locale"

    cid = int(character.id)
    meta_old = dict(character.meta_progress or {})
    locale_val = meta_old.get(locale_meta_key)

    await session.execute(delete(InventoryItem).where(InventoryItem.character_id == cid))
    await session.execute(delete(FloorProgress).where(FloorProgress.character_id == cid))
    await session.execute(delete(QuestProgress).where(QuestProgress.character_id == cid))
    await session.execute(delete(EnchantLog).where(EnchantLog.character_id == cid))
    await session.flush()

    cls = get_class_or_none(character.class_key) or get_class_or_none("warrior")
    if cls is None:
        raise RuntimeError("Нет ни одного класса в реестре")

    hp_max = _compute_hp_max(cls.vitality, cls.strength, cls)
    mp_max = _compute_mp_max(cls.intelligence, cls)
    now = datetime.now(UTC)

    character.class_key = cls.key
    character.stat_strength = cls.strength
    character.stat_dexterity = cls.dexterity
    character.stat_intelligence = cls.intelligence
    character.stat_vitality = cls.vitality
    character.stat_luck = cls.luck
    character.hp_max = hp_max
    character.hp_current = hp_max
    character.mp_max = mp_max
    character.mp_current = mp_max
    character.stamina = settings.MAX_STAMINA
    character.last_stamina_regen_at = now
    character.floor_number = 1
    character.highest_floor_reached = 1
    character.class_tier = 0
    character.subclass_key = None
    character.level = 1
    character.unspent_stat_points = 0
    character.experience = 0
    character.gold = 0
    character.rune_stones = 0
    character.active_title = None
    character.element = cls.default_element
    character.total_kills = 0
    character.death_count = 0
    character.tavern_visits = 0
    character.enchant_attempts = 0
    character.runes_socketed = 0

    new_meta: dict[str, Any] = {"tutorial_battle": "pending"}
    if locale_val in ("ru", "en"):
        new_meta[locale_meta_key] = locale_val
    character.meta_progress = new_meta

    await inventory_repo.add_starter_equipped_weapon(
        session,
        cid,
        item_data=starter_weapon_payload(cls.key),
    )
    for slot in (0, 1, 2):
        await inventory_repo.add_bag_item(
            session,
            cid,
            copy.deepcopy(starter_bread_payload()),
            bag_slot=slot,
        )
    await session.flush()


def try_allocate_stat_point(character: Character, stat_key: str) -> bool:
    """Потратить 1 свободное очко на стат. True если успех."""
    field = _STAT_FIELD_BY_KEY.get(stat_key)
    if field is None:
        return False
    if int(character.unspent_stat_points) <= 0:
        return False
    cur = int(getattr(character, field))
    setattr(character, field, cur + 1)
    character.unspent_stat_points = int(character.unspent_stat_points) - 1
    refresh_hp_mp_after_stats(character)
    return True
