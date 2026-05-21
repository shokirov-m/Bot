"""Найм, отряд, бой: статы наёмников и опыт."""

from __future__ import annotations

import html
import json
import random
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from db.models.character import Character
from db.models.mercenary import Mercenary
from db.repository import mercenary_repo
from game.mercenaries.constants import (
    FEATURE_BLACK_MARKET_COMBAT,
    MERC_COMBAT_POWER_MULT,
    MERC_EXTRA_XP_KEY,
    MERC_MAX_LEVELS_ABOVE_HERO,
    MERC_PER_LEVEL_ATK,
    MERC_PER_LEVEL_HP,
    MERC_QUARTERS_GIFT_GOLD,
    MERC_GEAR_ARMOR_HP_EACH,
    MERC_GEAR_ARMOR_MAX,
    MERC_GEAR_BLADE_ATK_EACH,
    MERC_GEAR_BLADE_MAX,
    MERC_TRAIN_ATK_ADD,
    MERC_TRAIN_GOLD,
    MERC_TRAIN_HP_ADD,
    MERC_TRAIN_LOYALTY,
    MERC_WORK_DURATION_SEC,
    MERC_WORK_GOLD_BASE,
    MERC_WORK_GOLD_PER_LEVEL,
    MERC_WORK_LOYALTY_CLAIM,
    MERC_XP_LEVEL_NEED_MULT,
    merc_gear_armor_upgrade_cost,
    merc_gear_blade_upgrade_cost,
)
from game.mercenaries.mercenary_classes import role_def
from game.mercenaries.mercenary_loyalty import (
    BATTLE_WIN_LOYALTY,
    DIALOG_LOYALTY,
    GIFT_LOYALTY_DELTA,
    LOYALTY_MAX,
    loyalty_stat_multiplier,
)
from game.mercenaries.shadow_market_meta import (
    get_merc_xp_share_percent,
    get_party_merc_ids,
    max_mercs_in_battle,
    roster_collection_cap,
    set_party_merc_ids,
)
from services.progression.character_service import experience_needed_for_next_level


def _merc_extra_dict(m: Mercenary) -> dict[str, Any]:
    raw = m.extra
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return dict(parsed)
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


def merc_gear_atk_flat(m: Mercenary) -> int:
    lv = max(0, min(MERC_GEAR_BLADE_MAX, int(_merc_extra_dict(m).get("gear_blade_lv", 0))))
    return lv * MERC_GEAR_BLADE_ATK_EACH


def merc_gear_hp_flat(m: Mercenary) -> int:
    lv = max(0, min(MERC_GEAR_ARMOR_MAX, int(_merc_extra_dict(m).get("gear_armor_lv", 0))))
    return lv * MERC_GEAR_ARMOR_HP_EACH


def merc_to_combat_dict(m: Mercenary) -> dict[str, Any]:
    rd = role_def(str(m.class_role))
    mult = loyalty_stat_multiplier(int(m.loyalty))
    g_atk = merc_gear_atk_flat(m)
    g_hp = merc_gear_hp_flat(m)
    hp0 = max(1, int(round(int(m.hp_max) * mult)) + g_hp)
    atk0 = max(1, int(round(int(m.atk) * mult)) + g_atk)
    pwr = max(0.1, float(MERC_COMBAT_POWER_MULT))
    hp = max(1, int(round(hp0 * pwr)))
    atk = max(1, int(round(atk0 * pwr)))
    return {
        "id": int(m.id),
        "name": str(m.display_name),
        "role": str(m.class_role),
        "is_tank": bool(rd.is_tank),
        "hp": hp,
        "hp_max": hp,
        "atk": atk,
        "loyalty": int(m.loyalty),
        "dead": False,
    }


async def build_combat_companions(session: AsyncSession, character: Character) -> list[dict[str, Any]]:
    from game.necromancer.service import build_skeleton_companions, is_necromancer

    if is_necromancer(character):
        return build_skeleton_companions(character)
    if not FEATURE_BLACK_MARKET_COMBAT:
        return []
    ids = get_party_merc_ids(character)
    if not ids:
        return []
    rows = await mercenary_repo.get_by_ids_for_character(session, int(character.id), ids)
    by_id = {int(r.id): r for r in rows}
    out: list[dict[str, Any]] = []
    for mid in ids:
        m = by_id.get(int(mid))
        if m is None:
            continue
        if merc_work_busy(m):
            continue
        out.append(merc_to_combat_dict(m))
    return out


