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
from services.fame_bonuses import max_arena_matches_per_day

ARENA_MATCHES_PER_DAY = 10
META_ARENA_DAILY = "arena_daily_v1"
# Событие этажа / награда: бои, не сжигающие дневной лимит
SPIRIT_ARENA_FIGHTS_KEY = "spirit_arena_fights_v1"
ARENA_MMR_KEY = "arena_mmr_v1"
ARENA_SEASON_ID = "s1"
_DEFAULT_MMR = 1000


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
    cap = max_arena_matches_per_day(character)
    return max(0, cap - arena_matches_used_today(character))


def arena_mmr(character: Character) -> int:
    """Elo-like рейтинг 200–3000 (оценка для матчмейкинга и лиг)."""
    raw = (character.meta_progress or {}).get(ARENA_MMR_KEY)
    v = int(raw) if raw is not None and str(raw).isdigit() else _DEFAULT_MMR
    return max(200, min(3000, v))


def arena_league_label(mmr: int) -> str:
    m = int(mmr)
    if m < 900:
        return "🥉 Бронза"
    if m < 1050:
        return "🥈 Серебро"
    if m < 1200:
        return "🥇 Золото"
    if m < 1400:
        return "💎 Сапфир"
    return "👑 Элита"


def _set_arena_mmr(character: Character, new_m: int) -> None:
    mp = dict(character.meta_progress or {})
    mp[ARENA_MMR_KEY] = max(200, min(3000, int(new_m)))
    character.meta_progress = mp


def _apply_arena_mmr_duel(
    character: Character,
    *,
    outcome: Outcome,
    opponent_mmr: int,
) -> tuple[str, int]:
    """Elo-обновление; соперник-бот ≈ 800–1500. Возврат: (строка для UI, дельта mmr)."""
    my = arena_mmr(character)
    om = max(200, min(3000, int(opponent_mmr)))
    e_self = 1.0 / (1.0 + 10.0 ** ((om - my) / 400.0))
    k = 28.0
    if outcome == "win":
        s = 1.0
    elif outcome == "lose":
        s = 0.0
    else:
        s = 0.5
    new_m = int(my + k * (s - e_self))
    delta = int(new_m - my)
    _set_arena_mmr(character, new_m)
    icon = "📈" if delta > 0 else "📉" if delta < 0 else "⏸"
    return f"{icon} MMR: <b>{new_m}</b> ({'+' if delta > 0 else ''}{delta}). Лига: {arena_league_label(new_m)}.", delta


def spirit_arena_charges(character: Character) -> int:
    """Сколько запасных боёв с события этажа (без дневного лимита)."""
    meta = dict(character.meta_progress or {})
    return max(0, int(meta.get(SPIRIT_ARENA_FIGHTS_KEY) or 0))


def _record_arena_match(character: Character) -> None:
    meta = dict(character.meta_progress or {})
    cap = max_arena_matches_per_day(character)
    used = arena_matches_used_today(character)
    if used < cap:
        today = _utc_today_iso()
        raw = meta.get(META_ARENA_DAILY)
        if not isinstance(raw, dict) or raw.get("d") != today:
            meta[META_ARENA_DAILY] = {"d": today, "n": 1}
        else:
            meta[META_ARENA_DAILY] = {"d": today, "n": int(raw.get("n", 0)) + 1}
    else:
        s = spirit_arena_charges(character)
        if s > 0:
            meta[SPIRIT_ARENA_FIGHTS_KEY] = s - 1
    character.meta_progress = meta


def arena_daily_limit_reached(character: Character) -> bool:
    """True — нельзя начать бой (лимит дня исчерпан и нет дух-запасов)."""
    cap = max_arena_matches_per_day(character)
    if arena_matches_used_today(character) < cap:
        return False
    return spirit_arena_charges(character) <= 0


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


