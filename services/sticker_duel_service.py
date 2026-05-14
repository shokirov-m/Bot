"""
Карточная «арена» (этажи 1–20): гача, альбом, дуэли.
Состояние: character.meta_progress['tower_cards_v1'].
Рейтинг дуэлей: колонки characters.sticker_duel_*.
"""

from __future__ import annotations

import html
import secrets
import string
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from loguru import logger

from aiogram import Bot
from aiogram.types import FSInputFile

from config import settings
from db.models.character import Character
from db.repository import character_repo, sticker_duel_challenge_repo, user_repo
from game.floors.monster_appearances_ru import APPEARANCE_RU
from game.sticker_pack.battle import duel_winner_from_scores, resolve_duel_scores
from game.tower_cards import monster_cards as tc
from services import character_service
from services import vip_shop_bonus_service

META_KEY = "tower_cards_v1"
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
    """Слот меты (имя функции историческое)."""
    return _slot(dict(character.meta_progress or {}))


def collection_map(character: Character) -> dict[str, dict[str, Any]]:
    st = sticker_pack_slot(character)
    raw = st.get("collection")
    coll = dict(raw) if isinstance(raw, dict) else {}
    return tc.filtered_collection(coll)


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


def _card_label_html(template_key: str, row: dict[str, Any] | None) -> str:
    nm = html.escape(str(row.get("name_ru")) if row else tc.display_name(template_key))
    em = str(row.get("emoji")) if row and row.get("emoji") else tc.emoji_for(template_key)
    return f"{html.escape(em)} {nm}"