def merc_level_cap(character: Character) -> int:
    return max(1, int(character.level) + int(MERC_MAX_LEVELS_ABOVE_HERO))


def merc_xp_needed_for_next_level(merc_level: int) -> int:
    """XP до следующего уровня наёмника (как у героя)."""
    lv = max(1, int(merc_level))
    base = int(experience_needed_for_next_level(lv))
    mult = float(MERC_XP_LEVEL_NEED_MULT)
    return max(1, int(round(base * mult))) if mult != 1.0 else max(1, base)


def _apply_merc_baseline_stats_for_level(m: Mercenary) -> None:
    """Карточные HP/ATK по уровню роли (как при найме из лота)."""
    rd = role_def(str(m.class_role))
    lv = max(1, int(m.level))
    m.hp_max = int(rd.base_hp) + lv * int(MERC_PER_LEVEL_HP)
    m.atk = int(rd.base_atk) + lv * int(MERC_PER_LEVEL_ATK)


def _living_merc_ids_from_companions(comps: list[dict[str, Any]]) -> list[int]:
    ids: list[int] = []
    for c in comps:
        if c.get("dead") or c.get("is_skeleton"):
            continue
        raw = c.get("id")
        try:
            ids.append(int(raw))
        except (TypeError, ValueError):
            continue
    return ids


def split_tower_battle_xp_for_mercs(
    character: Character,
    gross_xp: int,
    combat_state: dict[str, Any],
) -> tuple[int, int]:
    """Сколько опыта получает герой и сколько уходит в пул наёмников (вычитается из награды).

    Пул только если в бою были живые наёмники из отряда.
    """
    if not FEATURE_BLACK_MARKET_COMBAT:
        return max(0, int(gross_xp)), 0
    comps = list(combat_state.get("companions") or [])
    ids = _living_merc_ids_from_companions(comps)
    if not ids:
        return max(0, int(gross_xp)), 0
    gx = max(0, int(gross_xp))
    share = int(get_merc_xp_share_percent(character))
    pool = int(round(gx * (max(0, min(100, share)) / 100.0)))
    pool = min(pool, gx)
    hero_xp = gx - pool
    return hero_xp, pool


async def apply_merc_battle_xp_pool(
    session: AsyncSession,
    character: Character,
    merc_pool: int,
    combat_state: dict[str, Any],
) -> int:
    """Раздать merc_pool XP по наёмникам, участвовавшим в победе (живые в конце боя).

    Возвращает XP, не влезший наёмникам на капе уровня — отдать герою, чтобы не «сгорал».
    """
    if not FEATURE_BLACK_MARKET_COMBAT or merc_pool <= 0:
        return 0
    comps = list(combat_state.get("companions") or [])
    ids = _living_merc_ids_from_companions(comps)
    if not ids:
        return 0
    rows = await mercenary_repo.get_by_ids_for_character(session, int(character.id), ids)
    by_id = {int(r.id): r for r in rows}
    ordered = [by_id[i] for i in ids if i in by_id]
    if not ordered:
        return 0
    cap = merc_level_cap(character)
    n = len(ordered)
    base = merc_pool // n
    rem = merc_pool % n
    gains = [base + (1 if i < rem else 0) for i in range(n)]
    refund_hero_xp = 0
    for m, gain in zip(ordered, gains, strict=True):
        ex = _merc_extra_dict(m)
        if int(m.level) > cap:
            refund_hero_xp += int(ex.get(MERC_EXTRA_XP_KEY, 0))
            m.level = cap
            _apply_merc_baseline_stats_for_level(m)
            ex[MERC_EXTRA_XP_KEY] = 0
        if int(m.level) >= cap:
            banked = int(ex.get(MERC_EXTRA_XP_KEY, 0))
            if banked > 0:
                refund_hero_xp += banked
                ex[MERC_EXTRA_XP_KEY] = 0
            refund_hero_xp += int(gain)
            m.extra = ex
            m.loyalty = min(LOYALTY_MAX, int(m.loyalty) + BATTLE_WIN_LOYALTY)
            try:
                flag_modified(m, "extra")
                flag_modified(m, "loyalty")
            except Exception:
                pass
            continue
        cur_xp = int(ex.get(MERC_EXTRA_XP_KEY, 0))
        if gain > 0:
            cur_xp += int(gain)
        while int(m.level) < cap:
            need = merc_xp_needed_for_next_level(int(m.level))
            if cur_xp < need:
                break
            cur_xp -= need
            m.level = int(m.level) + 1
            m.hp_max = int(m.hp_max) + int(MERC_PER_LEVEL_HP)
            m.atk = int(m.atk) + int(MERC_PER_LEVEL_ATK)
        ex[MERC_EXTRA_XP_KEY] = max(0, cur_xp)
        m.extra = ex
        m.loyalty = min(LOYALTY_MAX, int(m.loyalty) + BATTLE_WIN_LOYALTY)
        try:
            flag_modified(m, "extra")
            flag_modified(m, "level")
            flag_modified(m, "atk")
            flag_modified(m, "hp_max")
            flag_modified(m, "loyalty")
        except Exception:
            pass
    return refund_hero_xp


