"""
Арена теней: сила считается по реальным статам и надетому оружию из БД.
Случайный соперник — тоже живой герой; если в базе только ты — «Тень башни».
Вызов: Telegram ID, @username или ответ на сообщение игрока.
"""

from __future__ import annotations

import html
import random
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.repository import character_repo, inventory_repo, user_repo

ARENA_MATCHES_PER_DAY = 10
META_ARENA_DAILY = "arena_daily_v1"


def _utc_today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


def arena_matches_used_today(character: Character) -> int:
    meta = dict(character.meta_progress or {})
    raw = meta.get(META_ARENA_DAILY)
    if not isinstance(raw, dict):
        return 0
    if raw.get("d") != _utc_today_iso():
        return 0
    return int(raw.get("n", 0))


def arena_matches_remaining_today(character: Character) -> int:
    return max(0, ARENA_MATCHES_PER_DAY - arena_matches_used_today(character))


def _record_arena_match(character: Character) -> None:
    meta = dict(character.meta_progress or {})
    today = _utc_today_iso()
    raw = meta.get(META_ARENA_DAILY)
    if not isinstance(raw, dict) or raw.get("d") != today:
        meta[META_ARENA_DAILY] = {"d": today, "n": 1}
    else:
        meta[META_ARENA_DAILY] = {"d": today, "n": int(raw.get("n", 0)) + 1}
    character.meta_progress = meta


def arena_daily_limit_reached(character: Character) -> bool:
    return arena_matches_used_today(character) >= ARENA_MATCHES_PER_DAY


def _arena_power(
    strength: int,
    dexterity: int,
    level: int,
    floor_number: int,
    weapon_attack: int,
) -> float:
    return (
        float(strength) * 3.0
        + float(dexterity) * 2.0
        + float(level) * 5.0
        + float(floor_number) * 1.5
        + float(weapon_attack) * 1.2
    )


async def character_arena_power(session: AsyncSession, character: Character) -> float:
    """Мощь героя: реальные статы + фактическое надетое оружие (атака + заточка)."""
    w = await inventory_repo.get_equipped_weapon(session, character.id)
    if w is None:
        w_atk = 5 + int(character.level) + int(character.floor_number) // 10
    else:
        data = w.item_data or {}
        base = int(data.get("attack", data.get("atk", 8)))
        ench = int(data.get("enchant", data.get("plus", 0)) or 0)
        w_atk = base + max(0, ench)
    return _arena_power(
        int(character.stat_strength),
        int(character.stat_dexterity),
        int(character.level),
        int(character.floor_number),
        w_atk,
    )


async def _power_label(session: AsyncSession, opp: Character) -> tuple[float, str]:
    p = await character_arena_power(session, opp)
    return p, (opp.display_name or "Странник")[:32]


def npc_shadow_power(character: Character) -> float:
    """Если в БД никого кроме тебя — тень башни по твоему этажу."""
    f = max(1, int(character.floor_number))
    return 40.0 + f * 4.0 + random.uniform(-5, 15)


async def resolve_opponent(
    session: AsyncSession,
    actor: Character,
    *,
    telegram_id: int | None = None,
    username: str | None = None,
) -> tuple[Character | None, str | None]:
    """
    Явный вызов игрока. (None, None) — без вызова (случайный режим).
    Иначе (Character, None) или (None, ключ_ошибки_i18n).
    """
    if telegram_id is None and (username is None or not username.strip()):
        return None, None

    if telegram_id is not None:
        user = await user_repo.get_by_telegram_id(session, telegram_id)
    else:
        user = await user_repo.find_by_username_ci(session, username or "")

    if user is None:
        return None, "arena_err_not_found"
    if user.is_banned:
        return None, "arena_err_target_banned"
    opp = await character_repo.get_by_user_id(session, user.id)
    if opp is None:
        return None, "arena_err_no_hero_target"
    if opp.id == actor.id:
        return None, "arena_err_self"
    return opp, None


