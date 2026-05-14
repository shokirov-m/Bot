"""
Стикер-гача, коллекция, дуэли: состояние в character.meta_progress['sticker_pack_v1'],
рейтинг дублей в колонках characters.sticker_duel_*.
"""

from __future__ import annotations

import html
import random
import secrets
import string
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from loguru import logger

from aiogram import Bot

from config import settings
from db.models.character import Character
from db.repository import character_repo, sticker_duel_challenge_repo, user_repo
from game.sticker_pack.catalog import (
    RARITY_ATK_RANGE,
    RARITY_DEF_RANGE,
    RARITY_STARS_RU,
    RARITY_WEIGHTS,
    STICKER_PACK_TOTAL,
    sticker_def_by_id,
    stickers_by_rarity,
)
from services import character_service
from services import vip_shop_bonus_service

META_KEY = "sticker_pack_v1"
MAX_PAID_SPINS_PER_DAY = 20
MAX_DUELS_PER_DAY = 40
DUEL_WIN_GOLD = 25
DUEL_LOSS_GOLD = 5
DUEL_WIN_XP = 8
DUEL_LOSS_XP = 3
ELO_K = 24
ELO_RATING_MIN = 100
ELO_RATING_MAX = 3000


def _utc_today() -> str:
    return datetime.now(UTC).date().isoformat()