def apply_knockout_no_loyalty_penalty(combat_state: dict[str, Any]) -> None:
    """Нокаут без штрафа преданности (план v2)."""
    for c in list(combat_state.get("companions") or []):
        if int(c.get("hp", 0)) <= 0:
            c["dead"] = True


async def hire_from_lot(
    session: AsyncSession,
    character: Character,
    lot: dict[str, Any],
) -> tuple[bool, str]:
    cap = roster_collection_cap(character)
    if cap <= 0:
        return False, "Нужен 15+ уровень для первого слота наёмника."
    have = await mercenary_repo.count_for_character(session, int(character.id))
    if have >= cap:
        return False, f"Ростер полон ({have}/{cap}). Улучши уровень героя для слотов."

    price = int(lot.get("price_gold", 0))
    if int(character.gold) < price:
        return False, f"Нужно {price} 💰."

    character.gold = int(character.gold) - price
    ex = lot.get("extra")
    extra = dict(ex) if isinstance(ex, dict) else {}
    m = Mercenary(
        character_id=int(character.id),
        display_name=str(lot.get("display_name", "Наёмник")),
        race_key=str(lot.get("race_key", "human")),
        class_role=str(lot.get("class_role", "dd_phys")),
        rarity=str(lot.get("rarity", "common")),
        level=int(lot.get("level", 1)),
        loyalty=int(lot.get("loyalty", 40)),
        hp_max=int(lot.get("hp_max", 100)),
        atk=int(lot.get("atk", 12)),
        extra=extra,
    )
    session.add(m)
    await session.flush()
    return True, f"Наёмник <b>{m.display_name}</b> теперь в твоём ростере."


def _merc_work_until(m: Mercenary) -> datetime | None:
    raw = _merc_extra_dict(m).get("work_until_iso")
    if not raw:
        return None
    try:
        s = str(raw).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except Exception:
        return None


def merc_work_phase(m: Mercenary) -> str:
    """idle | running | ready"""
    dt = _merc_work_until(m)
    if dt is None:
        return "idle"
    if datetime.now(tz=UTC) < dt:
        return "running"
    return "ready"


def merc_work_busy(m: Mercenary) -> bool:
    return merc_work_phase(m) != "idle"


def merc_work_seconds_left(m: Mercenary) -> int:
    dt = _merc_work_until(m)
    if dt is None:
        return 0
    return max(0, int((dt - datetime.now(tz=UTC)).total_seconds()))


def quarters_train_available_today(m: Mercenary) -> bool:
    return _merc_extra_dict(m).get("train_utc") != _utc_today_iso()


