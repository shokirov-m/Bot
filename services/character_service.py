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
from game.balance import (
    BALANCE_V2_ENABLED,
    HP_PER_VIT,
    PROGRESSION_BASE_EXP,
    PROGRESSION_XP_NEED_DIVISOR_FROM_LEVEL_2,
    ZONE_MULTIPLIER_BY_MAX_FLOOR,
)
from db.models.enchant import EnchantLog
from db.models.floor_progress import FloorProgress
from db.models.inventory import InventoryItem
from db.models.quest import QuestProgress
from db.models.user import User
from db.repository import character_repo, inventory_repo
from game.items import durability as durability_mod
from game.archetypes import manager as arch_manager
from game.archetypes.models import Archetype
from game.characters.classes import get_class_or_none
from game.items.equipment import (
    starter_bread_payload,
    starter_offhand_dagger_payload,
    starter_pants_payload,
    starter_weapon_payload,
)
from game.items.rarity_scaling import scaled_weapon_attack_value
from utils.profile_portraits import META_PORTRAIT_KEY, META_REG_GENDER

# История трат золота (для админки): список словарей в meta_progress.
SPEND_LEDGER_KEY = "spend_ledger_v1"
SPEND_LEDGER_MAX = 120


def record_spend_ledger(
    character: Character,
    amount: int,
    label: str,
    *,
    kind: str = "other",
) -> None:
    """Зафиксировать трату золота; ``amount`` — положительное число (сколько потрачено)."""
    n = int(amount)
    if n <= 0:
        return
    mp = dict(character.meta_progress or {})
    items = list(mp.get(SPEND_LEDGER_KEY) or [])
    items.append(
        {
            "t": datetime.now(UTC).isoformat(timespec="seconds"),
            "a": n,
            "l": (label or "")[:200],
            "k": (kind or "other")[:48],
        },
    )
    if len(items) > SPEND_LEDGER_MAX:
        items = items[-SPEND_LEDGER_MAX:]
    mp[SPEND_LEDGER_KEY] = items
    character.meta_progress = mp


SPEND_LEDGER_ADMIN_PAGE_SIZE = 12


