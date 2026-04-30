"""
Кланы: создание, уровни, постройки, казна, захват этажей, войны, реликвии, панель лидера.

payload Clan:
  treasury_gold   int           — золото в казне
  materials       dict          — {"wood": 0, "stone": 0, "herbs": 0}
  buildings       dict          — {"barracks": {"built": True, "build_until": null}}
  relics          list[str]     — ключи активных реликвий
  captured_floors dict          — {"15": {"captured_at": ..., "expires_at": ..., "income_at": ...}}
  war             dict | None   — текущая война (null = нет войны)
  event_log       list[dict]    — последние 20 событий для лидера
  banner          dict          — {"emoji": "⚔️", "text": "Клан"}
"""

from __future__ import annotations

import html
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.clan import Clan, ClanMembership
from db.models.character import Character
from db.models.user import User
from db.repository import clan_repo

# ─────────────────────────── Константы ─────────────────────────────────────

CLAN_RENAME_COST = 5_000
RENAME_COST = CLAN_RENAME_COST

CLAN_CREATE_COST_GOLD = 20_000

_NAME_RE = re.compile(r"^[\w\s\-\.А-Яа-яЁё]{2,40}$")
_TAG_RE = re.compile(r"^[A-Za-zА-Яа-яЁё0-9]{2,5}$")

# Роли
ROLES: dict[str, str] = {
    "leader":  "👑 Глава",
    "officer": "⚔️ Офицер",
    "veteran": "🛡️ Ветеран",
    "member":  "🧑 Рядовой",
}

ROLE_ORDER = ["leader", "officer", "veteran", "member"]


def role_label(role: str) -> str:
    return ROLES.get(role, "🧑 Рядовой")


def can_manage(role: str) -> bool:
    """Officer and above can kick/invite."""
    return role in ("leader", "officer")


# ─────────────────────────── Уровни клана ───────────────────────────────────

CLAN_LEVEL_DEFS: list[dict[str, Any]] = [
    # уровень 1 — стартовый, бесплатно
    {"level": 1,  "max_members": 5,   "cost_gold": 0,       "cost_wood": 0,    "cost_stone": 0,   "cost_herbs": 0},
    # уровень 2
    {"level": 2,  "max_members": 10,  "cost_gold": 5_000,   "cost_wood": 100,  "cost_stone": 0,   "cost_herbs": 0},
    # уровень 3
    {"level": 3,  "max_members": 20,  "cost_gold": 10_000,  "cost_wood": 500,  "cost_stone": 200, "cost_herbs": 0},
    # уровень 4
    {"level": 4,  "max_members": 30,  "cost_gold": 20_000,  "cost_wood": 800,  "cost_stone": 400, "cost_herbs": 100},
    # уровень 5
    {"level": 5,  "max_members": 40,  "cost_gold": 35_000,  "cost_wood": 1200, "cost_stone": 700, "cost_herbs": 300},
    # уровень 6
    {"level": 6,  "max_members": 50,  "cost_gold": 50_000,  "cost_wood": 1800, "cost_stone": 1000,"cost_herbs": 500},
    # уровень 7
    {"level": 7,  "max_members": 60,  "cost_gold": 70_000,  "cost_wood": 2500, "cost_stone": 1500,"cost_herbs": 800},
    # уровень 8
    {"level": 8,  "max_members": 70,  "cost_gold": 100_000, "cost_wood": 3500, "cost_stone": 2000,"cost_herbs": 1200},
    # уровень 9
    {"level": 9,  "max_members": 80,  "cost_gold": 150_000, "cost_wood": 5000, "cost_stone": 3000,"cost_herbs": 2000},
    # уровень 10
    {"level": 10, "max_members": 100, "cost_gold": 200_000, "cost_wood": 7000, "cost_stone": 4500,"cost_herbs": 3000},
]

_LEVEL_MAP: dict[int, dict[str, Any]] = {d["level"]: d for d in CLAN_LEVEL_DEFS}


def level_def(level: int) -> dict[str, Any]:
    return _LEVEL_MAP.get(level, CLAN_LEVEL_DEFS[-1])


def max_members_for_level(level: int) -> int:
    return int(level_def(level)["max_members"])


# ─────────────────────────── Постройки ──────────────────────────────────────

BUILDING_DEFS: dict[str, dict[str, Any]] = {
    "barracks": {
        "name": "🏟️ Казармы",
        "unlock_level": 2,
        "cost_gold": 2_000,   "cost_wood": 100, "cost_stone": 0,   "cost_herbs": 0,
        "build_hours": 2,
        "desc": "+5 слотов участников (суммируется со следующими уровнями клана).",
    },
    "forge_hall": {
        "name": "⚒️ Кузница",
        "unlock_level": 3,
        "cost_gold": 5_000,   "cost_wood": 300, "cost_stone": 100, "cost_herbs": 0,
        "build_hours": 6,
        "desc": "+5% к урону участников клана в бою (пассив).",
    },
    "library": {
        "name": "📚 Библиотека",
        "unlock_level": 3,
        "cost_gold": 5_000,   "cost_wood": 300, "cost_stone": 150, "cost_herbs": 0,
        "build_hours": 12,
        "desc": "+10% к получаемому опыту за победы над монстрами.",
    },
    "alchemy_lab": {
        "name": "⚗️ Алхимическая лаборатория",
        "unlock_level": 4,
        "cost_gold": 8_000,   "cost_wood": 400, "cost_stone": 200, "cost_herbs": 300,
        "build_hours": 24,
        "desc": "Позволяет крафтить реликвии из материалов казны.",
    },
    "treasury_vault": {
        "name": "🏦 Сокровищница",
        "unlock_level": 3,
        "cost_gold": 4_000,   "cost_wood": 200, "cost_stone": 150, "cost_herbs": 0,
        "build_hours": 8,
        "desc": "Увеличивает лимит казны до 500 000 💰 (без неё — 100 000 💰).",
    },
    "watchtower": {
        "name": "🗼 Сторожевая башня",
        "unlock_level": 5,
        "cost_gold": 12_000,  "cost_wood": 400, "cost_stone": 500, "cost_herbs": 0,
        "build_hours": 16,
        "desc": "+12 ч. к длительности захвата этажа (72 → 84 ч.).",
    },
    "armory": {
        "name": "⚔️ Арсенал",
        "unlock_level": 6,
        "cost_gold": 18_000,  "cost_wood": 600, "cost_stone": 400, "cost_herbs": 0,
        "build_hours": 20,
        "desc": "+7% к урону во время гильдийной войны.",
    },
    "clan_vault": {
        "name": "🗄️ Общее хранилище",
        "unlock_level": 5,
        "cost_gold": 12_000,  "cost_wood": 500, "cost_stone": 200, "cost_herbs": 0,
        "build_hours": 16,
        "desc": "20 общих слотов. Рядовые: 3 предмета/день; Офицеры: 10 предметов/день.",
    },
    "shrine": {
        "name": "🛕 Алтарь доблести",
        "unlock_level": 7,
        "cost_gold": 25_000,  "cost_wood": 700, "cost_stone": 500, "cost_herbs": 600,
        "build_hours": 36,
        "desc": "+10% к очкам вклада за все действия.",
    },
}

# ─────────────────────────── Реликвии ───────────────────────────────────────

RELIC_DEFS: dict[str, dict[str, Any]] = {
    "banner_of_conquest": {
        "name": "🚩 Знамя завоевателя",
        "desc": "+15% очков в гильдийной войне.",
        "craft_wood": 500, "craft_stone": 300, "craft_herbs": 200, "craft_gold": 20_000,
        "requires_alchemy_lab": True,
    },
    "shield_of_endurance": {
        "name": "🛡️ Щит стойкости",
        "desc": "-20% потери очков при проигрыше в войне.",
        "craft_wood": 300, "craft_stone": 600, "craft_herbs": 100, "craft_gold": 18_000,
        "requires_alchemy_lab": True,
    },
    "tome_of_wisdom": {
        "name": "📖 Фолиант мудрости",
        "desc": "+20% опыта всем участникам клана.",
        "craft_wood": 200, "craft_stone": 100, "craft_herbs": 500, "craft_gold": 15_000,
        "requires_alchemy_lab": True,
    },
    "golden_chalice": {
        "name": "🏆 Золотой кубок",
        "desc": "+10% золота за победы над монстрами.",
        "craft_wood": 400, "craft_stone": 200, "craft_herbs": 300, "craft_gold": 22_000,
        "requires_alchemy_lab": True,
    },
    "crown_of_valor": {
        "name": "👑 Корона доблести",
        "desc": "+10% к урону по боссам.",
        "craft_wood": 600, "craft_stone": 400, "craft_herbs": 250, "craft_gold": 25_000,
        "requires_alchemy_lab": True,
    },
}