async def prepare_arena_turn_opponent(
    session: AsyncSession,
    character: Character,
    *,
    fixed_opponent: Character | None,
) -> tuple[Character | None, str, float, str, int, bool]:
    """
    Соперник и баннер для пошаговой дуэли (как в run_shadow_match).
    Возвращает: opp | None, o_name, o_pow, banner_html, win_bonus, is_npc.
    """
    if fixed_opponent is not None:
        o_pow, o_name = await _power_label(session, fixed_opponent)
        gid = int(fixed_opponent.game_id) if fixed_opponent.game_id is not None else 0
        banner = (
            "<i>⚔️ Дуэль 1×1 (пошагово) с <b>"
            f"{html.escape(o_name)}</b> · игровой ID <b>{gid}</b>.</i>\n\n"
        )
        return fixed_opponent, o_name, float(o_pow), banner, 12, False

    opp = await character_repo.random_shadow_opponent(session, character.id)
    if opp is None:
        o_pow, o_name = npc_shadow_power(character), "Тень башни"
        banner = "<i>Пошаговый бой с <b>Тенью башни</b> (пока нет других героев в базе).</i>\n\n"
        return None, o_name, float(o_pow), banner, 0, True
    o_pow, o_name = await _power_label(session, opp)
    banner = "<i>Пошаговый бой со случайным героем из базы.</i>\n\n"
    return opp, o_name, float(o_pow), banner, 6, False


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
        from services import character_service

        gold = base_gold + (0 if is_npc else win_bonus)
        character_service.add_gold(character, gold)
        return _finish_match(
            character,
            f"{banner}"
            f"Противник: <b>{o_name}</b>\n"
            f"Счёт раундов: <b>{wins}</b>–<b>{losses}</b>.",
            gold,
            "win",
        )
    if losses >= 2:
        from services import character_service

        raw_penalty = max(8, int(base_gold * 0.4))
        cur = int(character.gold)
        penalty = min(raw_penalty, cur)
        gold_delta = -penalty
        if penalty > 0:
            character_service.add_gold(character, -penalty, spend_for="Арена: штраф", spend_kind="arena")
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


# ── Фантомы Топ-10 ─────────────────────────────────────────────────────────

async def top10_phantoms(
    session: AsyncSession,
    actor_id: int,
) -> list[tuple[Character, float, str]]:
    """
    Список до 10 сильнейших игроков (по мощи арены) кроме самого актора.
    Возвращает список (Character, power, name).
    """
    from db.repository import leaderboard_repo
    candidates: list[Character] = await leaderboard_repo.top_by_stat_sum(session, limit=20)
    result: list[tuple[Character, float, str]] = []
    for c in candidates:
        if int(c.id) == int(actor_id):
            continue
        p, n = await _power_label(session, c)
        result.append((c, p, n))
        if len(result) >= 10:
            break
    return result


async def prepare_phantom_fight(
    session: AsyncSession,
    character: Character,
    phantom_char: Character,
) -> tuple[str, dict]:
    """
    Подготовка пошаговой дуэли с фантомом (без начисления наград и учёта лимита).
    Возвращает: banner_html, initial_state.
    """
    import html as _html
    p_pow, _ = await _power_label(session, phantom_char)
    gid = int(phantom_char.game_id) if phantom_char.game_id is not None else 0
    name = (phantom_char.display_name or "Странник")[:32]
    banner = (
        "👻 <i>Тренировочный бой с фантомом <b>"
        f"{_html.escape(name)}</b> (ID <b>{gid}</b>).</i>\n"
        "<i>Награды нет — это только тренировка.</i>\n\n"
    )
    st = build_turn_duel_open_state(
        character=character,
        opponent=phantom_char,
        opponent_name=name,
        opponent_power=p_pow,
        opponent_mmr=arena_mmr(phantom_char),
        banner_html=banner,
        win_bonus=0,
        is_npc=True,  # is_npc=True → нет золота при победе/поражении
    )
    # Помечаем как фантомный бой (не считается в дневной лимит)
    st["is_phantom"] = True
    st["hist"] = []
    return banner, st


