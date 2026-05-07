"""Найм, отряд, бой: статы наёмников и опыт."""

from __future__ import annotations

import html
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from db.models.character import Character
from db.models.mercenary import Mercenary
from db.repository import mercenary_repo
from game.mercenaries.constants import FEATURE_BLACK_MARKET_COMBAT
from game.mercenaries.mercenary_classes import role_def
from game.mercenaries.mercenary_loyalty import (
    BATTLE_WIN_LOYALTY,
    LOYALTY_MAX,
    loyalty_stat_multiplier,
)
from game.mercenaries.shadow_market_meta import (
    get_merc_xp_share_percent,
    get_party_merc_ids,
    max_mercs_in_battle,
    roster_collection_cap,
)


def merc_to_combat_dict(m: Mercenary) -> dict[str, Any]:
    rd = role_def(str(m.class_role))
    mult = loyalty_stat_multiplier(int(m.loyalty))
    hp = max(1, int(round(int(m.hp_max) * mult)))
    atk = max(1, int(round(int(m.atk) * mult)))
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
        out.append(merc_to_combat_dict(m))
    return out


async def grant_merc_xp_after_tower_win(
    session: AsyncSession,
    character: Character,
    player_xp_gained: int,
    combat_state: dict[str, Any],
) -> None:
    if not FEATURE_BLACK_MARKET_COMBAT:
        return
    comps = list(combat_state.get("companions") or [])
    if not comps:
        return
    share = get_merc_xp_share_percent(character)
    per = max(0, int(round(int(player_xp_gained) * (share / 100.0))))
    if per <= 0:
        return
    ids = [int(c["id"]) for c in comps if not c.get("dead")]
    if not ids:
        return
    rows = await mercenary_repo.get_by_ids_for_character(session, int(character.id), ids)
    for m in rows:
        m.level = int(m.level) + max(0, per // 200)
        m.atk = int(m.atk) + max(0, per // 500)
        m.hp_max = int(m.hp_max) + max(0, per // 400)
        m.loyalty = min(LOYALTY_MAX, int(m.loyalty) + BATTLE_WIN_LOYALTY)
        try:
            flag_modified(m, "level")
            flag_modified(m, "atk")
            flag_modified(m, "hp_max")
            flag_modified(m, "loyalty")
        except Exception:
            pass


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
        extra={},
    )
    session.add(m)
    await session.flush()
    return True, f"Наёмник <b>{m.display_name}</b> теперь в твоём ростере."


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
        f"Слоты ростера: <b>{len(mercs)}</b> / {cap}. В бою одновременно: до <b>{max_mercs_in_battle(character)}</b>.",
        f"Доля XP с побед: <b>{xp_pct}%</b> от опыта героя (настраивается кнопками ниже).",
        "",
    ]
    if not mercs:
        lines.append("<i>Пока пусто — купи наёмника у Жабса на рынке (26 этаж после зачистки).</i>")
        return "\n".join(lines)
    party_set = {int(x) for x in party_ids}
    for m in mercs:
        rd = role_def(str(m.class_role))
        in_party = "✅ в отряде" if int(m.id) in party_set else "○ вне отряда"
        lines.append(
            f"• <b>{html.escape(m.display_name)}</b> — {html.escape(rd.name_ru)}, "
            f"ур.{m.level}, ♥{m.loyalty}, ❤️{m.hp_max} ⚔️{m.atk} ({in_party})",
        )
    lines.append(
        "\n<i>При высокой преданности (70+) наёмник умнее выбирает удары в бою (авто). "
        "Ревность и «работы» — в следующих обновлениях.</i>",
    )
    return "\n".join(lines)


def sync_party_after_roster_change(character: Character, valid_ids: set[int]) -> None:
    from game.mercenaries import shadow_market_meta as smm

    cur = [x for x in get_party_merc_ids(character) if int(x) in valid_ids]
    smm.set_party_merc_ids(character, cur)