async def resolve_opponent_digit_token(
    session: AsyncSession,
    actor: Character,
    value: int,
) -> tuple[Character | None, str | None]:
    """Число из команды: сначала как игровой ID героя, иначе как Telegram ID пользователя."""
    opp = await character_repo.get_by_game_id(session, int(value))
    if opp is not None:
        if opp.id == actor.id:
            return None, "arena_err_self"
        return opp, None
    return await resolve_opponent(session, actor, telegram_id=int(value), username=None)


Outcome = Literal["win", "lose", "draw"]


def _finish_match(
    character: Character,
    report: str,
    gold_delta: int,
    outcome: Outcome,
) -> tuple[str, int, Outcome]:
    _record_arena_match(character)
    return (report, gold_delta, outcome)


async def run_shadow_match(
    session: AsyncSession,
    character: Character,
    *,
    fixed_opponent: Character | None = None,
) -> tuple[str, int, Outcome]:
    """
    Три раунда «теневого» столкновения по мощи.
    fixed_opponent: дуэль с конкретным героем из БД; иначе случайный игрок или NPC.
    """
    if arena_daily_limit_reached(character):
        raise RuntimeError("arena: daily limit reached but run_shadow_match was called")

    p_pow = await character_arena_power(session, character)

    if fixed_opponent is not None:
        o_pow, o_name = await _power_label(session, fixed_opponent)
        gid = int(fixed_opponent.game_id) if fixed_opponent.game_id is not None else 0
        banner = (
            "<i>⚔️ Поединок 1×1 с реальным игроком: <b>"
            f"{html.escape(o_name)}</b> · игровой ID <b>{gid}</b> "
            "(статы и оружие из базы).</i>\n\n"
        )
        win_bonus = 12
        is_npc = False
    else:
        opp = await character_repo.random_shadow_opponent(session, character.id)
        if opp is None:
            o_pow, o_name = npc_shadow_power(character), "Тень башни"
            banner = "<i>Тень башни — пока нет других героев в базе.</i>\n\n"
            win_bonus = 0
            is_npc = True
        else:
            o_pow, o_name = await _power_label(session, opp)
            banner = "<i>Случайный соперник — реальный герой из базы (билд 1×1).</i>\n\n"
            win_bonus = 6
            is_npc = False

    wins, losses = 0, 0
    for _ in range(3):
        pr = p_pow * random.uniform(0.88, 1.12)
        or_ = o_pow * random.uniform(0.88, 1.12)
        if pr > or_:
            wins += 1
        elif pr < or_:
            losses += 1
        else:
            if random.random() < 0.5:
                wins += 1
            else:
                losses += 1

    base_gold = 12 + int(character.floor_number) // 2 + int(character.level)

    if wins >= 2:
        gold = base_gold + (0 if is_npc else win_bonus)
        character.gold = int(character.gold) + gold
        return _finish_match(
            character,
            f"{banner}"
            f"Противник: <b>{o_name}</b>\n"
            f"Счёт раундов: <b>{wins}</b>–<b>{losses}</b>.",
            gold,
            "win",
        )
    if losses >= 2:
        raw_penalty = max(8, int(base_gold * 0.4))
        cur = int(character.gold)
        penalty = min(raw_penalty, cur)
        if penalty > 0:
            character.gold = cur - penalty
        gold_delta = -penalty
        return _finish_match(
            character,
            f"{banner}"
            f"Противник: <b>{o_name}</b>\n"
            f"Счёт: <b>{wins}</b>–<b>{losses}</b>.",
            gold_delta,
            "lose",
        )
    return _finish_match(
        character,
        f"{banner}"
        f"Противник: <b>{o_name}</b>\n"
        f"Счёт: <b>{wins}</b>–<b>{losses}</b>.",
        0,
        "draw",
    )


# Обратная совместимость для тестов
async def player_power(session: AsyncSession, character: Character) -> float:
    return await character_arena_power(session, character)