def perform_spin(
    character: Character,
    *,
    paid: bool,
) -> tuple[bool, str, str | None, int | None]:
    """
    Одна крутка. paid=True — золото списывается в apply_paid_spin_gold.
    Возвращает (ok, html_message, template_key | None, source_floor | None).
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
            return False, "Сегодня бесплатные крутки уже использованы. Завтра снова или купи крутку за золото.", None, None
    else:
        if int(g.get("paid_used", 0)) >= MAX_PAID_SPINS_PER_DAY:
            return False, "Достигнут лимит платных круток на сегодня.", None, None

    src_floor, spawn = tc.pick_random_spawn_f1_20()
    sid = spawn.template.key
    tier = tc.tier_for_spawn(spawn, src_floor)
    atk, deff = tc.scaled_atk_def(sid, src_floor)
    raw_el = spawn.template.element
    d_el = tc.duel_element(raw_el)
    name_ru = spawn.template.name
    emoji = spawn.template.emoji

    coll_all = dict(slot.get("collection") or {})
    dup = sid in coll_all
    if dup:
        row = dict(coll_all[sid])
        row["atk"] = int(row.get("atk", 0)) + 2
        coll_all[sid] = row
        msg_extra = f"<b>Дубликат!</b> +2 ATK → теперь <b>{row['atk']}</b> ATK."
    else:
        coll_all[sid] = {
            "atk": atk,
            "def": deff,
            "element": d_el,
            "rarity": tier,
            "name_ru": name_ru,
            "emoji": emoji,
            "source_floor": src_floor,
            "raw_element": raw_el,
        }
        stars = tc.RARITY_STARS_RU.get(tier, "⭐")
        msg_extra = f"Новая карта: <b>{html.escape(name_ru)}</b> {stars}."

    if paid:
        g["paid_used"] = int(g.get("paid_used", 0)) + 1
    else:
        g["free_used"] = int(g.get("free_used", 0)) + 1

    slot["collection"] = coll_all
    slot["gacha"] = g
    _save_slot(character, meta, slot)

    stars = tc.RARITY_STARS_RU.get(tier, "⭐")
    vis = APPEARANCE_RU.get(tc.base_template_key(sid), "")
    vis_html = f"\n<i>{html.escape(vis[:220])}{'…' if len(vis) > 220 else ''}</i>" if vis else ""
    body = (
        f"🎴 <b>Выпало:</b> {html.escape(emoji)} <b>{html.escape(name_ru)}</b> {stars}\n"
        f"Этаж образца: <b>{src_floor}</b> · стихия (дуэль): <b>{d_el}</b> · было: <i>{html.escape(raw_el)}</i>\n"
        f"ATK <b>{coll_all[sid]['atk']}</b> · DEF <b>{coll_all[sid]['def']}</b>\n"
        f"{msg_extra}"
        f"{vis_html}"
    )
    return True, body, sid, src_floor


def apply_sticker_gacha_paid_spin_slot_only(character: Character) -> tuple[bool, str, str | None, int | None]:
    """Платная крутка без списания золота (оплата Stars или иной внешний платёж)."""
    if not can_use_paid_spin_slot(character):
        return False, "Достигнут лимит платных круток на сегодня.", None, None
    return perform_spin(character, paid=True)


async def apply_paid_spin_gold(session: AsyncSession, character: Character) -> tuple[bool, str, str | None, int | None]:
    """Списать золото и выполнить платную крутку."""
    if not can_buy_paid_spin_gold(character):
        return False, "Нельзя купить крутку (лимит или недостаточно золота).", None, None
    cost = int(settings.STICKER_GACHA_GOLD_PULL)
    character.gold = int(character.gold) - cost
    ok, msg, sid, fl = perform_spin(character, paid=True)
    if not ok:
        character.gold = int(character.gold) + cost
        return False, msg, None, None
    await session.flush()
    return True, msg, sid, fl


async def send_card_art_after_pull(bot: Bot, chat_id: int, template_key: str | None, source_floor: int | None) -> None:
    """После крутки — портрет монстра из assets (если файл есть)."""
    if not getattr(settings, "STICKER_SEND_AFTER_PULL", True):
        return
    if not template_key:
        return
    fl = int(source_floor or 10)
    p = tc.portrait_path(template_key, fl)
    if p is None or not p.is_file():
        return
    try:
        await bot.send_photo(chat_id, FSInputFile(p))
    except Exception:
        logger.debug("send_card_art_after_pull failed for {}", template_key)


def best_owned_sticker(character: Character) -> tuple[str, dict[str, Any], str] | None:
    """(template_key, row, display_name) или None."""
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
    name = str(coll[best_id].get("name_ru") or tc.display_name(best_id))
    return best_id, dict(coll[best_id]), name


def profile_sticker_lines_html(character: Character) -> str:
    own = unique_owned_count(character)
    total = tc.TW_POOL_TOTAL
    best = best_owned_sticker(character)
    lines = [f"🎴 <b>Коллекция карточек (этажи 1–20):</b> {own}/{total}"]
    if best:
        sid, row, name = best
        rarity = str(row.get("rarity", "common"))
        stars = tc.RARITY_STARS_RU.get(rarity, "⭐")
        lines.append(
            f"🏆 <b>Сильнейшая карта:</b> {html.escape(name)} {stars} "
            f"(<b>{int(row.get('atk', 0))}</b> ATK / <b>{int(row.get('def', 0))}</b> DEF)",
        )
    return "\n".join(lines)


def format_collection_screen_html(character: Character) -> str:
    coll = collection_map(character)
    lines = [
        "📦 <b>Альбом карточек</b>",
        f"<i>Собрано уникальных: {len(coll)}/{tc.TW_POOL_TOTAL}</i>",
        "",
    ]
    if not coll:
        lines.append("<i>Пока пусто — крути гачу в меню «Локации» → карточная арена.</i>")
        return "\n".join(lines)
    by_rare: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for sid, row in sorted(coll.items(), key=lambda x: x[0]):
        r = str(row.get("rarity", "common"))
        by_rare.setdefault(r, []).append((sid, row))
    for r in tc.RARITY_ORDER:
        if r not in by_rare:
            continue
        lines.append(f"<b>{r.upper()}</b>")
        for sid, row in by_rare[r]:
            nm = html.escape(str(row.get("name_ru", tc.display_name(sid))))
            sf = int(row.get("source_floor", 0) or 0)
            lines.append(
                f"  · {nm} — ATK {int(row.get('atk', 0))}, DEF {int(row.get('def', 0))}, "
                f"дуэль: {html.escape(str(row.get('element', '?')))}, эт.{sf}",
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
        return False, "У соперника ещё нет карточек для дуэли.", None
    if duels_used_today(attacker) >= MAX_DUELS_PER_DAY:
        return False, "Лимит дуэлей на сегодня.", None

    code = _challenge_code()
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

    na = html.escape(str(ra.get("name_ru", tc.display_name(a_sid))))
    nd = html.escape(str(rd.get("name_ru", tc.display_name(defender_sticker_id))))

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
    else:
        win_ch, lose_ch = defender, attacker
        win_name, lose_name = nd, na

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


def _portrait_str(template_key: str, row: dict[str, Any] | None) -> str | None:
    fl = int((row or {}).get("source_floor") or 10)
    p = tc.portrait_path(template_key, fl)
    return str(p) if p is not None and p.is_file() else None


async def mirror_sticker_spin_to_gacha_chat(
    bot: Bot,
    session: AsyncSession,
    character: Character,
    *,
    msg_html: str,
    sticker_id: str | None,
) -> None:
    """Дублировать крутку в канал объявлений гачи."""
    from services import gacha_broadcast_service

    u = await user_repo.get_by_id(session, int(character.user_id))
    who = html.escape((character.display_name or "?").strip() or "?")
    if u is not None and (u.username or "").strip():
        who += f" (@{html.escape((u.username or '').strip())})"
    coll = collection_map(character)
    row = coll.get(sticker_id or "") if sticker_id else None
    img = _portrait_str(sticker_id or "", row) if sticker_id else None
    await gacha_broadcast_service.broadcast_sticker_pack_activity(
        bot,
        session,
        html_text=f"🎴 {who}\n\n{msg_html}",
        sticker_file_ids=(),
        image_paths=(img,) if img else (),
    )


async def mirror_sticker_duel_to_gacha_chat(
    bot: Bot,
    session: AsyncSession,
    *,
    header_html: str,
    result_html: str,
    attacker_sticker_id: str,
    defender_sticker_id: str,
    attacker: Character | None,
    defender: Character,
) -> None:
    """Итог дуэли в канал объявлений + портреты карт."""
    from services import gacha_broadcast_service

    paths: list[str] = []
    ac = collection_map(attacker) if attacker else {}
    dc = collection_map(defender)
    pa = _portrait_str(attacker_sticker_id, ac.get(attacker_sticker_id))
    pd = _portrait_str(defender_sticker_id, dc.get(defender_sticker_id))
    if pa:
        paths.append(pa)
    if pd:
        paths.append(pd)
    await gacha_broadcast_service.broadcast_sticker_pack_activity(
        bot,
        session,
        html_text=header_html + "\n\n" + result_html,
        sticker_file_ids=(),
        image_paths=tuple(paths),
    )