async def apply_merc_train(session: AsyncSession, character: Character, m: Mercenary) -> tuple[bool, str]:
    if merc_work_busy(m):
        return False, "Сначала заверши смену на подработке."
    if not quarters_train_available_today(m):
        return False, "Сегодня уже тренировались."
    if int(character.gold) < MERC_TRAIN_GOLD:
        return False, f"Нужно {MERC_TRAIN_GOLD} 💰."
    character.gold = int(character.gold) - MERC_TRAIN_GOLD
    m.atk = int(m.atk) + MERC_TRAIN_ATK_ADD
    m.hp_max = int(m.hp_max) + MERC_TRAIN_HP_ADD
    m.loyalty = min(LOYALTY_MAX, int(m.loyalty) + MERC_TRAIN_LOYALTY)
    ex = _merc_extra_dict(m)
    ex["train_utc"] = _utc_today_iso()
    m.extra = ex
    try:
        flag_modified(m, "extra")
        flag_modified(m, "atk")
        flag_modified(m, "hp_max")
        flag_modified(m, "loyalty")
    except Exception:
        pass
    await session.flush()
    return (
        True,
        f"−{MERC_TRAIN_GOLD} 💰 · ⚔️ +{MERC_TRAIN_ATK_ADD} · ❤️ +{MERC_TRAIN_HP_ADD} max · "
        f"♥ +{MERC_TRAIN_LOYALTY}.",
    )


async def upgrade_merc_gear_blade(session: AsyncSession, character: Character, m: Mercenary) -> tuple[bool, str]:
    if merc_work_busy(m):
        return False, "На работе — пока без кузницы."
    ex = _merc_extra_dict(m)
    lv = int(ex.get("gear_blade_lv", 0))
    if lv >= MERC_GEAR_BLADE_MAX:
        return False, "Клинок на максимуме."
    cost = merc_gear_blade_upgrade_cost(lv)
    if int(character.gold) < cost:
        return False, f"Нужно {cost} 💰."
    character.gold = int(character.gold) - cost
    ex["gear_blade_lv"] = lv + 1
    m.extra = ex
    try:
        flag_modified(m, "extra")
    except Exception:
        pass
    await session.flush()
    return True, f"Клинок ур. {lv + 1} — в бою +{merc_gear_atk_flat(m)} ATK (за уровни экипа)."


async def upgrade_merc_gear_armor(session: AsyncSession, character: Character, m: Mercenary) -> tuple[bool, str]:
    if merc_work_busy(m):
        return False, "На работе — пока без оружейной."
    ex = _merc_extra_dict(m)
    lv = int(ex.get("gear_armor_lv", 0))
    if lv >= MERC_GEAR_ARMOR_MAX:
        return False, "Доспех на максимуме."
    cost = merc_gear_armor_upgrade_cost(lv)
    if int(character.gold) < cost:
        return False, f"Нужно {cost} 💰."
    character.gold = int(character.gold) - cost
    ex["gear_armor_lv"] = lv + 1
    m.extra = ex
    try:
        flag_modified(m, "extra")
    except Exception:
        pass
    await session.flush()
    return True, f"Доспех ур. {lv + 1} — в бою +{merc_gear_hp_flat(m)} HP (за уровни экипа)."


async def start_merc_work_session(session: AsyncSession, character: Character, m: Mercenary) -> tuple[bool, str]:
    ph = merc_work_phase(m)
    if ph == "running":
        return False, f"Уже на смене (~{merc_work_seconds_left(m) // 60} мин)."
    if ph == "ready":
        return False, "Сначала забери зарплату."
    mid = int(m.id)
    cur = [x for x in get_party_merc_ids(character) if int(x) != mid]
    set_party_merc_ids(character, cur)
    ex = _merc_extra_dict(m)
    ex["work_until_iso"] = (datetime.now(tz=UTC) + timedelta(seconds=MERC_WORK_DURATION_SEC)).isoformat()
    m.extra = ex
    try:
        flag_modified(m, "extra")
    except Exception:
        pass
    await session.flush()
    h, rem = MERC_WORK_DURATION_SEC // 3600, (MERC_WORK_DURATION_SEC % 3600) // 60
    human = f"{h}ч {rem}м" if h > 0 else f"{rem}м"
    return True, f"Смена ~{human}. В отряд вернётся после выплаты."


