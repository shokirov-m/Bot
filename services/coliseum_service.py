"""
Прогресс Колизея в meta_progress.coliseum_v1, доступ к бойцам, награды за победу.
"""

from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.repository import inventory_repo
from game.coliseum.coliseum_data import fighter_by_id
from game.coliseum.coliseum_rewards import COLISEUM_LOOT, LootEntry, loot_for_fighter_id
from game.items.stat_bonuses import STAT_KEYS
from services import title_service

META_KEY = "coliseum_v1"

_STAT_FLAT_LABEL_RU: dict[str, str] = {
    "str": "СИЛ",
    "dex": "ЛОВ",
    "int": "ИНТ",
    "vit": "ВЫН",
    "luck": "УДЧ",
}


def _coliseum_skill_reward_html(pl: dict[str, Any], sk: str) -> str:
    parts: list[str] = []
    for k in STAT_KEYS:
        v = int(pl.get(f"{k}_flat") or 0)
        if v and k in _STAT_FLAT_LABEL_RU:
            parts.append(f"+{v} {_STAT_FLAT_LABEL_RU[k]}")
    lab = str(pl.get("label_ru") or sk)
    if parts:
        return f"📜 Приём Колизея: <b>{lab}</b> <i>({', '.join(parts)} навсегда)</i>"
    return f"📜 Приём Колизея: <b>{lab}</b>"


def _block(character: Character) -> dict[str, Any]:
    mp = dict(character.meta_progress or {})
    raw = mp.get(META_KEY)
    if not isinstance(raw, dict):
        return {}
    return raw


def defeated_ids(character: Character) -> list[int]:
    d = _block(character).get("defeated")
    if not isinstance(d, list):
        return []
    out: list[int] = []
    for x in d:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return sorted(set(out))


def next_fighter_id(character: Character) -> int | None:
    """Первый не побеждённый боец по порядку 1..50 для UI «следующий»."""
    beat = set(defeated_ids(character))
    for fid in range(1, 51):
        if fid not in beat:
            return fid
    return None


def can_start_fight(character: Character, fighter_id: int) -> tuple[bool, str]:
    fid = int(fighter_id)
    if fid < 1 or fid > 50:
        return False, "Нет такого бойца."
    fdef = fighter_by_id(fid)
    if fdef is None:
        return False, "Данные бойца отсутствуют."
    if int(character.level) < int(fdef.required_level):
        return False, f"Нужен уровень {fdef.required_level}."
    beat = defeated_ids(character)
    if fid in beat:
        return False, "Этот боец уже повержен."
    if fid > 1 and (fid - 1) not in beat:
        return False, "Сначала победи предыдущего бойца."
    return True, ""


def reward_multipliers(fighter_id: int) -> tuple[int, int]:
    """Базовые exp и gold из таблицы; чемпион ×2."""
    fdef = fighter_by_id(int(fighter_id))
    if fdef is None:
        return 0, 0
    mult = 2 if fdef.is_champion else 1
    return int(fdef.exp_reward) * mult, int(fdef.gold_reward) * mult


async def record_victory(session: AsyncSession, character: Character, fighter_id: int) -> None:
    mp = dict(character.meta_progress or {})
    block = dict(mp.get(META_KEY) or {})
    done = set(defeated_ids(character))
    done.add(int(fighter_id))
    block["defeated"] = sorted(done)
    mp[META_KEY] = block
    character.meta_progress = mp
    await session.flush()
    if len(block["defeated"]) >= 50:
        title_service.grant_title_key(character, "coliseum_overlord", silent=True)
    title_service.refresh_unlocks(character)
    await session.flush()


async def grant_loot(session: AsyncSession, character: Character, loot: LootEntry | None) -> list[str]:
    """Выдача одной награды; строки для экрана победы."""
    if loot is None:
        return []
    lines: list[str] = []
    kind = str(loot.get("kind") or "")
    try:
        if kind == "title":
            tk = str(loot.get("title_key") or "")
            if tk and title_service.grant_title_key(character, tk, silent=True):
                from game.characters.titles import TITLE_BY_KEY

                nm = TITLE_BY_KEY[tk].name_ru if tk in TITLE_BY_KEY else tk
                lines.append(f"🏆 Титул: <b>{nm}</b>")
        elif kind == "equipment" or kind == "consumable":
            data = dict(loot.get("item_data") or {})
            if not data:
                return lines
            row = await inventory_repo.add_bag_item(session, int(character.id), data)
            if row is None:
                lines.append("⚠️ Сумка полна — предмет не добавлен.")
            else:
                nm = str(data.get("name") or "Предмет")
                lines.append(f"📦 Получено: <b>{nm}</b>")
        elif kind == "skill_meta":
            sk = str(loot.get("skill_key") or "")
            pl = dict(loot.get("skill_payload") or {})
            if sk:
                mp = dict(character.meta_progress or {})
                skills = dict(mp.get("coliseum_skills") or {})
                skills[sk] = pl
                mp["coliseum_skills"] = skills
                character.meta_progress = mp
                lines.append(_coliseum_skill_reward_html(pl, sk))
    except Exception:
        logger.exception("coliseum grant_loot")
    return lines


def loot_entry_for_fighter(fighter_id: int) -> LootEntry | None:
    fdef = fighter_by_id(int(fighter_id))
    if fdef is None:
        return None
    return loot_for_fighter_id(int(fighter_id)) or COLISEUM_LOOT.get(fdef.loot_id)