def finish_phantom_duel_no_economy(
    state: dict,
) -> str:
    """Итог боя с фантомом — только текст, без изменения золота/лимита."""
    p_hp = int(state.get("p_hp", 0))
    o_hp = int(state.get("o_hp", 0))
    if p_hp <= 0:
        return "👻 Тренировка завершена: <b>поражение</b>. Фантом оказался сильнее!"
    if o_hp <= 0:
        return "👻 Тренировка завершена: <b>победа!</b> Фантом побеждён — но золото не начислено."
    if p_hp > o_hp:
        return "👻 Тренировка (лимит раундов): <b>ты впереди по HP</b>."
    if p_hp < o_hp:
        return "👻 Тренировка (лимит раундов): <b>фантом впереди по HP</b>."
    return "👻 Тренировка: <b>ничья</b>."


# Обратная совместимость для тестов
async def player_power(session: AsyncSession, character: Character) -> float:
    return await character_arena_power(session, character)


def _hp_pool(character: Character) -> int:
    return max(
        35,
        40 + int(character.level) * 2 + int(character.floor_number) // 2 + int(character.stat_vitality) // 2,
    )


def build_turn_duel_open_state(
    *,
    character: Character,
    opponent: Character | None,
    opponent_name: str,
    opponent_power: float,
    opponent_mmr: int,
    banner_html: str,
    win_bonus: int,
    is_npc: bool,
) -> dict:
    """Снимок для FSM: пошаговая дуэль (один игрок в чате, соперник из БД или тень)."""
    pm = _hp_pool(character)
    # «Тень» без записи героя — те же правила по этажу
    if opponent is None:
        om = max(30, 35 + int(character.floor_number) * 2)
        oid = 0
    else:
        om = _hp_pool(opponent)
        oid = int(opponent.id)
    return {
        "v": 1,
        "p_hp": pm,
        "p_max": pm,
        "o_hp": om,
        "o_max": om,
        "o_name": opponent_name[:48],
        "o_pow": float(opponent_power),
        "o_mmr": int(opponent_mmr),
        "banner": banner_html,
        "win_bonus": int(win_bonus),
        "is_npc": bool(is_npc),
        "opp_id": oid,
        "next_inc_reduction": 0.0,
        "round_i": 0,
        "max_rounds": 8,
    }


def format_turn_duel_screen_html(state: dict, *, log_lines: list[str] | None = None) -> str:
    log_lines = log_lines or []
    ommr = int(state.get("o_mmr", 1000) or 1000)
    body = (
        f"{state['banner']}"
        f"<b>{html.escape(state['o_name'])}</b> · MMR соперника: <b>~{ommr}</b> · "
        f"раунд <b>{int(state['round_i']) + 1}</b> / {int(state['max_rounds'])}\n"
        f"Ты: <b>{int(state['p_hp'])}</b> / {int(state['p_max'])} HP · "
        f"Соперник: <b>{int(state['o_hp'])}</b> / {int(state['o_max'])} HP\n"
        "<i>Удар — урон обоим; Защита — меньше урона в ответ, без твоего удара.</i>\n"
    )
    if log_lines:
        body += "\n" + "\n".join(log_lines[-6:])
    return body