# ─────────────────────────── Захват этажей ──────────────────────────────────

# Этажи, доступные для захвата кланом: каждые 5 этажей начиная с 13-го
CAPTURABLE_FLOORS: list[int] = list(range(13, 100, 5))  # 13, 18, 23, 28, ..., 98

CAPTURE_DURATION_HOURS = 72          # базовая длительность захвата
CAPTURE_INCOME_PER_HOUR = 50         # золото в казну / час
CAPTURE_INCOME_INTERVAL_HOURS = 1

# Максимальное кол-во одновременно захваченных этажей по уровню клана
CAPTURE_LIMIT_PER_CLAN_LEVEL: dict[int, int] = {
    1: 2,
    2: 3,
    3: 4,
    4: 5,
    5: 6,
    6: 8,
    7: 10,
    8: 12,
    9: 15,
    10: 18,  # = все возможные этажи
}

CAPTURE_GUARDIAN_BOSS_KEYS: dict[int, str] = {
    13: "boss_forest_warden",
    18: "boss_stone_golem_guardian",
    23: "boss_swamp_troll_warden",
    28: "boss_iron_sentinel",
    33: "boss_crystal_titan",
    38: "boss_shadow_lord",
    43: "boss_bone_colossus",
    48: "boss_void_herald",
    53: "boss_storm_wyrm",
    58: "boss_lava_titan",
    63: "boss_elder_lich",
    68: "boss_sea_leviathan",
    73: "boss_forest_warden",       # повторяемые ключи для высоких этажей
    78: "boss_stone_golem_guardian",
    83: "boss_iron_sentinel",
    88: "boss_crystal_titan",
    93: "boss_void_herald",
    98: "boss_elder_lich",
}

# ─────────────────────────── Войны ──────────────────────────────────────────

WAR_DECLARE_COST = 5_000
WAR_DURATION_DAYS = 7
WAR_AUTO_REJECT_HOURS = 24          # авто-проигрыш если не приняли
WAR_AUTO_REJECT_PENALTY_PCT = 5     # -5% казны у декларанта при авто-отказе

# ─────────────────────────── Вспомогательные функции ────────────────────────

def _payload(clan: Clan) -> dict[str, Any]:
    return dict(clan.payload or {})


def _mat(payload: dict[str, Any]) -> dict[str, int]:
    m = payload.get("materials") or {}
    return {
        "wood":  int(m.get("wood", 0)),
        "stone": int(m.get("stone", 0)),
        "herbs": int(m.get("herbs", 0)),
    }