def format_spend_ledger_admin_html(
    character: Character,
    *,
    page: int = 0,
    page_size: int = SPEND_LEDGER_ADMIN_PAGE_SIZE,
) -> tuple[str, int, int]:
    """HTML для админки: траты золота с пагинацией. Возвращает (html, page, total_pages)."""
    import html as html_mod

    items = list((character.meta_progress or {}).get(SPEND_LEDGER_KEY) or [])
    if not items:
        return (
            "🛒 <b>Расходы золота</b>\n\n"
            "<i>Записей пока нет. История ведётся с момента обновления бота; "
            "прошлые операции сюда не переносятся.</i>",
            0,
            1,
        )
    rev = list(reversed(items))
    total = len(rev)
    psize = max(1, int(page_size))
    total_pages = max(1, (total + psize - 1) // psize)
    pg = max(0, min(int(page), total_pages - 1))
    chunk = rev[pg * psize : (pg + 1) * psize]
    lines: list[str] = [
        "🛒 <b>Расходы золота</b>",
        f"<i>Стр. <b>{pg + 1}</b>/<b>{total_pages}</b> · всего записей: <b>{total}</b> · "
        f"по <b>{psize}</b> на страницу · сумма · описание · время (UTC)</i>\n",
    ]
    for row in chunk:
        a = int(row.get("a", 0))
        lab = str(row.get("l", ""))[:220]
        t = str(row.get("t", "?"))[:40]
        lines.append(
            f"· <b>{a:,}</b> 💰 — {html_mod.escape(lab)} <i>({html_mod.escape(t)})</i>",
        )
    return "\n".join(lines), pg, total_pages


def zone_multiplier_for_floor(floor_number: int) -> float:
    """Множитель зоны по номеру текущего этажа персонажа."""
    if floor_number <= 0:
        return 1.0
    for max_floor, mult in ZONE_MULTIPLIER_BY_MAX_FLOOR:
        if floor_number <= max_floor:
            return mult
    return ZONE_MULTIPLIER_BY_MAX_FLOOR[-1][1]


def experience_needed_for_next_level(level: int, floor_number: int | None = None) -> int:
    """Опыт до следующего уровня — только от текущего уровня персонажа.

    Параметр floor_number оставлен для совместимости вызовов и игнорируется:
    раньше порог умножался на «зону этажа», из‑за чего при том же уровне требуемый опыт
    менялся при переходе между этажами (например, после возврата на низкие этажи).
    Начисление опыта за бои по-прежнему может зависеть от этажа отдельно.
    """
    _ = floor_number  # совместимость API
    if level < 1:
        level = 1
    n_next = level + 1
    need = max(1, int(PROGRESSION_BASE_EXP * (n_next**2.2)))
    need = max(1, need // PROGRESSION_XP_NEED_DIVISOR_FROM_LEVEL_2)
    return need


def _compute_hp_max(vitality: int, strength: int, arch: Archetype) -> int:
    """Базовый расчёт HP с учётом ВЫН/СИЛ и пассива архетипа.
    BALANCE_V2: HP/ВЫН — см. HP_PER_VIT в game/balance.py.
    """
    hp_per_vit = int(HP_PER_VIT) if BALANCE_V2_ENABLED else 6
    base = 40 + vitality * hp_per_vit + strength * 5
    return max(1, int(round(float(base) * float(arch.hp_multiplier))))


def _compute_mp_max(intelligence: int, arch: Archetype) -> int:
    """Базовый расчёт MP с учётом ИНТ и пассива архетипа."""
    base = 15 + intelligence * 5
    return max(0, int(round(float(base) * float(arch.mp_multiplier))))


async def create_character_for_user(
    session: AsyncSession,
    *,
    user: User,
    display_name: str,
    class_key: str,
    portrait_key: str | None = None,
    reg_gender: str | None = None,
) -> Character:
    """
    Создать персонажа для пользователя. Вызывать только если персонажа ещё нет.
    """
    arch = arch_manager.get_archetype(class_key) or arch_manager.get_archetype("wanderer")
    
    name = (display_name or "Странник")[:64]
    st_str = arch.base_stats.get("str", 10)
    st_vit = arch.base_stats.get("vit", 10)
    st_int = arch.base_stats.get("int", 10)
    
    hp_max = _compute_hp_max(st_vit, st_str, arch)
    mp_max = _compute_mp_max(st_int, arch)

    now = datetime.now(UTC)
    meta: dict[str, Any] = {"tutorial_battle": "pending"}
    pk = (portrait_key or "").strip()
    if pk:
        meta[META_PORTRAIT_KEY] = pk[:48]
    rg = str(reg_gender or "").strip().lower()
    if rg in ("male", "female"):
        meta[META_REG_GENDER] = rg
    char = Character(
        user_id=user.id,
        display_name=name,
        class_key=arch.key,
        stat_strength=st_str,
        stat_dexterity=arch.base_stats.get("dex", 10),
        stat_intelligence=st_int,
        stat_vitality=st_vit,
        stat_luck=arch.base_stats.get("luck", 10),
        hp_current=hp_max,
        hp_max=hp_max,
        mp_current=mp_max,
        mp_max=mp_max,
        stamina=settings.MAX_STAMINA,
        last_stamina_regen_at=now,
        floor_number=0,
        highest_floor_reached=0,
        level=1,
        experience=0,
        gold=0,
        rune_stones=0,
        active_title=None,
        element=getattr(arch, "default_element", None),
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
        item_data=starter_weapon_payload(arch.key),
    )
    for slot in (0, 1, 2):
        await inventory_repo.add_bag_item(
            session,
            char.id,
            copy.deepcopy(starter_bread_payload()),
            bag_slot=slot,
        )
    await inventory_repo.add_bag_item(
        session,
        char.id,
        copy.deepcopy(starter_pants_payload()),
        bag_slot=3,
    )
    if arch.key == "assassin":
        await inventory_repo.add_bag_item(
            session,
            char.id,
            copy.deepcopy(starter_offhand_dagger_payload()),
            bag_slot=4,
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
    from game.items.enchant import enchant_stat_multiplier
    base = int(item_data.get("attack", item_data.get("atk", 8)))
    ench = int(item_data.get("enchant", item_data.get("plus", 0)) or 0)
    atk = scaled_weapon_attack_value(base, item_data)
    return max(1, int(round(atk * enchant_stat_multiplier(ench))))


async def equipped_weapon_attack_value(session: AsyncSession, character: Character) -> int:
    weapon = await inventory_repo.get_equipped_weapon(session, character.id)
    off = await inventory_repo.get_equipped_in_slot(session, int(character.id), "offhand")
    lv = int(character.level)
    fl = int(character.floor_number)
    total = 0
    if weapon is not None:
        wd = dict(weapon.item_data or {})
        if not durability_mod.item_is_broken(wd):
            total += weapon_attack_value_from_item_data(wd, level=lv, floor_number=fl)
    if off is not None:
        od = dict(off.item_data or {})
        if int(od.get("attack", od.get("atk", 0)) or 0) > 0:
            if not durability_mod.item_is_broken(od):
                total += weapon_attack_value_from_item_data(od, level=lv, floor_number=fl)
    if weapon is None and off is None:
        return weapon_attack_value_from_item_data(None, level=lv, floor_number=fl)
    if total <= 0:
        return weapon_attack_value_from_item_data(None, level=lv, floor_number=fl)
    return total


def add_gold(
    character: Character,
    amount: int,
    *,
    spend_for: str | None = None,
    spend_kind: str = "other",
) -> None:
    amt = int(amount)
    if amt > 0:
        bonus = float((character.meta_progress or {}).get("achievement_gold_bonus", 0.0))
        if bonus > 0.001:
            amt = int(round(amt * (1.0 + bonus)))
    character.gold = int(character.gold) + amt
    if amt < 0 and spend_for:
        record_spend_ledger(character, -amt, spend_for, kind=spend_kind)


async def add_gold_async(
    session: AsyncSession,
    character: Character,
    amount: int,
    *,
    source: str = "other",
    bot: Bot | None = None,
    telegram_id: int | None = None,
    username: str | None = None,
) -> None:
    """Централизованное начисление золота с записью в античит."""
    add_gold(character, amount)
    if amount > 0 and telegram_id is not None:
        from services import anticheat_service
        await anticheat_service.record_gold_gain(
            session,
            character,
            telegram_id=telegram_id,
            username=username,
            gold_delta=amount,
            bot=bot,
        )


def try_spend_gold(
    character: Character,
    amount: int,
    *,
    note: str | None = None,
    kind: str = "spend",
) -> bool:
    """Списать золото, если хватает. При amount <= 0 — True без изменений."""
    n = int(amount)
    if n <= 0:
        return True
    cur = int(character.gold)
    if cur < n:
        return False
    add_gold(character, -n)
    if note:
        record_spend_ledger(character, n, note, kind=kind)
    return True


def add_experience(character: Character, amount: int) -> int:
    """Начислить опыт. Возвращает число полученных уровней за этот вызов."""
    amt = int(amount)
    if amt > 0:
        bonus = float((getattr(character, "meta_progress", None) or {}).get("achievement_xp_bonus", 0.0))
        if bonus > 0.001:
            amt = int(round(amt * (1.0 + bonus)))

    character.experience = int(character.experience) + amt
    levels = 0
    while True:
        need = experience_needed_for_next_level(character.level)
        if character.experience < need:
            break
        character.experience -= need
        character.level += 1
        levels += 1
    if levels:
        character.unspent_stat_points = int(character.unspent_stat_points) + 5 * levels
        # Grant SP starting from lvl 10
        sp_gained = 0
        for lv in range(character.level - levels + 1, character.level + 1):
            if lv >= 10:
                sp_gained += 1
        
        if sp_gained > 0:
            mp = dict(getattr(character, "meta_progress", None) or {})
            mp["unspent_sp"] = int(mp.get("unspent_sp", 0)) + sp_gained
            character.meta_progress = mp
            
    return levels


async def add_experience_async(
    session: AsyncSession,
    character: Character,
    amount: int,
    *,
    bot: Any = None,
) -> int:
    """
    Начислить опыт и реферальные награды пригласившему (2 ур. приглашённого; пять приглашённых с 3+ ур.).
    """
    old_level = int(character.level)
    gained = add_experience(character, amount)
    if gained > 0:
        try:
            from services import unlock_service

            notes = unlock_service.collect_level_unlock_notifications(
                character,
                old_level=old_level,
                new_level=int(character.level),
            )
            if notes and bot is not None:
                from db.repository import user_repo

                user = await user_repo.get_by_id(session, int(character.user_id))
                tid = int(user.telegram_id) if user is not None else 0
                if tid:
                    for msg in notes:
                        try:
                            await bot.send_message(tid, msg, parse_mode="HTML")
                        except Exception:
                            # Уведомления не должны ломать выдачу опыта.
                            pass
        except Exception:
            pass
    if old_level < 2 <= int(character.level) or int(character.level) >= 3:
        from services import referral_service

        if old_level < 2 <= int(character.level):
            await referral_service.try_reward_referrer_for_invitee_level_two(
                session,
                character,
                bot=bot,
            )
        if int(character.level) >= 3:
            await referral_service.try_reward_referrer_five_invitees_level_three(
                session,
                character,
                bot=bot,
            )
    return gained


def level_up_notice_html(character: Character, levels_gained: int) -> str:
    """Короткая HTML-строка для экранов награды после повышения уровня."""
    if levels_gained <= 0:
        return ""
    sp = int((character.meta_progress or {}).get("unspent_sp", 0))
    sp_line = f"\n✨ Очков навыков: <b>{sp}</b> — в меню персонажа" if character.level >= 10 else ""
    return (
        f"\n🎉 <b>Уровень +{levels_gained}!</b> Сейчас: <b>{character.level}</b> ур. "
        f"Свободных очков: <b>{int(character.unspent_stat_points)}</b> — /stats"
        f"{sp_line}"
    )


_ADMIN_LEVEL_CAP = 9999


async def admin_grant_character_levels(
    session: AsyncSession,
    character: Character,
    *,
    delta: int | None = None,
    target_level: int | None = None,
) -> tuple[int, str | None]:
    """
    Админ: повысить уровень (только вверх). Начисляет +5 очков характеристик за каждый новый уровень
    (как при обычном левелапе), обновляет титулы и HP/MP от эффективных статов.

    Возвращает (сколько уровней добавлено, текст ошибки или None при успехе).
    """
    old = int(character.level)
    if target_level is not None:
        tgt = int(target_level)
        if tgt < old:
            return 0, "Целевой уровень ниже текущего — снижение через эту кнопку недоступно."
        if tgt == old:
            return 0, "Уже этот уровень."
        d = tgt - old
    elif delta is not None:
        d = int(delta)
        if d <= 0:
            return 0, "Нужно положительное число уровней."
    else:
        return 0, "Внутренняя ошибка параметров."

    if old >= _ADMIN_LEVEL_CAP:
        return 0, f"Уже достигнут предел выдачи ({_ADMIN_LEVEL_CAP} ур.)."
    d = min(d, _ADMIN_LEVEL_CAP - old)
    if d <= 0:
        return 0, f"Уже достигнут предел выдачи ({_ADMIN_LEVEL_CAP} ур.)."

    character.level = old + d
    character.unspent_stat_points = int(character.unspent_stat_points) + 5 * d
    # Grant SP for admin levels too
    sp_gained = 0
    for lv in range(old + 1, character.level + 1):
        if lv >= 10:
            sp_gained += 1
    if sp_gained > 0:
        mp = dict(character.meta_progress or {})
        mp["unspent_sp"] = int(mp.get("unspent_sp", 0)) + sp_gained
        character.meta_progress = mp

    title_service.refresh_unlocks(character)
    await refresh_hp_mp_from_effective(session, character)
    return d, None


_ADMIN_UNSPENT_STAT_SINGLE_MAX = 10_000
_ADMIN_UNSPENT_STAT_TOTAL_CAP = 9_999_999


def admin_grant_unspent_stat_points(character: Character, amount: int) -> tuple[bool, str]:
    """
    Админ: добавить свободные очки характеристик (поле unspent_stat_points), без уровня.
    Распределение — только игроком в /stats.
    """
    n = int(amount)
    if n <= 0:
        return False, "Нужно положительное число очков."
    if n > _ADMIN_UNSPENT_STAT_SINGLE_MAX:
        return False, f"За раз не больше {_ADMIN_UNSPENT_STAT_SINGLE_MAX} очков."
    cur = int(getattr(character, "unspent_stat_points", 0) or 0)
    if cur + n > _ADMIN_UNSPENT_STAT_TOTAL_CAP:
        return False, f"Слишком много свободных очков (лимит {_ADMIN_UNSPENT_STAT_TOTAL_CAP})."
    character.unspent_stat_points = cur + n
    return True, ""


_STAT_FIELD_BY_KEY: dict[str, str] = {
    "str": "stat_strength",
    "dex": "stat_dexterity",
    "int": "stat_intelligence",
    "vit": "stat_vitality",
    "luck": "stat_luck",
}


def _apply_hp_mp_caps_from_totals(
    character: Character,
    *,
    vit: int,
    strn: int,
    intl: int,
    ratio_hp_old_max: int | None = None,
    ratio_mp_old_max: int | None = None,
    gear_hp_flat: int = 0,
) -> None:
    """Пересчитать максимумы HP/MP по заданным основным статам; текущие — пропорционально.

    ratio_hp_old_max / ratio_mp_old_max — знаменатель для доли текущих HP/MP до смены статов
    (например макс по эффективным статам *до* клика +1 СИЛ). Если None — берётся из полей
    персонажа; при устаревшем hp_max в БД иначе «залипал» прирост от +1 СИЛ/ВЫН.
    gear_hp_flat — плоский бонус к макс. HP с надетой брони (kind=armor, поле hp_bonus).
    """
    arch = arch_manager.get_character_archetype(character)
    gh = max(0, int(gear_hp_flat))
    new_hp = max(1, int(_compute_hp_max(int(vit), int(strn), arch)) + gh)
    new_mp = _compute_mp_max(int(intl), arch)
    old_hm = max(1, int(ratio_hp_old_max)) if ratio_hp_old_max is not None else max(1, int(character.hp_max))
    old_mm = max(0, int(ratio_mp_old_max)) if ratio_mp_old_max is not None else max(0, int(character.mp_max))
    character.hp_max = new_hp
    character.mp_max = new_mp
    hc = int(character.hp_current)
    mc = int(character.mp_current)
    character.hp_current = max(1, min(new_hp, int(hc * new_hp / old_hm)))
    if old_mm > 0:
        character.mp_current = max(0, min(new_mp, int(mc * new_mp / old_mm)))
    else:
        character.mp_current = max(0, min(new_mp, mc))


def refresh_hp_mp_after_stats(character: Character) -> None:
    """Пересчитать HP/MP только по базовым статам из БД (без экипировки). Для сбросов без сессии."""
    _apply_hp_mp_caps_from_totals(
        character,
        vit=int(character.stat_vitality),
        strn=int(character.stat_strength),
        intl=int(character.stat_intelligence),
    )


async def refresh_hp_mp_from_effective(
    session: AsyncSession,
    character: Character,
    *,
    prior_effective_stats: dict[str, int] | None = None,
    prior_armor_hp_bonus_flat: int | None = None,
) -> None:
    """HP/MP максимумы по итоговым статам (база + экипировка + титулы), как в бою.

    prior_effective_stats — снимок effective_primary_stats *до* изменения базы/экипа;
    тогда доля текущего HP/MP считается от формульного макс. до изменения, а не от hp_max в БД.
    prior_armor_hp_bonus_flat — сумма hp_bonus с брони *до* смены экипа; если None при
    prior_effective_stats, берётся текущая сумма (статы менялись, броня та же).
    """
    from services import stat_bonus_service

    eff = await stat_bonus_service.effective_primary_stats(session, character)
    gear_hp = await stat_bonus_service.equipped_armor_hp_bonus_flat(session, int(character.id))
    arch = arch_manager.get_character_archetype(character)
    ratio_hp: int | None = None
    ratio_mp: int | None = None
    if prior_effective_stats is not None:
        pe = prior_effective_stats
        old_gear_hp = (
            max(0, int(prior_armor_hp_bonus_flat))
            if prior_armor_hp_bonus_flat is not None
            else gear_hp
        )
        computed_hp = max(1, int(_compute_hp_max(int(pe["vit"]), int(pe["str"]), arch)) + old_gear_hp)
        # Если hp_max в БД «завышен» относительно формулы, долю текущего HP считаем от большего
        # знаменателя — иначе при снятии вещи здоровье проседало сильнее пропорции.
        ratio_hp = max(computed_hp, max(1, int(character.hp_max)))
        computed_mp = max(0, _compute_mp_max(int(pe["int"]), arch))
        ratio_mp = max(computed_mp, max(0, int(character.mp_max)))
    _apply_hp_mp_caps_from_totals(
        character,
        vit=int(eff["vit"]),
        strn=int(eff["str"]),
        intl=int(eff["int"]),
        ratio_hp_old_max=ratio_hp,
        ratio_mp_old_max=ratio_mp,
        gear_hp_flat=gear_hp,
    )


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


async def delete_character_and_all_progress(session: AsyncSession, character: Character) -> None:
    """
    Полный вайп: удалить персонажа так, будто его никогда не было.

    Используется для "сброса прогресса" с полным началом регистрации: пол → ник → портрет.
    Большинство связей удалится каскадом по FK (ondelete=CASCADE); здесь дополнительно
    чистим ключевые таблицы прогресса, чтобы не зависеть от настроек FK в рантайме.
    """
    cid = int(character.id)
    # Явно чистим "основные" прогресс-таблицы (дублирует каскады, но безопаснее).
    await session.execute(delete(InventoryItem).where(InventoryItem.character_id == cid))
    await session.execute(delete(FloorProgress).where(FloorProgress.character_id == cid))
    await session.execute(delete(QuestProgress).where(QuestProgress.character_id == cid))
    await session.execute(delete(EnchantLog).where(EnchantLog.character_id == cid))
    await session.flush()

    # Удаление самого персонажа (остальное — каскадом: кланы, лоты, и т.д.).
    await session.delete(character)
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
    character.highest_floor_reached = 2
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


STAT_ALLOC_RESET_COST_GOLD = 200
STAT_ALLOC_RESET_DAY_META_KEY = "stat_alloc_reset_utc_day"


def nominal_primary_stats_tuple(character: Character) -> tuple[int, int, int, int, int]:
    """
    Ожидаемые базовые статы персонажа из класса (без ручного распределения из /stats).
    После подкласса (57) статы в БД хранятся как база класса ×2.
    """
    arch = arch_manager.get_character_archetype(character)
    bs = arch.base_stats
    mult = 1
    return (
        int(bs.get("str", 10)) * mult,
        int(bs.get("dex", 10)) * mult,
        int(bs.get("int", 10)) * mult,
        int(bs.get("vit", 10)) * mult,
        int(bs.get("luck", 10)) * mult,
    )


def count_allocated_stat_points_over_nominal(character: Character) -> int:
    """Сколько очков вложено в статы сверх номинала класса (то, что вернёт сброс)."""
    nom = nominal_primary_stats_tuple(character)
    cur = (
        int(character.stat_strength),
        int(character.stat_dexterity),
        int(character.stat_intelligence),
        int(character.stat_vitality),
        int(character.stat_luck),
    )
    return sum(max(0, c - n) for c, n in zip(cur, nom))


def stat_alloc_reset_available_today(character: Character) -> bool:
    """Раз в календарный день UTC."""
    today = datetime.now(UTC).date().isoformat()
    mp = character.meta_progress or {}
    return str(mp.get(STAT_ALLOC_RESET_DAY_META_KEY) or "") != today


def try_paid_reset_stat_allocations(character: Character) -> tuple[bool, str]:
    """
    Сбросить вручную вложенные очки в статы: вернуть номинал класса и вернуть очки в unspent.
    Стоимость STAT_ALLOC_RESET_COST_GOLD, не чаще 1 раза в сутки UTC.
    Возвращает (True, "") или (False, ключ i18n).
    """
    if not stat_alloc_reset_available_today(character):
        return False, "settings_stat_reset_today"
    pts = count_allocated_stat_points_over_nominal(character)
    if pts <= 0:
        return False, "settings_stat_reset_none"
    if not try_spend_gold(
        character,
        STAT_ALLOC_RESET_COST_GOLD,
        note="Сброс распределения статов",
        kind="stats",
    ):
        return False, "settings_stat_reset_no_gold"
    nom = nominal_primary_stats_tuple(character)
    character.stat_strength = nom[0]
    character.stat_dexterity = nom[1]
    character.stat_intelligence = nom[2]
    character.stat_vitality = nom[3]
    character.stat_luck = nom[4]
    character.unspent_stat_points = int(character.unspent_stat_points) + pts
    mp = dict(character.meta_progress or {})
    mp[STAT_ALLOC_RESET_DAY_META_KEY] = datetime.now(UTC).date().isoformat()
    character.meta_progress = mp
    return True, ""


def try_allocate_stat_point(character: Character, stat_key: str, amount: int = 1) -> int:
    """Потратить до `amount` свободных очков на стат.
    Возвращает фактически потраченное количество (0 = ничего не потрачено).
    Обратная совместимость: старый bool-результат заменён на int (0 = False, >0 = True).
    """
    field = _STAT_FIELD_BY_KEY.get(stat_key)
    if field is None:
        return 0
    free = int(character.unspent_stat_points)
    if free <= 0:
        return 0
    actual = min(amount, free)
    cur = int(getattr(character, field))
    setattr(character, field, cur + actual)
    character.unspent_stat_points = free - actual
    return actual