def _slot(meta: dict[str, Any]) -> dict[str, Any]:
    raw = meta.get(META_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def _save_slot(character: Character, meta: dict[str, Any], slot: dict[str, Any]) -> None:
    mp = dict(character.meta_progress or {})
    mp[META_KEY] = slot
    character.meta_progress = mp
    flag_modified(character, "meta_progress")


def sticker_pack_slot(character: Character) -> dict[str, Any]:
    return _slot(dict(character.meta_progress or {}))


def collection_map(character: Character) -> dict[str, dict[str, Any]]:
    st = sticker_pack_slot(character)
    raw = st.get("collection")
    return dict(raw) if isinstance(raw, dict) else {}


def unique_owned_count(character: Character) -> int:
    return len(collection_map(character))


def free_spin_cap(character: Character) -> int:
    return 2 if vip_shop_bonus_service.has_frost_throne_bundle(character) else 1


def _gacha_sub(slot: dict[str, Any]) -> dict[str, Any]:
    g = slot.get("gacha")
    return dict(g) if isinstance(g, dict) else {}


def free_spins_used_today(character: Character) -> int:
    st = sticker_pack_slot(character)
    g = _gacha_sub(st)
    if g.get("date") != _utc_today():
        return 0
    return int(g.get("free_used", 0))


def paid_spins_used_today(character: Character) -> int:
    st = sticker_pack_slot(character)
    g = _gacha_sub(st)
    if g.get("date") != _utc_today():
        return 0
    return int(g.get("paid_used", 0))


def duels_used_today(character: Character) -> int:
    st = sticker_pack_slot(character)
    d = st.get("duel_day")
    if not isinstance(d, dict) or d.get("date") != _utc_today():
        return 0
    return int(d.get("n", 0))


def can_use_free_spin(character: Character) -> bool:
    return free_spins_used_today(character) < free_spin_cap(character)


def can_use_paid_spin_slot(character: Character) -> bool:
    return paid_spins_used_today(character) < MAX_PAID_SPINS_PER_DAY


def can_buy_paid_spin_gold(character: Character) -> bool:
    if not can_use_paid_spin_slot(character):
        return False
    return int(character.gold) >= int(settings.STICKER_GACHA_GOLD_PULL)


def _roll_rarity() -> str:
    total = sum(w for _, w in RARITY_WEIGHTS)
    r = random.randint(1, total)
    acc = 0
    for name, w in RARITY_WEIGHTS:
        acc += w
        if r <= acc:
            return name
    return RARITY_WEIGHTS[-1][0]


def _roll_atk_def(rarity: str) -> tuple[int, int]:
    ar = RARITY_ATK_RANGE[rarity]
    dr = RARITY_DEF_RANGE[rarity]
    return random.randint(ar[0], ar[1]), random.randint(dr[0], dr[1])


def perform_spin(
    character: Character,
    *,
    paid: bool,
) -> tuple[bool, str, str | None]:
    """
    Одна крутка. paid=True — списать золото (вызывать после проверки can_buy).
    Возвращает (ok, html_message, sticker_id_or_None).
    """
    meta = dict(character.meta_progress or {})
    slot = _slot(meta)
    today = _utc_today()
    g = _gacha_sub(slot)
    if g.get("date") != today:
        g = {"date": today, "free_used": 0, "paid_used": 0}

    if not paid:
        cap = free_spin_cap(character)
        if int(g.get("free_used", 0)) >= cap:
            return False, "Сегодня бесплатные крутки уже использованы. Завтра снова или купи крутку за золото.", None
    else:
        if int(g.get("paid_used", 0)) >= MAX_PAID_SPINS_PER_DAY:
            return False, "Достигнут лимит платных круток на сегодня.", None

    rarity = _roll_rarity()
    pool = stickers_by_rarity(rarity)
    if not pool:
        return False, "Ошибка каталога редкости.", None
    picked = random.choice(pool)
    sid = picked.id

    coll = dict(slot.get("collection") or {})
    dup = sid in coll
    if dup:
        row = dict(coll[sid])
        row["atk"] = int(row.get("atk", 0)) + 2
        coll[sid] = row
        msg_extra = f"<b>Дубликат!</b> +2 ATK → теперь <b>{row['atk']}</b> ATK."
    else:
        atk, deff = _roll_atk_def(rarity)
        coll[sid] = {"atk": atk, "def": deff, "element": picked.element}
        msg_extra = f"Новая карта: <b>{html.escape(picked.name_ru)}</b> ({RARITY_STARS_RU.get(rarity, '')})."

    if paid:
        g["paid_used"] = int(g.get("paid_used", 0)) + 1
    else:
        g["free_used"] = int(g.get("free_used", 0)) + 1

    slot["collection"] = coll
    slot["gacha"] = g
    _save_slot(character, meta, slot)

    stars = RARITY_STARS_RU.get(rarity, "")
    body = (
        f"🎴 <b>Выпало:</b> {html.escape(picked.name_ru)} {stars}\n"
        f"Стихия: <b>{picked.element}</b>\n"
        f"{msg_extra}"
    )
    return True, body, sid


def apply_sticker_gacha_paid_spin_slot_only(character: Character) -> tuple[bool, str, str | None]:
    """Платная крутка без списания золота (оплата Stars или иной внешний платёж)."""
    if not can_use_paid_spin_slot(character):
        return False, "Достигнут лимит платных круток на сегодня.", None
    return perform_spin(character, paid=True)


async def apply_paid_spin_gold(session: AsyncSession, character: Character) -> tuple[bool, str, str | None]:
    """Списать золото и выполнить платную крутку."""
    if not can_buy_paid_spin_gold(character):
        return False, "Нельзя купить крутку (лимит или недостаточно золота).", None
    cost = int(settings.STICKER_GACHA_GOLD_PULL)
    character.gold = int(character.gold) - cost
    ok, msg, sid = perform_spin(character, paid=True)
    if not ok:
        character.gold = int(character.gold) + cost
        return False, msg, None
    await session.flush()
    return True, msg, sid


async def send_sticker_effect_if_configured(bot: Bot, chat_id: int, sticker_id: str | None) -> None:
    """Опциональный эффект после дропа (file_id в каталоге)."""
    if not getattr(settings, "STICKER_SEND_AFTER_PULL", True):
        return
    if not sticker_id:
        return
    d = sticker_def_by_id(sticker_id)
    fid = getattr(d, "telegram_file_id", None) if d else None
    if not fid:
        return
    try:
        await bot.send_sticker(chat_id, fid)
    except Exception:
        logger.debug("send_sticker_effect failed for {}", sticker_id)


def best_owned_sticker(character: Character) -> tuple[str, dict[str, Any], str] | None:
    """(sticker_id, row, name_ru) или None."""
    coll = collection_map(character)
    if not coll:
        return None
    best_id = None
    best_score = -1
    for sid, row in coll.items():
        atk = int(row.get("atk", 0))
        deff = int(row.get("def", 0))
        sc = atk * 2 + deff
        if sc > best_score:
            best_score = sc
            best_id = sid
    if best_id is None:
        return None
    d = sticker_def_by_id(best_id)
    name = d.name_ru if d else best_id
    return best_id, dict(coll[best_id]), name


def profile_sticker_lines_html(character: Character) -> str:
    own = unique_owned_count(character)
    total = STICKER_PACK_TOTAL
    best = best_owned_sticker(character)
    lines = [f"🎴 <b>Коллекция стикеров:</b> {own}/{total}"]
    if best:
        sid, row, name = best
        d = sticker_def_by_id(sid)
        rarity = d.rarity if d else "common"
        stars = RARITY_STARS_RU.get(rarity, "⭐")
        lines.append(
            f"🏆 <b>Лучший стикер:</b> {html.escape(name)} {stars} "
            f"(<b>{int(row.get('atk', 0))}</b> ATK / <b>{int(row.get('def', 0))}</b> DEF)",
        )
    return "\n".join(lines)


def format_collection_screen_html(character: Character) -> str:
    coll = collection_map(character)
    lines = [
        "📦 <b>Альбом стикеров</b>",
        f"<i>Собрано уникальных: {len(coll)}/{STICKER_PACK_TOTAL}</i>",
        "",
    ]
    if not coll:
        lines.append("<i>Пока пусто — крути гачу в меню Локации.</i>")
        return "\n".join(lines)
    # по редкости группами
    by_rare: dict[str, list[tuple[str, dict]]] = {}
    for sid, row in sorted(coll.items(), key=lambda x: x[0]):
        d = sticker_def_by_id(sid)
        r = d.rarity if d else "common"
        by_rare.setdefault(r, []).append((sid, row))
    order = ["mythic", "legendary", "epic", "rare", "uncommon", "common"]
    for r in order:
        if r not in by_rare:
            continue
        lines.append(f"<b>{r.upper()}</b>")
        for sid, row in by_rare[r]:
            d = sticker_def_by_id(sid)
            nm = html.escape(d.name_ru if d else sid)
            lines.append(
                f"  · {nm} — ATK {int(row.get('atk', 0))}, DEF {int(row.get('def', 0))}, "
                f"{html.escape(str(row.get('element', '?')))}",
            )
        lines.append("")
    return "\n".join(lines).rstrip()


def _challenge_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def _parse_challenge_ts(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(ts))
    except (TypeError, ValueError):
        return None


async def create_duel_challenge(
    session: AsyncSession,
    *,
    attacker: Character,
    defender: Character,
    attacker_sticker_id: str,
) -> tuple[bool, str, str | None]:
    if attacker.id == defender.id:
        return False, "Нельзя вызвать самого себя.", None
    coll_a = collection_map(attacker)
    if attacker_sticker_id not in coll_a:
        return False, "У тебя нет этой карты.", None
    if not collection_map(defender):
        return False, "У соперника ещё нет стикеров для дуэли.", None
    if duels_used_today(attacker) >= MAX_DUELS_PER_DAY:
        return False, "Лимит дуэлей на сегодня.", None

    code = _challenge_code()
    # избегаем коллизии (редко)
    for _ in range(5):
        existing = await sticker_duel_challenge_repo.fetch_challenge(session, code)
        if existing is None:
            break
        code = _challenge_code()
    else:
        return False, "Не удалось создать код вызова.", None

    await sticker_duel_challenge_repo.insert_challenge(
        session,
        code=code,
        attacker_character_id=int(attacker.id),
        defender_character_id=int(defender.id),
        attacker_sticker_id=attacker_sticker_id,
    )
    return (
        True,
        f"Вызов отправлен. Код для соперника: <code>{code}</code>\n"
        f"Пусть введёт: <code>/duel_accept {code}</code>",
        code,
    )


async def resolve_duel_by_code(
    session: AsyncSession,
    *,
    defender: Character,
    code: str,
    defender_sticker_id: str,
) -> tuple[bool, str]:
    row = await sticker_duel_challenge_repo.fetch_challenge(session, code)
    if row is None:
        return False, "Код не найден или устарел."
    if int(row["defender_character_id"]) != int(defender.id):
        return False, "Этот вызов не для тебя."
    ts = _parse_challenge_ts(str(row.get("created_at") or ""))
    if ts is not None:
        age = (datetime.now(UTC) - ts).total_seconds()
        if age > float(settings.STICKER_DUEL_CHALLENGE_TTL_SEC):
            await sticker_duel_challenge_repo.delete_challenge(session, code)
            return False, "Вызов истёк."

    aid = int(row["attacker_character_id"])
    attacker = await character_repo.get_by_id(session, aid)
    if attacker is None:
        await sticker_duel_challenge_repo.delete_challenge(session, code)
        return False, "Атакующий не найден."

    a_sid = str(row["attacker_sticker_id"])
    coll_a = collection_map(attacker)
    coll_d = collection_map(defender)
    if a_sid not in coll_a or defender_sticker_id not in coll_d:
        return False, "У одного из игроков нет выбранной карты."

    ra = coll_a[a_sid]
    rd = coll_d[defender_sticker_id]
    atk_a, def_a = int(ra.get("atk", 0)), int(ra.get("def", 0))
    atk_d, def_d = int(rd.get("atk", 0)), int(rd.get("def", 0))
    elem_a = str(ra.get("element", "earth"))
    elem_d = str(rd.get("element", "earth"))

    sa, sb = resolve_duel_scores(
        atk_a=atk_a,
        def_a=def_a,
        atk_b=atk_d,
        def_b=def_d,
        elem_a=elem_a,
        elem_b=elem_d,
    )
    outcome = duel_winner_from_scores(sa, sb)

    da = sticker_def_by_id(a_sid)
    dd = sticker_def_by_id(defender_sticker_id)
    na = html.escape(da.name_ru if da else a_sid)
    nd = html.escape(dd.name_ru if dd else defender_sticker_id)

    # дневной счётчик у обоих
    def _bump_duel_day(ch: Character) -> None:
        mp = dict(ch.meta_progress or {})
        st = _slot(mp)
        ddct = st.get("duel_day")
        dday = dict(ddct) if isinstance(ddct, dict) else {}
        if dday.get("date") != _utc_today():
            dday = {"date": _utc_today(), "n": 0}
        dday["n"] = int(dday.get("n", 0)) + 1
        st["duel_day"] = dday
        _save_slot(ch, mp, st)

    _bump_duel_day(attacker)
    _bump_duel_day(defender)

    if outcome == "draw":
        await sticker_duel_challenge_repo.delete_challenge(session, code)
        await session.flush()
        return True, f"🤝 <b>Ничья!</b>\n{na} vs {nd}\nОчки: {sa:.1f} — {sb:.1f}"

    if outcome == "a":
        win_ch, lose_ch = attacker, defender
        win_name, lose_name = na, nd
        win_sid, lose_sid = a_sid, defender_sticker_id
    else:
        win_ch, lose_ch = defender, attacker
        win_name, lose_name = nd, na
        win_sid, lose_sid = defender_sticker_id, a_sid

    _apply_elo(win_ch, lose_ch)

    win_ch.sticker_duel_wins = int(win_ch.sticker_duel_wins) + 1
    lose_ch.sticker_duel_losses = int(lose_ch.sticker_duel_losses) + 1

    await character_service.add_gold_async(
        session,
        win_ch,
        DUEL_WIN_GOLD,
        source="sticker_duel_win",
    )
    await character_service.add_gold_async(
        session,
        lose_ch,
        DUEL_LOSS_GOLD,
        source="sticker_duel_loss",
    )
    await character_service.add_experience_async(session, win_ch, DUEL_WIN_XP)
    await character_service.add_experience_async(session, lose_ch, DUEL_LOSS_XP)

    await sticker_duel_challenge_repo.delete_challenge(session, code)
    await session.flush()

    return True, (
        f"⚔️ <b>{win_name}</b> побеждает <b>{lose_name}</b>!\n"
        f"Счёт: {sa:.1f} vs {sb:.1f}\n"
        f"Победитель: +{DUEL_WIN_GOLD} 💰, +{DUEL_WIN_XP} XP · проигравший: +{DUEL_LOSS_GOLD} 💰, +{DUEL_LOSS_XP} XP\n"
        f"<i>Рейтинг обновлён.</i>"
    )


def _apply_elo(winner: Character, loser: Character) -> None:
    rw = int(winner.sticker_duel_rating)
    rl = int(loser.sticker_duel_rating)
    e_w = 1.0 / (1.0 + 10 ** ((rl - rw) / 400.0))
    delta = round(ELO_K * (1.0 - e_w))
    delta = max(1, min(delta, 48))
    winner.sticker_duel_rating = min(ELO_RATING_MAX, rw + delta)
    loser.sticker_duel_rating = max(ELO_RATING_MIN, rl - delta)


async def resolve_opponent_by_game_id(
    session: AsyncSession,
    *,
    self_char: Character,
    game_id: int,
) -> tuple[Character | None, str | None]:
    """Найти соперника по публичному game_id."""
    stmt = select(Character).where(Character.game_id == int(game_id))
    r = await session.execute(stmt)
    opp = r.scalar_one_or_none()
    if opp is None:
        return None, "Герой с таким ID не найден."
    if int(opp.id) == int(self_char.id):
        return None, "Это твой же герой."
    return opp, None


async def mirror_sticker_spin_to_gacha_chat(
    bot: Bot,
    session: AsyncSession,
    character: Character,
    *,
    msg_html: str,
    sticker_id: str | None,
) -> None:
    """Дублировать крутку в канал объявлений гачи (GACHA_BROADCAST_*), если включено в настройках."""
    from services import gacha_broadcast_service

    u = await user_repo.get_by_id(session, int(character.user_id))
    who = html.escape((character.display_name or "?").strip() or "?")
    if u is not None and (u.username or "").strip():
        who += f" (@{html.escape((u.username or '').strip())})"
    d = sticker_def_by_id(sticker_id or "")
    fid = (d.telegram_file_id if d else None) or ""
    await gacha_broadcast_service.broadcast_sticker_pack_activity(
        bot,
        session,
        html_text=f"🎴 {who}\n\n{msg_html}",
        sticker_file_ids=(fid,) if fid else (),
    )


async def mirror_sticker_duel_to_gacha_chat(
    bot: Bot,
    session: AsyncSession,
    *,
    header_html: str,
    result_html: str,
    attacker_sticker_id: str,
    defender_sticker_id: str,
) -> None:
    """Итог дуэли — в тот же канал, что и объявления гачи; стикеры по file_id из каталога."""
    from services import gacha_broadcast_service

    fids: list[str] = []
    for sid in (attacker_sticker_id, defender_sticker_id):
        dd = sticker_def_by_id(sid)
        if dd and dd.telegram_file_id:
            fids.append(dd.telegram_file_id)
    await gacha_broadcast_service.broadcast_sticker_pack_activity(
        bot,
        session,
        html_text=header_html + "\n\n" + result_html,
        sticker_file_ids=tuple(fids),
    )