async def claim_merc_work_reward(session: AsyncSession, character: Character, m: Mercenary) -> tuple[bool, str]:
    if merc_work_phase(m) != "ready":
        return False, "Нечего забирать."
    gross = MERC_WORK_GOLD_BASE + int(m.level) * MERC_WORK_GOLD_PER_LEVEL + int(m.loyalty) // 12
    character.gold = int(character.gold) + gross
    m.loyalty = min(LOYALTY_MAX, int(m.loyalty) + MERC_WORK_LOYALTY_CLAIM)
    ex = _merc_extra_dict(m)
    ex.pop("work_until_iso", None)
    m.extra = ex
    try:
        flag_modified(m, "extra")
        flag_modified(m, "loyalty")
    except Exception:
        pass
    await session.flush()
    return True, f"+{gross} 💰 · ♥ +{MERC_WORK_LOYALTY_CLAIM}."


def _utc_today_iso() -> str:
    return datetime.now(tz=UTC).date().isoformat()


def quarters_dialog_available_today(m: Mercenary) -> bool:
    return _merc_extra_dict(m).get("quarters_dialog_utc") != _utc_today_iso()


def quarters_gift_available_today(m: Mercenary) -> bool:
    return _merc_extra_dict(m).get("quarters_gift_utc") != _utc_today_iso()


_QUARTERS_TALK_REPLIES: tuple[str, ...] = (
    "Сегодня ты дал бой не в одиночку — это заметно. Так держать, босс.",
    "Честь нести службу. Только скажи «вперёд» — прикрою как умею.",
    "После боя руки дрожат, но спокойнее, когда знаешь: приказ ясен.",
    "Золото на рынке вертится быстрее правды… но за тебя я не торгуюсь.",
    "Башня шепчет не вслух. Если пойдём выше — постараюсь не отставать.",
)


def apply_quarters_dialog(m: Mercenary) -> tuple[bool, str]:
    if not quarters_dialog_available_today(m):
        return False, "Свидание сегодня уже было — загляни завтра."
    ex = _merc_extra_dict(m)
    ex["quarters_dialog_utc"] = _utc_today_iso()
    m.extra = ex
    m.loyalty = min(LOYALTY_MAX, int(m.loyalty) + DIALOG_LOYALTY)
    try:
        flag_modified(m, "extra")
        flag_modified(m, "loyalty")
    except Exception:
        pass
    line = random.choice(_QUARTERS_TALK_REPLIES)
    return True, f"<i>«{html.escape(line)}»</i>\n♥ +{DIALOG_LOYALTY} к преданности."


def can_apply_quarters_gift(merc: Mercenary, character: Character) -> tuple[bool, str]:
    if not quarters_gift_available_today(merc):
        return False, "Подарок уже был сегодня."
    if int(character.gold) < MERC_QUARTERS_GIFT_GOLD:
        return False, f"Нужно {MERC_QUARTERS_GIFT_GOLD} 💰."
    return True, ""


async def apply_quarters_gift(session: AsyncSession, character: Character, m: Mercenary) -> tuple[bool, str]:
    ok, err = can_apply_quarters_gift(m, character)
    if not ok:
        return False, err
    character.gold = int(character.gold) - MERC_QUARTERS_GIFT_GOLD
    ex = _merc_extra_dict(m)
    ex["quarters_gift_utc"] = _utc_today_iso()
    m.extra = ex
    m.loyalty = min(LOYALTY_MAX, int(m.loyalty) + GIFT_LOYALTY_DELTA)
    try:
        flag_modified(m, "extra")
        flag_modified(m, "loyalty")
    except Exception:
        pass
    await session.flush()
    return True, f"−{MERC_QUARTERS_GIFT_GOLD} 💰 · ♥ +{GIFT_LOYALTY_DELTA} к преданности."