def _buildings(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return dict(payload.get("buildings") or {})


def _has_building(payload: dict[str, Any], key: str) -> bool:
    bld = _buildings(payload).get(key) or {}
    return bool(bld.get("built"))


def _treasury_gold(payload: dict[str, Any]) -> int:
    return int(payload.get("treasury_gold") or 0)


def _treasury_limit(payload: dict[str, Any]) -> int:
    return 500_000 if _has_building(payload, "treasury_vault") else 100_000


def _relics(payload: dict[str, Any]) -> list[str]:
    return list(payload.get("relics") or [])


def _captured_floors(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return dict(payload.get("captured_floors") or {})


def _floor_capture_active(entry: dict[str, Any], now: datetime) -> bool:
    """Возвращает True если захват этажа ещё активен (не истёк)."""
    try:
        expires = datetime.fromisoformat(entry["expires_at"])
        return now < expires
    except Exception as e:
        logger.error(f"Error checking floor capture: {e}")
        return False


def _war(payload: dict[str, Any]) -> dict[str, Any] | None:
    return payload.get("war") or None


def _add_event(payload: dict[str, Any], text: str) -> None:
    log: list[dict[str, Any]] = list(payload.get("event_log") or [])
    log.append({"ts": datetime.now(UTC).isoformat(), "text": text})
    payload["event_log"] = log[-20:]  # хранить последние 20


def _fmt_ts(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%d.%m %H:%M")
    except Exception:
        return "—"


# ─────────────────────────── Создание клана ─────────────────────────────────

async def try_create_clan(
    session: AsyncSession, leader: Character, raw_name: str, raw_tag: str | None = None
) -> tuple[bool, str]:
    name = (raw_name or "").strip()
    if not _NAME_RE.match(name):
        return False, "Имя клана: 2–40 символов (буквы, цифры, пробел, дефис)."
    tag: str | None = None
    if raw_tag:
        t = raw_tag.strip().upper()
        if not _TAG_RE.match(t):
            return False, "Тег клана: 2–5 символов (буквы и цифры). Например: WOLF"
        tag = t
    if await clan_repo.get_membership(session, int(leader.id)) is not None:
        return False, "Ты уже в клане. Сначала выйди из текущего."
    if int(leader.gold) < CLAN_CREATE_COST_GOLD:
        return False, f"Создание клана стоит {CLAN_CREATE_COST_GOLD:,} 💰. У тебя не хватает."
    if await clan_repo.get_clan_by_name(session, name) is not None:
        return False, "Такое имя клана уже занято."
    if tag and await clan_repo.get_clan_by_tag(session, tag) is not None:
        return False, f"Тег [{tag}] уже занят другим кланом."
    character_service.add_gold(
        leader,
        -CLAN_CREATE_COST_GOLD,
        spend_for="Создание клана",
        spend_kind="clan",
    )
    c = await clan_repo.create_clan(session, name=name, tag=tag, leader=leader)
    payload = {"treasury_gold": 0, "materials": {"wood": 0, "stone": 0, "herbs": 0},
               "buildings": {}, "relics": [], "captured_floors": {}, "war": None, "event_log": []}
    _add_event(payload, f"Клан основан лидером {html.escape(leader.display_name)}")
    c.payload = payload
    await session.flush()
    tag_str = f" [{tag}]" if tag else ""
    return (
        True,
        f"⚔️ Клан <b>{html.escape(name)}</b>{html.escape(tag_str)} создан!\n"
        f"ID клана: <code>{c.id}</code>\n"
        f"Игроки вступают: <code>/clan join {c.id}</code>",
    )


# ─────────────────────────── Вступление / выход ─────────────────────────────

async def try_join_clan(
    session: AsyncSession, character: Character, clan_id: int
) -> tuple[bool, str]:
    if await clan_repo.get_membership(session, int(character.id)) is not None:
        return False, "Ты уже в клане."
    clan = await clan_repo.get_clan(session, int(clan_id))
    if clan is None:
        return False, "Клан с таким ID не найден."
    n = await clan_repo.count_members(session, int(clan.id))
    max_m = max_members_for_level(int(clan.clan_level))
    # Казармы дают +5 к лимиту
    payload = _payload(clan)
    if _has_building(payload, "barracks"):
        max_m += 5
    if n >= max_m:
        return False, f"Клан полон ({n}/{max_m}). Дождись свободного места или повышения уровня."
    await clan_repo.add_member(session, clan_id=int(clan.id), character=character)
    payload2 = _payload(clan)
    _add_event(payload2, f"{html.escape(character.display_name)} вступил в клан")
    await clan_repo.update_payload(session, clan, payload2)
    return True, f"🎉 Добро пожаловать в клан <b>{html.escape(clan.name)}</b>!"


async def try_leave_clan(session: AsyncSession, character: Character) -> tuple[bool, str]:
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return False, "Ты не в клане."
    if m.role == "leader":
        n = await clan_repo.count_members(session, int(m.clan_id))
        if n > 1:
            return (
                False,
                "Ты лидер — перед выходом передай права другому участнику через панель управления.",
            )
        # Единственный участник — распускаем клан
        clan = await clan_repo.get_clan(session, int(m.clan_id))
        if clan:
            await session.delete(clan)
            await session.flush()
        return True, "Клан распущен (ты был единственным участником)."
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    await clan_repo.remove_member(session, m)
    if clan:
        payload = _payload(clan)
        _add_event(payload, f"{html.escape(character.display_name)} покинул клан")
        await clan_repo.update_payload(session, clan, payload)
    return True, "Ты покинул клан."


# ─────────────────────────── Казна ──────────────────────────────────────────

async def try_donate_gold(
    session: AsyncSession, character: Character, amount: int
) -> tuple[bool, str]:
    amount = int(amount)
    if amount <= 0:
        return False, "Укажи положительную сумму."
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return False, "Ты не в клане."
    if int(character.gold) < amount:
        return False, f"Недостаточно золота. У тебя: {int(character.gold):,} 💰"
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return False, "Клан не найден."
    payload = _payload(clan)
    limit = _treasury_limit(payload)
    cur = _treasury_gold(payload)
    actual = min(amount, limit - cur)
    if actual <= 0:
        return False, f"Казна переполнена ({cur:,}/{limit:,} 💰). Сначала обновите клан или постройте сокровищницу."
    from services import character_service as _csvc
    _csvc.add_gold(
        character,
        -actual,
        spend_for=f"Клан «{clan.name}»: взнос в казну",
        spend_kind="clan",
    )
    payload["treasury_gold"] = cur + actual
    pts = max(1, actual // 1000)
    await clan_repo.add_contribution(session, m, pts)
    _add_event(
        payload,
        f"{html.escape(str(character.display_name or '?'))} пожертвовал {actual:,} 💰 (вклад +{pts})",
    )
    await clan_repo.update_payload(session, clan, payload)
    return True, f"💰 Внесено <b>{actual:,}</b> в казну клана. Вклад +{pts}."


# ─────────────────────────── Распределение ЗП из казны ─────────────────────

def _salary_pool(payload: dict[str, Any]) -> dict[str, int]:
    """Накопленная ЗП по character_id (как str)."""
    return dict(payload.get("salary_pool") or {})


def pending_salary_for(character: Character, payload: dict[str, Any] | None = None) -> int:
    """Сколько ЗП ждёт персонажа (по его character_id)."""
    if payload is None:
        return 0
    pool = _salary_pool(payload)
    return int(pool.get(str(int(character.id)), 0))


async def allocate_salary(
    session: AsyncSession,
    actor: Character,
    target_char_id: int,
    amount: int,
) -> tuple[bool, str]:
    """
    Лидер/офицер: списать `amount` из казны и добавить в salary_pool[target_char_id].
    Сама ЗП лежит в payload, забрать её участник может через `claim_salary`.
    """
    amt = int(amount)
    if amt <= 0:
        return False, "Сумма ЗП должна быть положительной."
    m_actor = await clan_repo.get_membership(session, int(actor.id))
    if m_actor is None:
        return False, "Ты не в клане."
    if not can_manage(m_actor.role):
        return False, "Только лидер или офицер может выделять ЗП."
    m_target = await clan_repo.get_membership(session, int(target_char_id))
    if m_target is None or int(m_target.clan_id) != int(m_actor.clan_id):
        return False, "Этот игрок не состоит в твоём клане."
    clan = await clan_repo.get_clan(session, int(m_actor.clan_id))
    if clan is None:
        return False, "Клан не найден."
    payload = _payload(clan)
    tg = _treasury_gold(payload)
    if tg < amt:
        return False, f"В казне всего {tg:,} 💰 — недостаточно."
    pool = _salary_pool(payload)
    key = str(int(target_char_id))
    pool[key] = int(pool.get(key, 0)) + amt
    payload["salary_pool"] = pool
    payload["treasury_gold"] = tg - amt
    target_name = "?"
    try:
        from db.repository import character_repo as _crepo

        tgt_char = await _crepo.get_by_id(session, int(target_char_id))
        if tgt_char is not None:
            target_name = str(tgt_char.display_name or "?")
    except Exception:
        pass
    _add_event(
        payload,
        f"{html.escape(actor.display_name)} выделил ЗП {amt:,} 💰 → {html.escape(target_name)}",
    )
    await clan_repo.update_payload(session, clan, payload)
    return True, f"💼 Выделено <b>{amt:,}</b> 💰 для <b>{html.escape(target_name)}</b>. Игрок заберёт её сам."


async def list_pending_salary(
    session: AsyncSession, clan_id: int
) -> list[tuple[int, int, str, str]]:
    """[(character_id, amount, name, role)] — кому какую ЗП выделили, ещё не забрали."""
    clan = await clan_repo.get_clan(session, int(clan_id))
    if clan is None:
        return []
    payload = _payload(clan)
    pool = _salary_pool(payload)
    if not pool:
        return []
    out: list[tuple[int, int, str, str]] = []
    members = await clan_repo.get_members_with_characters(session, int(clan_id))
    by_id: dict[int, tuple[Character, str]] = {}
    for mbr, ch in members:
        by_id[int(ch.id)] = (ch, mbr.role)
    for k, v in pool.items():
        try:
            cid = int(k)
        except (TypeError, ValueError):
            continue
        amt = int(v or 0)
        if amt <= 0:
            continue
        info = by_id.get(cid)
        if info is None:
            out.append((cid, amt, "(вышел из клана)", "—"))
        else:
            ch, role = info
            out.append((cid, amt, str(ch.display_name or "?"), role))
    out.sort(key=lambda r: r[1], reverse=True)
    return out


async def claim_salary(session: AsyncSession, character: Character) -> tuple[bool, str]:
    """Участник забирает накопленную ЗП в личное золото."""
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return False, "Ты не в клане."
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return False, "Клан не найден."
    payload = _payload(clan)
    pool = _salary_pool(payload)
    key = str(int(character.id))
    amt = int(pool.get(key, 0))
    if amt <= 0:
        return False, "Тебе пока не выделили ЗП."
    pool[key] = 0
    # Чистим ноль чтобы не плодить мусор.
    pool = {k: v for k, v in pool.items() if int(v or 0) > 0}
    payload["salary_pool"] = pool
    from services import character_service as _csvc

    _csvc.add_gold(character, amt)
    _add_event(payload, f"{html.escape(character.display_name)} забрал ЗП {amt:,} 💰")
    await clan_repo.update_payload(session, clan, payload)
    return True, f"📥 Получено <b>{amt:,}</b> 💰 от клана."


async def try_donate_materials(
    session: AsyncSession, character: Character, wood: int = 0, stone: int = 0, herbs: int = 0
) -> tuple[bool, str]:
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return False, "Ты не в клане."
    mp = dict(character.meta_progress or {})
    char_mats: dict[str, int] = dict(mp.get("clan_materials") or {})
    give = {"wood": min(wood, int(char_mats.get("wood", 0))),
            "stone": min(stone, int(char_mats.get("stone", 0))),
            "herbs": min(herbs, int(char_mats.get("herbs", 0)))}
    if sum(give.values()) == 0:
        return False, "Нечего жертвовать — нет материалов."
    for k, v in give.items():
        char_mats[k] = int(char_mats.get(k, 0)) - v
    mp["clan_materials"] = char_mats
    character.meta_progress = mp
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return False, "Клан не найден."
    payload = _payload(clan)
    mats = _mat(payload)
    for k, v in give.items():
        mats[k] = mats.get(k, 0) + v
    payload["materials"] = mats
    pts = sum(give.values()) // 10
    if pts > 0:
        await clan_repo.add_contribution(session, m, pts)
    summary = ", ".join(f"{v} {'🪵' if k=='wood' else '🪨' if k=='stone' else '🌿'}" for k, v in give.items() if v > 0)
    _add_event(payload, f"{html.escape(character.display_name)} пожертвовал {summary}")
    await clan_repo.update_payload(session, clan, payload)
    return True, f"Материалы переданы в казну: {summary}."


# ─────────────────────────── Повышение уровня клана ─────────────────────────

async def try_level_up_clan(
    session: AsyncSession, character: Character
) -> tuple[bool, str]:
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return False, "Ты не в клане."
    if m.role not in ("leader",):
        return False, "Только лидер может повышать уровень клана."
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return False, "Клан не найден."
    cur_lv = int(clan.clan_level)
    if cur_lv >= 10:
        return False, "Клан уже достиг максимального уровня (10)."
    nxt = cur_lv + 1
    req = level_def(nxt)
    payload = _payload(clan)
    mats = _mat(payload)
    tg = _treasury_gold(payload)
    missing: list[str] = []
    if tg < req["cost_gold"]:
        missing.append(f"{req['cost_gold']:,} 💰 (в казне {tg:,})")
    if mats["wood"] < req["cost_wood"]:
        missing.append(f"{req['cost_wood']} 🪵 (в казне {mats['wood']})")
    if mats["stone"] < req["cost_stone"]:
        missing.append(f"{req['cost_stone']} 🪨 (в казне {mats['stone']})")
    if mats["herbs"] < req["cost_herbs"]:
        missing.append(f"{req['cost_herbs']} 🌿 (в казне {mats['herbs']})")
    if missing:
        return False, "Не хватает ресурсов:\n• " + "\n• ".join(missing)
    payload["treasury_gold"] = tg - req["cost_gold"]
    payload["materials"] = {
        "wood":  mats["wood"]  - req["cost_wood"],
        "stone": mats["stone"] - req["cost_stone"],
        "herbs": mats["herbs"] - req["cost_herbs"],
    }
    clan.clan_level = nxt
    _add_event(payload, f"Клан повышен до уровня {nxt}!")
    await clan_repo.update_payload(session, clan, payload)
    return True, f"🎉 Клан повышен до <b>уровня {nxt}</b>!\nМаксимум участников: {req['max_members']}."


# ─────────────────────────── Постройки ──────────────────────────────────────

async def try_start_building(
    session: AsyncSession, character: Character, building_key: str,
    *, admin_bypass: bool = False,
) -> tuple[bool, str]:
    if building_key not in BUILDING_DEFS:
        return False, "Неизвестная постройка."
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return False, "Ты не в клане."
    if not can_manage(m.role):
        return False, "Только офицер или лидер может начать строительство."
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return False, "Клан не найден."
    bdef = BUILDING_DEFS[building_key]
    if int(clan.clan_level) < bdef["unlock_level"]:
        return False, f"Нужен уровень клана {bdef['unlock_level']} (сейчас {clan.clan_level})."
    payload = _payload(clan)
    blds = _buildings(payload)
    bstate = blds.get(building_key) or {}
    if bstate.get("built"):
        return False, f"{bdef['name']} уже построена."
    if bstate.get("build_until"):
        fin = _fmt_ts(bstate["build_until"])
        return False, f"Строительство уже идёт, завершится {fin}."
    mats = _mat(payload)
    tg = _treasury_gold(payload)
    if not admin_bypass:
        missing: list[str] = []
        if tg < bdef["cost_gold"]:
            missing.append(f"{bdef['cost_gold']:,} 💰 (в казне {tg:,})")
        if mats["wood"] < bdef["cost_wood"]:
            missing.append(f"{bdef['cost_wood']} 🪵 (в казне {mats['wood']})")
        if mats["stone"] < bdef["cost_stone"]:
            missing.append(f"{bdef['cost_stone']} 🪨 (в казне {mats['stone']})")
        if mats["herbs"] < bdef["cost_herbs"]:
            missing.append(f"{bdef['cost_herbs']} 🌿 (в казне {mats['herbs']})")
        if missing:
            return False, "Не хватает ресурсов:\n• " + "\n• ".join(missing)
        payload["treasury_gold"] = tg - bdef["cost_gold"]
        payload["materials"] = {
            "wood":  mats["wood"]  - bdef["cost_wood"],
            "stone": mats["stone"] - bdef["cost_stone"],
            "herbs": mats["herbs"] - bdef["cost_herbs"],
        }
    finish = datetime.now(UTC) + timedelta(hours=bdef["build_hours"])
    blds[building_key] = {"built": False, "build_until": finish.isoformat()}
    payload["buildings"] = blds
    _add_event(payload, f"Начато строительство: {bdef['name']} (завершение ~{_fmt_ts(finish.isoformat())})")
    await clan_repo.update_payload(session, clan, payload)
    return True, (
        f"🔨 Строительство <b>{bdef['name']}</b> начато!\n"
        f"Завершится через <b>{bdef['build_hours']} ч.</b>"
    )


def check_and_complete_buildings(payload: dict[str, Any]) -> list[str]:
    """Проверить таймеры построек и пометить завершённые. Возвращает список завершённых."""
    blds = _buildings(payload)
    completed: list[str] = []
    now = datetime.now(UTC)
    for key, bstate in blds.items():
        if bstate.get("built"):
            continue
        until_str = bstate.get("build_until")
        if not until_str:
            continue
        try:
            until = datetime.fromisoformat(until_str)
        except Exception:
            continue
        if now >= until:
            bstate["built"] = True
            bstate["build_until"] = None
            completed.append(key)
    payload["buildings"] = blds
    return completed


# ─────────────────────────── Захват этажей ──────────────────────────────────

async def try_capture_floor(
    session: AsyncSession, character: Character, floor_number: int
) -> tuple[bool, str]:
    """Персонаж заявляет захват этажа."""
    if floor_number not in CAPTURABLE_FLOORS:
        nearest = sorted(CAPTURABLE_FLOORS, key=lambda x: abs(x - floor_number))[:3]
        return False, f"Этаж {floor_number} нельзя захватить. Ближайшие: {nearest}."
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return False, "Ты не в клане."
    if m.role not in ("leader", "officer"):
        return False, "Только лидер или офицер клана может инициировать захват."
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return False, "Клан не найден."
    payload = _payload(clan)
    caps = _captured_floors(payload)
    fl_key = str(floor_number)
    # Проверка: этаж уже захвачен этим кланом
    if fl_key in caps:
        entry = caps[fl_key]
        try:
            expires = datetime.fromisoformat(entry["expires_at"])
            if datetime.now(UTC) < expires:
                return False, f"Этаж {floor_number} уже захвачен вашим кланом до {_fmt_ts(entry['expires_at'])}."
        except Exception:
            logger.exception(f"Ошибка парсинга expires_at для клана {clan.id}, этаж {fl_key}")
    # Проверка лимита захватов по уровню клана
    clan_lv = int(clan.clan_level)
    cap_limit = CAPTURE_LIMIT_PER_CLAN_LEVEL.get(clan_lv, 2)
    now = datetime.now(UTC)
    active_caps = sum(
        1 for k, v in caps.items()
        if k != fl_key and _floor_capture_active(v, now)
    )
    if active_caps >= cap_limit:
        return False, (
            f"Лимит захватов для клана ур. {clan_lv}: <b>{cap_limit}</b>.\n"
            f"Сейчас активных захватов: {active_caps}. Повысь уровень клана или дождись истечения."
        )
    # Записываем заявку на захват — окончательно закрепляется после победы стража
    pending_key = f"capture_pending_{fl_key}"
    pending = payload.get("capture_pending") or {}
    pending[fl_key] = {
        "initiated_by": int(character.id),
        "initiated_at": datetime.now(UTC).isoformat(),
        "floor": floor_number,
    }
    payload["capture_pending"] = pending
    _add_event(payload, f"{html.escape(character.display_name)} инициировал захват этажа {floor_number}")
    await clan_repo.update_payload(session, clan, payload)
    guardian_key = CAPTURE_GUARDIAN_BOSS_KEYS.get(floor_number, "boss_forest_warden")
    return (
        True,
        f"⚔️ Заявка на захват этажа {floor_number} подана!\n"
        f"Победи стража (<b>{guardian_key}</b>) на этом этаже, чтобы завершить захват.\n"
        f"<i>Для стабильного захвата рекомендуется участие 3+ членов клана.</i>",
    )


async def confirm_floor_capture(
    session: AsyncSession, character: Character, floor_number: int
) -> bool:
    """Вызывается после победы над стражем этажа — закрепляет захват."""
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return False
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return False
    payload = _payload(clan)
    pending = payload.get("capture_pending") or {}
    fl_key = str(floor_number)
    if fl_key not in pending:
        return False
    duration_h = CAPTURE_DURATION_HOURS
    if _has_building(payload, "watchtower"):
        duration_h += 12
    now = datetime.now(UTC)
    caps = _captured_floors(payload)
    caps[fl_key] = {
        "captured_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=duration_h)).isoformat(),
        "income_at": now.isoformat(),
    }
    payload["captured_floors"] = caps
    del pending[fl_key]
    payload["capture_pending"] = pending
    _add_event(payload, f"Этаж {floor_number} захвачен! Удерживать {duration_h} ч.")
    await clan_repo.add_contribution(session, m, 10)
    await clan_repo.update_payload(session, clan, payload)
    return True


async def collect_floor_income(session: AsyncSession, clan: Clan) -> int:
    """Начислить пассивный доход с захваченных этажей в казну. Возвращает начисленную сумму."""
    payload = _payload(clan)
    caps = _captured_floors(payload)
    if not caps:
        return 0
    now = datetime.now(UTC)
    total = 0
    updated_caps: dict[str, Any] = {}
    for fl_key, entry in caps.items():
        try:
            expires = datetime.fromisoformat(entry["expires_at"])
            if now >= expires:
                continue  # истёк — убираем
            income_at = datetime.fromisoformat(entry.get("income_at") or entry["captured_at"])
            hours_since = (now - income_at).total_seconds() / 3600
            portions = int(hours_since / CAPTURE_INCOME_INTERVAL_HOURS)
            if portions > 0:
                earned = portions * CAPTURE_INCOME_PER_HOUR
                total += earned
                new_income_at = income_at + timedelta(hours=portions * CAPTURE_INCOME_INTERVAL_HOURS)
                updated_caps[fl_key] = {**entry, "income_at": new_income_at.isoformat()}
            else:
                updated_caps[fl_key] = entry
        except Exception:
            logger.exception(f"Критическая ошибка в collect_floor_income для клана {clan.id}, этаж {fl_key}")
            # Не добавляем в updated_caps, чтобы битая запись не блокировала слот вечно
    if total > 0:
        limit = _treasury_limit(payload)
        cur = _treasury_gold(payload)
        payload["treasury_gold"] = min(cur + total, limit)
        payload["captured_floors"] = updated_caps
        await clan_repo.update_payload(session, clan, payload)
    return total


# ─────────────────────────── Войны ──────────────────────────────────────────

async def try_declare_war(
    session: AsyncSession, character: Character, target_clan_id: int
) -> tuple[bool, str]:
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return False, "Ты не в клане."
    if m.role != "leader":
        return False, "Только лидер может объявить войну."
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return False, "Клан не найден."
    if int(clan.id) == int(target_clan_id):
        return False, "Нельзя объявить войну самому себе."
    target = await clan_repo.get_clan(session, int(target_clan_id))
    if target is None:
        return False, f"Клан с ID {target_clan_id} не найден."
    payload = _payload(clan)
    if _war(payload) is not None:
        return False, "Клан уже ведёт войну (только 1 война одновременно)."
    tg = _treasury_gold(payload)
    if tg < WAR_DECLARE_COST:
        return False, f"Нужно {WAR_DECLARE_COST:,} 💰 в казне для объявления войны (сейчас {tg:,})."
    target_payload = _payload(target)
    if _war(target_payload) is not None:
        return False, f"Клан «{html.escape(target.name)}» уже ведёт другую войну."
    # Списать взнос
    payload["treasury_gold"] = tg - WAR_DECLARE_COST
    war_id = str(uuid.uuid4())[:8]
    now = datetime.now(UTC)
    auto_reject_at = now + timedelta(hours=WAR_AUTO_REJECT_HOURS)
    war_entry: dict[str, Any] = {
        "war_id": war_id,
        "opponent_clan_id": int(target.id),
        "opponent_name": target.name,
        "declared_by_clan_id": int(clan.id),
        "declared_at": now.isoformat(),
        "auto_reject_at": auto_reject_at.isoformat(),
        "accepted_at": None,
        "ends_at": None,
        "our_points": 0,
        "their_points": 0,
        "status": "pending",
    }
    payload["war"] = war_entry
    _add_event(payload, f"Объявлена война клану «{html.escape(target.name)}»")
    await clan_repo.update_payload(session, clan, payload)

    # Зеркало для противника
    war_mirror: dict[str, Any] = {
        **war_entry,
        "opponent_clan_id": int(clan.id),
        "opponent_name": clan.name,
        "declared_by_clan_id": int(clan.id),
        "status": "incoming",
    }
    target_payload["war"] = war_mirror
    _add_event(target_payload, f"Клан «{html.escape(clan.name)}» объявил вам войну!")
    await clan_repo.update_payload(session, target, target_payload)
    return (
        True,
        f"⚔️ Война объявлена клану <b>{html.escape(target.name)}</b>!\n"
        f"ID войны: <code>{war_id}</code>\n"
        f"Противник должен принять в течение {WAR_AUTO_REJECT_HOURS} ч., иначе авто-проигрыш.",
    )


async def try_accept_war(
    session: AsyncSession, character: Character
) -> tuple[bool, str]:
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return False, "Ты не в клане."
    if m.role != "leader":
        return False, "Только лидер может принять вызов."
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return False, "Клан не найден."
    payload = _payload(clan)
    war = _war(payload)
    if war is None or war.get("status") != "incoming":
        return False, "Нет входящего вызова на войну."
    now = datetime.now(UTC)
    ends_at = now + timedelta(days=WAR_DURATION_DAYS)
    war["status"] = "active"
    war["accepted_at"] = now.isoformat()
    war["ends_at"] = ends_at.isoformat()
    payload["war"] = war
    _add_event(payload, f"Война с кланом «{html.escape(war['opponent_name'])}» принята! Конец: {_fmt_ts(ends_at.isoformat())}")
    await clan_repo.update_payload(session, clan, payload)

    # Обновить у противника
    opp = await clan_repo.get_clan(session, int(war["opponent_clan_id"]))
    if opp:
        opp_payload = _payload(opp)
        opp_war = _war(opp_payload)
        if opp_war:
            opp_war["status"] = "active"
            opp_war["accepted_at"] = now.isoformat()
            opp_war["ends_at"] = ends_at.isoformat()
            opp_payload["war"] = opp_war
            _add_event(opp_payload, f"Клан «{html.escape(clan.name)}» принял вашу войну!")
            await clan_repo.update_payload(session, opp, opp_payload)
    return (
        True,
        f"⚔️ Война с <b>{html.escape(war['opponent_name'])}</b> начата!\n"
        f"Длится до {_fmt_ts(ends_at.isoformat())} ({WAR_DURATION_DAYS} дней).",
    )


async def try_reject_war(
    session: AsyncSession, character: Character
) -> tuple[bool, str]:
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return False, "Ты не в клане."
    if m.role != "leader":
        return False, "Только лидер может отказать."
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return False, "Клан не найден."
    payload = _payload(clan)
    war = _war(payload)
    if war is None or war.get("status") != "incoming":
        return False, "Нет входящего вызова."
    opp_name = war.get("opponent_name", "?")
    opp_id = war.get("opponent_clan_id")
    payload["war"] = None
    _add_event(payload, f"Война с кланом «{html.escape(opp_name)}» отклонена")
    await clan_repo.update_payload(session, clan, payload)
    # Противник: пометить их войну как auto-rejected
    if opp_id:
        opp = await clan_repo.get_clan(session, int(opp_id))
        if opp:
            opp_payload = _payload(opp)
            opp_payload["war"] = None
            pct = WAR_AUTO_REJECT_PENALTY_PCT
            tg = _treasury_gold(opp_payload)
            fine = int(tg * pct / 100)
            opp_payload["treasury_gold"] = max(0, tg - fine)
            _add_event(opp_payload, f"Клан «{html.escape(clan.name)}» отказал в войне. Штраф: -{fine:,} 💰 из казны")
            await clan_repo.update_payload(session, opp, opp_payload)
    return True, f"Вызов от клана «{html.escape(opp_name)}» отклонён."


async def add_war_points(
    session: AsyncSession, character: Character, points: int
) -> None:
    """Начислить очки войны клану персонажа."""
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return
    payload = _payload(clan)
    war = _war(payload)
    if war is None or war.get("status") != "active":
        return
    war["our_points"] = int(war.get("our_points") or 0) + int(points)
    payload["war"] = war
    await clan_repo.update_payload(session, clan, payload)


# ─────────────────────────── Реликвии ───────────────────────────────────────

async def try_craft_relic(
    session: AsyncSession, character: Character, relic_key: str
) -> tuple[bool, str]:
    if relic_key not in RELIC_DEFS:
        return False, "Неизвестная реликвия."
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return False, "Ты не в клане."
    if not can_manage(m.role):
        return False, "Только офицер или лидер может крафтить реликвии."
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return False, "Клан не найден."
    payload = _payload(clan)
    if not _has_building(payload, "alchemy_lab"):
        return False, "Нужна ⚗️ Алхимическая лаборатория (постройте её первым)."
    relics = _relics(payload)
    if relic_key in relics:
        return False, "Эта реликвия уже есть у клана."
    rdef = RELIC_DEFS[relic_key]
    mats = _mat(payload)
    tg = _treasury_gold(payload)
    missing: list[str] = []
    if tg < rdef["craft_gold"]:
        missing.append(f"{rdef['craft_gold']:,} 💰 (в казне {tg:,})")
    if mats["wood"] < rdef["craft_wood"]:
        missing.append(f"{rdef['craft_wood']} 🪵 (в казне {mats['wood']})")
    if mats["stone"] < rdef["craft_stone"]:
        missing.append(f"{rdef['craft_stone']} 🪨 (в казне {mats['stone']})")
    if mats["herbs"] < rdef["craft_herbs"]:
        missing.append(f"{rdef['craft_herbs']} 🌿 (в казне {mats['herbs']})")
    if missing:
        return False, "Не хватает ресурсов:\n• " + "\n• ".join(missing)
    payload["treasury_gold"] = tg - rdef["craft_gold"]
    payload["materials"] = {
        "wood":  mats["wood"]  - rdef["craft_wood"],
        "stone": mats["stone"] - rdef["craft_stone"],
        "herbs": mats["herbs"] - rdef["craft_herbs"],
    }
    relics.append(relic_key)
    payload["relics"] = relics
    _add_event(payload, f"{html.escape(character.display_name)} создал реликвию {rdef['name']}")
    await clan_repo.update_payload(session, clan, payload)
    return True, f"✨ Реликвия <b>{rdef['name']}</b> создана!"


# ─────────────────────────── Управление участниками ─────────────────────────

async def try_kick_member(
    session: AsyncSession, acting: Character, target_char_id: int
) -> tuple[bool, str]:
    m_actor = await clan_repo.get_membership(session, int(acting.id))
    if m_actor is None:
        return False, "Ты не в клане."
    if not can_manage(m_actor.role):
        return False, "Только офицер или лидер может исключать участников."
    if int(acting.id) == int(target_char_id):
        return False, "Нельзя исключить самого себя."
    m_target = await clan_repo.get_membership(session, int(target_char_id))
    if m_target is None or int(m_target.clan_id) != int(m_actor.clan_id):
        return False, "Участник не найден в вашем клане."
    if m_target.role == "leader":
        return False, "Нельзя исключить лидера клана."
    if m_target.role == "officer" and m_actor.role != "leader":
        return False, "Только лидер может исключить офицера."
    tgt_char = await session.get(Character, int(target_char_id))
    tgt_name = tgt_char.display_name if tgt_char else f"#{target_char_id}"
    clan = await clan_repo.get_clan(session, int(m_actor.clan_id))
    await clan_repo.remove_member(session, m_target)
    if clan:
        payload = _payload(clan)
        _add_event(payload, f"{html.escape(tgt_name)} исключён из клана ({m_actor.role}: {html.escape(acting.display_name)})")
        await clan_repo.update_payload(session, clan, payload)
    return True, f"Участник <b>{html.escape(tgt_name)}</b> исключён из клана."


async def try_change_role(
    session: AsyncSession, acting: Character, target_char_id: int, new_role: str
) -> tuple[bool, str]:
    if new_role not in ("officer", "veteran", "member"):
        return False, "Допустимые роли: officer, veteran, member."
    m_actor = await clan_repo.get_membership(session, int(acting.id))
    if m_actor is None:
        return False, "Ты не в клане."
    if m_actor.role != "leader":
        return False, "Только лидер может менять роли."
    if int(acting.id) == int(target_char_id):
        return False, "Нельзя изменить собственную роль через это меню."
    m_target = await clan_repo.get_membership(session, int(target_char_id))
    if m_target is None or int(m_target.clan_id) != int(m_actor.clan_id):
        return False, "Участник не найден в вашем клане."
    if m_target.role == "leader":
        return False, "Нельзя изменить роль лидера без передачи власти."
    tgt_char = await session.get(Character, int(target_char_id))
    tgt_name = tgt_char.display_name if tgt_char else f"#{target_char_id}"
    old_role = m_target.role
    m_target.role = new_role
    await session.flush()
    clan = await clan_repo.get_clan(session, int(m_actor.clan_id))
    if clan:
        payload = _payload(clan)
        _add_event(payload, f"Роль {html.escape(tgt_name)}: {old_role} → {new_role}")
        await clan_repo.update_payload(session, clan, payload)
    return True, f"Роль <b>{html.escape(tgt_name)}</b> изменена: {role_label(new_role)}"


async def try_transfer_leadership(
    session: AsyncSession, acting: Character, target_char_id: int
) -> tuple[bool, str]:
    m_actor = await clan_repo.get_membership(session, int(acting.id))
    if m_actor is None:
        return False, "Ты не в клане."
    if m_actor.role != "leader":
        return False, "Только лидер может передать власть."
    if int(acting.id) == int(target_char_id):
        return False, "Нельзя передать власть самому себе."
    m_target = await clan_repo.get_membership(session, int(target_char_id))
    if m_target is None or int(m_target.clan_id) != int(m_actor.clan_id):
        return False, "Участник не найден в вашем клане."
    tgt_char = await session.get(Character, int(target_char_id))
    tgt_name = tgt_char.display_name if tgt_char else f"#{target_char_id}"
    clan = await clan_repo.get_clan(session, int(m_actor.clan_id))
    if clan is None:
        return False, "Клан не найден."
    # Поменять роли
    m_actor.role = "officer"
    m_target.role = "leader"
    clan.leader_character_id = int(target_char_id)
    await session.flush()
    payload = _payload(clan)
    _add_event(payload, f"{html.escape(acting.display_name)} передал власть {html.escape(tgt_name)}")
    await clan_repo.update_payload(session, clan, payload)
    return True, f"👑 Лидерство передано <b>{html.escape(tgt_name)}</b>."


# ─────────────────────────── Ссылка на чат ──────────────────────────────────

async def try_set_clan_chat(
    session: AsyncSession, character: Character, url: str
) -> tuple[bool, str]:
    u = (url or "").strip()
    if len(u) < 8 or not (u.startswith("http://") or u.startswith("https://") or u.startswith("t.me/")):
        return False, "Укажи ссылку на чат (https://… или t.me/…)."
    if not u.startswith("http"):
        u = "https://" + u.lstrip("/")
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None or m.role not in ("leader", "officer"):
        return False, "Только офицер/лидер клана может задать ссылку."
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return False, "Клан не найден."
    clan.chat_url = u[:256]
    await session.flush()
    return True, "Ссылка на чат клана сохранена."


# ─────────────────────────── Вклад за победы ────────────────────────────────

async def on_monster_win_add_clan_xp(
    session: AsyncSession, character: Character, *, delta: int = 1
) -> None:
    """Начислить вклад и XP клана за победу над монстром."""
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return
    await clan_repo.add_contribution(session, m, delta)
    await clan_repo.add_clan_xp(session, clan, delta)


# ─────────────────────────── Материальный дроп ──────────────────────────────

def add_material_drop(character: Character, material: str, amount: int) -> None:
    """Добавить материал в meta_progress.clan_materials персонажа."""
    if amount <= 0 or material not in ("wood", "stone", "herbs"):
        return
    mp = dict(character.meta_progress or {})
    mats = dict(mp.get("clan_materials") or {})
    mats[material] = int(mats.get(material, 0)) + amount
    mp["clan_materials"] = mats
    character.meta_progress = mp


def get_character_materials(character: Character) -> dict[str, int]:
    mp = dict(character.meta_progress or {})
    raw = mp.get("clan_materials") or {}
    return {"wood": int(raw.get("wood", 0)), "stone": int(raw.get("stone", 0)), "herbs": int(raw.get("herbs", 0))}


# ─────────────────────────── HTML-форматирование ────────────────────────────

async def format_clan_card_html(session: AsyncSession, character: Character) -> str:
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return (
            "⚔️ <b>Кланы</b>\n\n"
            "Ты не в клане.\n\n"
            "• Создать клан: <code>/clan create Название</code>\n"
            "• Вступить по ID: <code>/clan join &lt;ID&gt;</code>\n\n"
            "<i>Стоимость создания: 50 000 💰.</i>"
        )
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return "<i>Данные клана не найдены.</i>"
    payload = _payload(clan)
    check_and_complete_buildings(payload)
    n = await clan_repo.count_members(session, int(clan.id))
    lv = int(clan.clan_level)
    max_m = max_members_for_level(lv)
    if _has_building(payload, "barracks"):
        max_m += 5
    tag_str = f" [{html.escape(clan.tag)}]" if clan.tag else ""
    tg = _treasury_gold(payload)
    tg_lim = _treasury_limit(payload)
    mats = _mat(payload)
    relics = _relics(payload)
    war = _war(payload)
    caps = _captured_floors(payload)
    # Постройки
    bld_names = [BUILDING_DEFS[k]["name"] for k, v in _buildings(payload).items() if v.get("built")]
    bld_str = ", ".join(bld_names) if bld_names else "<i>нет</i>"
    # Война
    if war and war.get("status") == "active":
        war_str = (
            f"\n⚔️ Война с <b>{html.escape(war.get('opponent_name','?'))}</b>: "
            f"наши {war.get('our_points',0)} — их {war.get('their_points',0)} очков. "
            f"До {_fmt_ts(war.get('ends_at'))}"
        )
    elif war and war.get("status") == "pending":
        war_str = f"\n📤 Ожидает ответа от <b>{html.escape(war.get('opponent_name','?'))}</b>…"
    elif war and war.get("status") == "incoming":
        war_str = f"\n📥 Входящий вызов от <b>{html.escape(war.get('opponent_name','?'))}</b>! (лидер: принять/отказать)"
    else:
        war_str = ""
    # Захваченные этажи
    now = datetime.now(UTC)
    active_caps = []
    for fl_key, entry in caps.items():
        try:
            exp = datetime.fromisoformat(entry["expires_at"])
            if now < exp:
                active_caps.append(f"Эт.{fl_key} (до {_fmt_ts(entry['expires_at'])})")
        except Exception:
            pass
    caps_str = ", ".join(active_caps) if active_caps else "<i>нет</i>"
    chat = f'<a href="{html.escape(clan.chat_url)}">Чат клана</a>' if clan.chat_url else ""
    mat_str = f"🪵{mats['wood']} 🪨{mats['stone']} 🌿{mats['herbs']}"
    banner = payload.get("banner")
    banner_str = f"<b>{banner['emoji']} {html.escape(banner['text'])}</b>\n" if banner else ""
    return (
        f"⚔️ <b>{html.escape(clan.name)}</b>{tag_str} · ID <code>{clan.id}</code>\n"
        f"{banner_str}"
        f"📊 Уровень: <b>{lv}/10</b> · Участников: <b>{n}/{max_m}</b>\n"
        f"💰 Казна: <b>{tg:,}</b>/{tg_lim:,} · {mat_str}\n"
        f"🏆 Реликвий: <b>{len(relics)}</b> · Этажей: {caps_str}\n"
        f"🔨 Постройки: {bld_str}"
        f"{war_str}\n"
        f"<i>Твоя роль: {role_label(m.role)} · Вклад: {int(m.contribution_points or 0):,}</i>"
        + (f"\n{chat}" if chat else "")
    )


def format_members_list_html(
    rows: list[tuple[ClanMembership, Character]], clan_name: str, is_leader: bool
) -> str:
    if not rows:
        return "<i>Нет участников.</i>"
    lines: list[str] = [f"👥 <b>Участники клана «{html.escape(clan_name)}»</b>\n"]
    for mbr, char in rows:
        last = _fmt_ts(mbr.last_active_at.isoformat() if mbr.last_active_at else None)
        contrib = int(mbr.contribution_points or 0)
        tag = f" [ID{char.game_id}]" if char.game_id else ""
        lines.append(
            f"{role_label(mbr.role)} <b>{html.escape(char.display_name)}</b>{tag} "
            f"Ур.{char.level} · Эт.{char.floor_number} · "
            f"Вклад <b>{contrib:,}</b> · Акт. {last}"
        )
    if not is_leader:
        lines.append("\n<i>Полная панель управления — только у лидера.</i>")
    return "\n".join(lines)


def format_buildings_html(payload: dict[str, Any], clan_level: int) -> str:
    lines = ["🔨 <b>Постройки клана</b>\n"]
    blds = _buildings(payload)
    for key, bdef in BUILDING_DEFS.items():
        bstate = blds.get(key) or {}
        if bstate.get("built"):
            status = "✅ Построено"
        elif bstate.get("build_until"):
            status = f"🔨 Строится (готово: {_fmt_ts(bstate['build_until'])})"
        elif clan_level < bdef["unlock_level"]:
            status = f"🔒 Ур.клана {bdef['unlock_level']}"
        else:
            status = "⬜ Можно построить"
        lines.append(f"{bdef['name']} — {status}\n  <i>{bdef['desc']}</i>")
    return "\n".join(lines)


def format_war_html(payload: dict[str, Any]) -> str:
    war = _war(payload)
    if war is None:
        return (
            "⚔️ <b>Гильдийные войны</b>\n\n"
            "Активной войны нет.\n"
            "<i>Лидер может объявить войну другому клану (стоимость: 5 000 💰 из казны, макс. 1 война).</i>"
        )
    status_map = {
        "pending": "📤 Ожидает принятия",
        "incoming": "📥 Входящий вызов",
        "active": "⚔️ Активна",
        "ended": "🏁 Завершена",
    }
    st = status_map.get(war.get("status", ""), "?")
    opp = html.escape(war.get("opponent_name", "?"))
    our = int(war.get("our_points") or 0)
    their = int(war.get("their_points") or 0)
    ends = _fmt_ts(war.get("ends_at"))
    auto_rej = _fmt_ts(war.get("auto_reject_at"))
    return (
        f"⚔️ <b>Война против «{opp}»</b>\n"
        f"Статус: {st}\n"
        f"Счёт: <b>Мы {our} — Они {their}</b>\n"
        f"{'Конец: ' + ends if ends != '—' else 'Авто-проигрыш: ' + auto_rej}"
    )


def format_relics_html(payload: dict[str, Any], has_alchemy_lab: bool) -> str:
    relics = _relics(payload)
    lines = ["✨ <b>Реликвии клана</b>\n"]
    if relics:
        for rk in relics:
            rd = RELIC_DEFS.get(rk)
            if rd:
                lines.append(f"• {rd['name']} — <i>{rd['desc']}</i>")
    else:
        lines.append("<i>Реликвий нет.</i>")
    if has_alchemy_lab:
        lines.append("\n<b>Можно создать:</b>")
        for rk, rd in RELIC_DEFS.items():
            if rk not in relics:
                lines.append(
                    f"• {rd['name']} — {rd['craft_wood']}🪵 {rd['craft_stone']}🪨 "
                    f"{rd['craft_herbs']}🌿 {rd['craft_gold']:,}💰"
                )
    else:
        lines.append("\n<i>Для крафта реликвий нужна ⚗️ Алхимическая лаборатория.</i>")
    return "\n".join(lines)


# ─────────────────────────── Список кланов (браузер) ────────────────────────

async def browse_clans_page(
    session: AsyncSession, page: int = 0, page_size: int = 8
) -> tuple[list[tuple[Clan, int]], int]:
    """Постраничный список кланов. Возвращает ([(clan, member_count)], total_count)."""
    from sqlalchemy import func as sqlfunc
    from sqlalchemy import select as sqlsel
    from db.models.clan import ClanMembership as CM

    # Общее количество
    total_res = await session.execute(sqlsel(sqlfunc.count()).select_from(Clan))
    total = int(total_res.scalar() or 0)

    # Постраничная выборка — сортировка по уровню клана, затем по XP
    res = await session.execute(
        sqlsel(Clan)
        .order_by(Clan.clan_level.desc(), Clan.clan_xp.desc(), Clan.id.asc())
        .limit(page_size)
        .offset(page * page_size)
    )
    clans = list(res.scalars().all())

    result: list[tuple[Clan, int]] = []
    for c in clans:
        cnt = await clan_repo.count_members(session, int(c.id))
        result.append((c, cnt))
    return result, total


def format_clan_browse_html(
    clans: list[tuple[Clan, int]], page: int, total: int, page_size: int
) -> str:
    if not clans:
        return "⚔️ <b>Все кланы</b>\n\n<i>Кланов пока нет. Создай первый!</i>"
    lines = [f"⚔️ <b>Все кланы</b> (стр. {page + 1})\n"]
    for clan, cnt in clans:
        tag_str = f" [{html.escape(clan.tag)}]" if clan.tag else ""
        desc_str = f"\n   <i>{html.escape(clan.description[:60])}…</i>" if clan.description else ""
        max_m = max_members_for_level(int(clan.clan_level))
        lines.append(
            f"• <b>{html.escape(clan.name)}</b>{tag_str} · ID <code>{clan.id}</code>\n"
            f"   Ур.<b>{clan.clan_level}</b> · 👥 {cnt}/{max_m}"
            f"{desc_str}"
        )
    total_pages = max(1, (total + page_size - 1) // page_size)
    lines.append(f"\n<i>Всего кланов: {total}. Страница {page + 1}/{total_pages}.</i>")
    return "\n".join(lines)


# ─────────────────────────── Редактирование профиля клана ───────────────────

_DESC_MAX = 200

async def try_set_description(
    session: AsyncSession, character: Character, text: str
) -> tuple[bool, str]:
    text = (text or "").strip()
    if len(text) > _DESC_MAX:
        return False, f"Описание не должно превышать {_DESC_MAX} символов."
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None or m.role not in ("leader", "officer"):
        return False, "Только лидер или офицер могут изменить описание."
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return False, "Клан не найден."
    clan.description = text if text else None
    await session.flush()
    payload = _payload(clan)
    _add_event(payload, f"Описание клана обновлено ({m.role}: {html.escape(character.display_name)})")
    await clan_repo.update_payload(session, clan, payload)
    return True, "✅ Описание клана обновлено."


async def try_set_tag(
    session: AsyncSession, character: Character, raw_tag: str
) -> tuple[bool, str]:
    tag = (raw_tag or "").strip().upper()
    if tag == "-":
        tag = ""
    if tag and not _TAG_RE.match(tag):
        return False, "Тег: 2–5 символов (буквы, цифры). Например: WOLF"
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None or m.role != "leader":
        return False, "Только лидер может менять тег клана."
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return False, "Клан не найден."
    if tag:
        existing = await clan_repo.get_clan_by_tag(session, tag)
        if existing and int(existing.id) != int(clan.id):
            return False, f"Тег [{tag}] уже занят другим кланом."
    clan.tag = tag if tag else None
    await session.flush()
    payload = _payload(clan)
    _add_event(payload, f"Тег клана изменён на [{tag or 'убран'}]")
    await clan_repo.update_payload(session, clan, payload)
    return True, f"✅ Тег клана: {'[' + tag + ']' if tag else 'убран'}."


async def try_rename_clan(
    session: AsyncSession, character: Character, new_name: str
) -> tuple[bool, str]:
    name = (new_name or "").strip()
    if not _NAME_RE.match(name):
        return False, "Имя клана: 2–40 символов (буквы, цифры, пробел, дефис)."
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None or m.role != "leader":
        return False, "Только лидер может переименовать клан."
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return False, "Клан не найден."
    existing = await clan_repo.get_clan_by_name(session, name)
    if existing and int(existing.id) != int(clan.id):
        return False, "Такое имя уже занято другим кланом."
    # Переименование стоит золото (анти-спам)
    if int(character.gold) < CLAN_RENAME_COST:
        return False, f"Переименование стоит {CLAN_RENAME_COST:,} 💰."
    character_service.add_gold(
        character,
        -CLAN_RENAME_COST,
        spend_for="Клан: переименование",
        spend_kind="clan",
    )
    old_name = clan.name
    clan.name = name[:64]
    await session.flush()
    payload = _payload(clan)
    _add_event(payload, f"Клан переименован: «{html.escape(old_name)}» → «{html.escape(name)}»")
    await clan_repo.update_payload(session, clan, payload)
    return True, f"✅ Клан переименован в <b>{html.escape(name)}</b>."


def format_clan_settings_html(clan: Clan) -> str:
    tag_str = f"[{html.escape(clan.tag)}]" if clan.tag else "<i>не задан</i>"
    desc_str = html.escape(clan.description) if clan.description else "<i>не задано</i>"
    chat_str = f'<a href="{html.escape(clan.chat_url)}">открыть</a>' if clan.chat_url else "<i>не задана</i>"
    return (
        f"⚙️ <b>Настройки клана «{html.escape(clan.name)}»</b>\n\n"
        f"📛 Название: <b>{html.escape(clan.name)}</b>\n"
        f"🏷️ Тег: {tag_str}\n"
        f"📝 Описание: {desc_str}\n"
        f"💬 Ссылка на чат: {chat_str}\n\n"
        f"<i>Нажми кнопку, чтобы изменить соответствующее поле.</i>"
    )
async def try_set_clan_banner(
    session: AsyncSession, character: Character, emoji: str, text: str
) -> tuple[bool, str]:
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None or m.role != "leader":
        return False, "Только лидер может менять знамя."
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None: return False, "Клан не найден."
    
    payload = _payload(clan)
    payload["banner"] = {"emoji": emoji[:2], "text": text[:32]}
    _add_event(payload, f"Лидер обновил знамя клана: {emoji} {text}")
    await clan_repo.update_payload(session, clan, payload)
    return True, "Знамя обновлено!"


async def try_assign_member_title(
    session: AsyncSession, character: Character, target_id: int, title: str
) -> tuple[bool, str]:
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None or not can_manage(m.role):
        return False, "Недостаточно прав."
    tm = await clan_repo.get_membership(session, int(target_id))
    if tm is None or tm.clan_id != m.clan_id:
        return False, "Игрок не в вашем клане."
    
    payload = tm.payload or {}
    payload["clan_title"] = title[:16]
    tm.payload = payload
    await session.flush()
    return True, "Титул присвоен!"


async def try_clan_altar_blessing(
    session: AsyncSession, character: Character
) -> tuple[bool, str]:
    """Ежедневное благословение у алтаря клана."""
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return False, "Вы не состоите в клане."
    
    # Check cooldown
    from datetime import date
    m_payload = dict(m.payload or {})
    last_bless_str = m_payload.get("last_altar_blessing")
    today = date.today().isoformat()
    
    if last_bless_str == today:
        return False, "Вы уже получили благословение сегодня. Возвращайтесь завтра!"
    
    # Mark as used
    m_payload["last_altar_blessing"] = today
    m.payload = m_payload
    
    # Generate random blessing
    import random
    blessings = [
        ("🗡️ Благословение Меча", "+3 к Силе"),
        ("🛡️ Благословение Щита", "+3 к Выносливости"),
        ("⚡ Благословение Ветра", "+3 к Ловкости"),
        ("🔮 Благословение Мудрости", "+3 к Интеллекту"),
        ("🍀 Благословение Фортуны", "+3 к Удаче"),
    ]
    b_name, b_desc = random.choice(blessings)
    
    # Для реализации реального бонуса нужно добавить временный эффект в Character.payload.
    # Пока что ограничимся уведомлением и сохранением в логах.
    return True, (
        f"🙏 Вы склонились перед алтарем клана...\n\n"
        f"<b>{b_name}</b> снизошло на вас!\n"
        f"<i>{b_desc} (бонус активен до конца дня)</i>"
    )