def apply_turn_duel_step(
    character: Character,
    state: dict,
    move: str,
) -> tuple[dict, list[str], Outcome | None]:
    """
    Один ход игрока (atk|def). Возвращает (нов_state, log, outcome или None если бой продолжается).
    """
    import random

    move = (move or "").lower().strip()
    if move not in ("atk", "def"):
        move = "atk"

    logs: list[str] = []
    red = float(state.get("next_inc_reduction") or 0.0)
    st = int(character.stat_strength)
    floor_f = max(1, int(character.floor_number))
    o_pow = max(20.0, float(state.get("o_pow") or 40.0))

    if move == "atk":
        raw = random.randint(6, 14) + st // 4 + floor_f // 5
        dealt = max(2, int(raw * random.uniform(0.92, 1.08)))
        state["o_hp"] = int(state["o_hp"]) - dealt
        logs.append(f"⚔️ Ты бьёшь на <b>{dealt}</b>.")

        back = int((o_pow * 0.12 + random.uniform(3, 9)) * random.uniform(0.88, 1.12))
        back = max(2, int(back * (1.0 - min(0.75, red))))
        state["p_hp"] = int(state["p_hp"]) - back
        logs.append(f"↩️ Ответ: <b>-{back}</b> HP.")
        state["next_inc_reduction"] = 0.0
    else:
        heal = min(6, int(state["p_max"]) - int(state["p_hp"]))
        if heal > 0:
            state["p_hp"] = int(state["p_hp"]) + heal
            logs.append(f"🛡️ Защита · +{heal} HP.")
        else:
            logs.append("🛡️ Защита · HP уже полные.")
        state["next_inc_reduction"] = 0.38

        opp_act = random.choice(("atk", "def"))
        if opp_act == "atk":
            hit = int((o_pow * 0.10 + random.uniform(2, 8)) * random.uniform(0.85, 1.1))
            hit = max(1, int(hit * (1.0 - min(0.75, red))))
            state["p_hp"] = int(state["p_hp"]) - hit
            logs.append(f"Соперник бьёт: <b>-{hit}</b> HP.")
        else:
            tick = min(5, int(state["o_max"]) - int(state["o_hp"]))
            if tick > 0:
                state["o_hp"] = int(state["o_hp"]) + tick
                logs.append(f"Соперник в защите · +{tick} HP себе.")
            else:
                logs.append("Соперник в защите.")

    state["p_hp"] = max(0, min(int(state["p_max"]), int(state["p_hp"])))
    state["o_hp"] = max(0, min(int(state["o_max"]), int(state["o_hp"])))
    state["round_i"] = int(state["round_i"]) + 1

    if int(state["o_hp"]) <= 0:
        return state, logs, "win"
    if int(state["p_hp"]) <= 0:
        return state, logs, "lose"
    if int(state["round_i"]) >= int(state["max_rounds"]):
        if int(state["p_hp"]) > int(state["o_hp"]):
            return state, logs + ["⏱️ Время — по HP ты впереди."], "win"
        if int(state["p_hp"]) < int(state["o_hp"]):
            return state, logs + ["⏱️ Время — соперник впереди по HP."], "lose"
        return state, logs + ["⏱️ Время — равные HP."], "draw"

    return state, logs, None


def finish_turn_duel_economy(
    character: Character,
    *,
    outcome: Outcome,
    is_npc: bool,
    win_bonus: int,
    opponent_mmr: int = 1000,
) -> tuple[str, int, Outcome]:
    """Награды, MMR, учёт дневного/дух-лимита (один бой)."""
    from services import character_service

    base_gold = 12 + int(character.floor_number) // 2 + int(character.level)
    gold_delta = 0
    if outcome == "win":
        gold_delta = base_gold + (0 if is_npc else int(win_bonus))
        character_service.add_gold(character, gold_delta)
        report = f"Итог: <b>победа</b>.\nНаграда: <b>+{gold_delta}</b> 💰"
    elif outcome == "lose":
        raw_penalty = max(8, int(base_gold * 0.4))
        cur = int(character.gold)
        penalty = min(raw_penalty, cur)
        gold_delta = -penalty
        if penalty > 0:
            character_service.add_gold(character, -penalty, spend_for="Арена: штраф", spend_kind="arena")
        report = (
            f"Итог: <b>поражение</b>.\nШтраф: <b>-{penalty}</b> 💰" if penalty > 0 else "Итог: <b>поражение</b>."
        )
    else:
        report = "Итог: <b>ничья</b>."
    mmr_line, _d = _apply_arena_mmr_duel(
        character,
        outcome=outcome,
        opponent_mmr=int(opponent_mmr),
    )
    report = f"{report}\n{mmr_line}"
    _ = ARENA_SEASON_ID  # сезон; награда сезона — через планировщик
    _record_arena_match(character)
    return report, gold_delta, outcome