def format_merc_detail_html(m: Mercenary, *, party_ids: list[int]) -> str:
    rd = role_def(str(m.class_role))
    in_party = int(m.id) in {int(x) for x in party_ids}
    dlg_ok = quarters_dialog_available_today(m)
    gift_ok = quarters_gift_available_today(m)
    b_lv = max(0, min(MERC_GEAR_BLADE_MAX, int(_merc_extra_dict(m).get("gear_blade_lv", 0))))
    a_lv = max(0, min(MERC_GEAR_ARMOR_MAX, int(_merc_extra_dict(m).get("gear_armor_lv", 0))))
    gatk = merc_gear_atk_flat(m)
    ghp = merc_gear_hp_flat(m)
    train_ok = quarters_train_available_today(m)
    wph = merc_work_phase(m)
    if wph == "running":
        wline = f"💼 Подработка: смена (~{merc_work_seconds_left(m) // 60} мин)."
    elif wph == "ready":
        wline = "💼 Подработка: <b>забери зарплату</b>."
    else:
        wline = "💼 Подработка: свободен (2 ч)."
    eff = merc_to_combat_dict(m)
    lines = [
        f"🛏 <b>{html.escape(m.display_name)}</b>",
        f"{html.escape(rd.name_ru)}, ур.{m.level}, ♥ преданность <b>{m.loyalty}</b>",
        f"❤️ {m.hp_max} · ⚔️ {m.atk} <i>(база в карточке)</i>",
        f"🛡️ <b>В бою сейчас:</b> ❤️ {eff['hp_max']} · ⚔️ {eff['atk']} "
        f"<i>(учтены экип +{gatk}/{ghp} и множитель ♥)</i>",
        "",
        f"⚔️ Экип: клинок <b>{b_lv}/{MERC_GEAR_BLADE_MAX}</b> → +{gatk} ATK · "
        f"доспех <b>{a_lv}/{MERC_GEAR_ARMOR_MAX}</b> → +{ghp} HP",
        f"🎯 Тренировка: <b>{'можно' if train_ok else 'сегодня уже была'}</b> ({MERC_TRAIN_GOLD}💰).",
        wline,
        "",
        f"В отряде: <b>{'да' if in_party else 'нет'}</b>",
        f"💕 Свидание сегодня: <b>{'доступно' if dlg_ok else 'уже было'}</b>",
        f"🎁 Подарок ({MERC_QUARTERS_GIFT_GOLD} 💰) сегодня: <b>{'можно' if gift_ok else 'уже вручён'}</b>",
    ]
    return "\n".join(lines)


def format_quarters_html(
    character: Character,
    mercs: list[Mercenary],
    *,
    cap: int,
    party_ids: list[int],
) -> str:
    xp_pct = get_merc_xp_share_percent(character)
    lines = [
        "🛏 <b>Покои наёмников</b>\n",
        f"Ростер: <b>{len(mercs)}</b> / {cap}. В бою одновременно: до <b>{max_mercs_in_battle(character)}</b>.",
        "",
        "<b>Где что искать:</b>",
        "• <b>Доля XP наёмников</b> (20–40%) — кнопки <b>20% / 30% / 40%</b> внизу этого экрана. "
        f"Сейчас: <b>{xp_pct}%</b> от награды за победу в башне <b>не идёт герою</b> — эту долю делят наёмники, "
        "с которыми ты вышел в бой (живые к концу боя). Уровень наёмника не уходит дальше, чем герой "
        "уровень не ограничен уровнем героя.",
        "• <b>Свидание</b>, <b>подарок</b>, <b>тренировка</b>, <b>экип</b> (клинок/доспех) и <b>подработка</b> — "
        "в карточке наёмника (нажми имя в списке).",
        "",
    ]
    if not mercs:
        lines.append("<i>Пока пусто — купи наёмника у Жабса на чёрном рынке (26 этаж после зачистки).</i>")
        return "\n".join(lines)
    party_set = {int(x) for x in party_ids}
    lines.append("<b>Твои наёмники:</b>")
    lines.append("")
    for m in mercs:
        rd = role_def(str(m.class_role))
        in_party = "✅ в отряде" if int(m.id) in party_set else "○ вне отряда"
        lines.append(
            f"• <b>{html.escape(m.display_name)}</b> — {html.escape(rd.name_ru)}, "
            f"ур.{m.level}, ♥{m.loyalty}, ❤️{m.hp_max} ⚔️{m.atk} ({in_party})",
        )
    lines.append(
        "\n<i>При преданности 70+ наёмник умнее бьёт в авто-бою.</i>",
    )
    return "\n".join(lines)


def sync_party_after_roster_change(character: Character, valid_ids: set[int]) -> None:
    from game.mercenaries import shadow_market_meta as smm

    cur = [x for x in get_party_merc_ids(character) if int(x) in valid_ids]
    smm.set_party_merc_ids(character, cur)
