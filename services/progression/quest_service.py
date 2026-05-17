"""
Квесты: странник (tower_slain_*), расширенные NPC (npcq_*), награды и прогресс.
"""

from __future__ import annotations

import html
import random
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.models.quest import QuestProgress
from db.repository import character_repo, inventory_repo, quest_repo
from game.enemies.floors.spawns import FloorMonsterSpawn
from game.tower.quests.floor_quests import npc_quest_template, reward_for_quest
from game.tower.quests.npc_quests import (
    QuestTemplate,
    quest_bonus_item_payload,
    template_by_key,
    templates_for_floor,
)
import services.progression.character_service as character_service


async def apply_kill_progress(session: AsyncSession, character: Character) -> str:
    """
    После победы: +1 к счётчику активных квестов tower_slain_* (странник).
    Награда выдаётся сразу при выполнении.
    """
    rows = await quest_repo.list_active_slain_quests(session, character.id)
    if not rows:
        return ""

    lines: list[str] = []
    for row in rows:
        p = dict(row.progress or {})
        need = int(p.get("need", 2))
        k = int(p.get("kills", 0)) + 1
        p["kills"] = k
        row.progress = p

        if k >= need:
            gold = int(p.get("reward_gold", 0))
            xp = int(p.get("reward_xp", 0))
            await quest_repo.mark_completed(session, row)
            character_service.add_gold(character, gold)
            lv = await character_service.add_experience_async(session, character, xp, bot=None)
            mpq = dict(character.meta_progress or {})
            mpq["stranger_quests_done"] = int(mpq.get("stranger_quests_done", 0)) + 1
            character.meta_progress = mpq
            title = html.escape(str(p.get("title", "Странник")))
            lines.append(
                f"\n📜 <b>Квест выполнен:</b> {title}\n"
                f"   +{gold} 💰, +{xp} опыта."
                f"{character_service.level_up_notice_html(character, lv)}",
            )

    await session.flush()
    return "".join(lines)


def _snapshot_progress(tpl: QuestTemplate) -> dict[str, Any]:
    return {
        "quest_type": tpl.quest_type,
        "target_key": tpl.target_key,
        "current": 0,
        "target_count": tpl.target_count,
        "reward_gold": tpl.reward_gold,
        "reward_exp": tpl.reward_exp,
        "reward_item_chance": tpl.reward_item_chance,
        "reward_rune_chance": tpl.reward_rune_chance,
        "pending_claim": False,
        "title": tpl.title,
        "npc_floor": tpl.floor,
    }


def _matches_kill_event(
    p: dict[str, Any],
    monster_key: str,
    *,
    is_elite: bool,
    is_mini_boss: bool,
    is_major_boss: bool,
) -> bool:
    qt = str(p.get("quest_type", ""))
    tk = str(p.get("target_key", ""))
    if qt == "kill":
        if is_mini_boss or is_major_boss:
            return False
        return monster_key == tk
    if qt == "kill_elite":
        return is_elite
    if qt == "kill_mini":
        return is_mini_boss and monster_key == tk
    if qt == "defeat_boss":
        return is_major_boss and monster_key == tk
    return False


async def get_available_quests(
    session: AsyncSession,
    character_id: int,
    floor: int,
) -> list[QuestTemplate]:
    """Шаблоны на этаже, которые ещё не взяты (нет записи или не активны как новые)."""
    out: list[QuestTemplate] = []
    for tpl in templates_for_floor(floor):
        row = await quest_repo.get_by_key(session, character_id, tpl.key)
        if row is None:
            out.append(tpl)
    return out


async def take_quest(session: AsyncSession, character: Character, quest_key: str) -> tuple[bool, str]:
    """Взять квест npcq. Сообщение — plain для alert или HTML для экрана."""
    tpl = template_by_key(quest_key)
    if tpl is None:
        return False, "Неизвестное задание."
    if int(character.floor_number) != tpl.floor:
        return False, "Заказчик ждёт на другом этаже."
    if not templates_for_floor(tpl.floor):
        return False, "Здесь нет такого поручения."

    row = await quest_repo.get_by_key(session, character.id, quest_key)
    if row is not None:
        if row.status == "completed":
            return False, "Ты уже выполнял это поручение."
        if row.status == "active":
            return False, "Задание уже в журнале."

    await quest_repo.create_active(session, character.id, quest_key, _snapshot_progress(tpl))
    await session.flush()
    return True, (
        f"📋 <b>{html.escape(tpl.title)}</b>\n"
        f"{html.escape(tpl.description)}\n\n"
        "✅ Задание принято. Выполняй и вернись за наградой."
    )


async def update_kill_progress(
    session: AsyncSession,
    character_id: int,
    monster_key: str,
    *,
    is_elite: bool = False,
    is_mini_boss: bool = False,
    is_major_boss: bool = False,
) -> list[str]:
    """
    После победы над монстром: обновить активные npcq_*.
    Возвращает ключи квестов, которые только что стали готовы к сдаче (pending_claim).
    """
    rows = await quest_repo.list_active_npc_extended_quests(session, character_id)
    done: list[str] = []
    for row in rows:
        p = dict(row.progress or {})
        if p.get("pending_claim"):
            continue
        if not _matches_kill_event(
            p,
            monster_key,
            is_elite=is_elite,
            is_mini_boss=is_mini_boss,
            is_major_boss=is_major_boss,
        ):
            continue
        cur = int(p.get("current", 0)) + 1
        tgt = int(p.get("target_count", 1))
        p["current"] = cur
        if cur >= tgt:
            p["pending_claim"] = True
            done.append(row.quest_key)
        row.progress = p
    if done:
        await session.flush()
    return done


async def update_kill_progress_from_spawn(
    session: AsyncSession,
    character_id: int,
    spawn: FloorMonsterSpawn,
) -> list[str]:
    """Обертка: взять флаги из спавна."""
    return await update_kill_progress(
        session,
        character_id,
        spawn.template.key,
        is_elite=spawn.is_elite,
        is_mini_boss=spawn.is_mini_boss,
        is_major_boss=spawn.is_major_boss,
    )


async def check_quest_completion(session: AsyncSession, character_id: int, quest_key: str) -> bool:
    """True если цель достигнута и ждёт награда у NPC."""
    row = await quest_repo.get_by_key(session, character_id, quest_key)
    if row is None or row.status != "active":
        return False
    p = dict(row.progress or {})
    return bool(p.get("pending_claim"))


async def claim_quest_reward(
    session: AsyncSession,
    character: Character,
    quest_key: str,
) -> dict[str, Any]:
    """
    Выдать награду за npcq. Возвращает {gold, exp, item, rune_stones, title, errors?}.
    """
    await character_repo.lock_character_row(session, character.id)
    row = await quest_repo.get_by_key(session, character.id, quest_key)
    tpl = template_by_key(quest_key)
    if row is None or tpl is None:
        return {"ok": False, "error": "Квест не найден."}
    if row.status != "active":
        return {"ok": False, "error": "Квест не активен."}
    p = dict(row.progress or {})
    if not p.get("pending_claim"):
        return {"ok": False, "error": "Ещё не выполнено."}

    gold = int(p.get("reward_gold", tpl.reward_gold))
    xp = int(p.get("reward_exp", tpl.reward_exp))
    ich = float(p.get("reward_item_chance", tpl.reward_item_chance))
    rch = float(p.get("reward_rune_chance", tpl.reward_rune_chance))

    character_service.add_gold(character, gold)
    lv = await character_service.add_experience_async(session, character, xp, bot=None)
    await quest_repo.mark_completed(session, row)

    item_gained: dict[str, Any] | None = None
    if random.random() < ich:
        slot = await inventory_repo.first_free_bag_slot(session, character.id)
        if slot is not None:
            payload = quest_bonus_item_payload(tpl.floor)
            await inventory_repo.add_bag_item(session, character.id, payload, bag_slot=slot)
            item_gained = payload

    rune_gain = 0
    if random.random() < rch:
        rune_gain = 1 + (tpl.floor // 40)
        character.rune_stones = int(character.rune_stones) + rune_gain

    if random.random() < 0.02:
        from game.crafting.workshop_meta import add_known_blueprint

        add_known_blueprint(character, "bp_tower_flame_blade")

    await session.flush()
    return {
        "ok": True,
        "gold": gold,
        "exp": xp,
        "item": item_gained,
        "rune_stones": rune_gain,
        "title": tpl.title,
        "level_up_html": character_service.level_up_notice_html(character, lv),
    }


async def active_npc_quest_rows_for_floor(
    session: AsyncSession,
    character_id: int,
    floor: int,
) -> list[QuestProgress]:
    """Активные npcq на этом этаже (по шаблонам этажа)."""
    keys = {t.key for t in templates_for_floor(floor)}
    rows = await quest_repo.list_active_npc_extended_quests(session, character_id)
    return [r for r in rows if r.quest_key in keys]


async def try_accept_quest(
    session: AsyncSession,
    character: Character,
    floor_number: int,
) -> tuple[bool, str]:
    """
    Принять квест странника (tower_slain_*). (ok, message_html).
    """
    tpl = npc_quest_template(floor_number)
    if tpl is None:
        return False, "Здесь нет странника с поручением."

    existing = await quest_repo.get_by_key(session, character.id, tpl.quest_key)
    if existing is not None:
        if existing.status == "completed":
            return True, (
                f"📜 <b>{html.escape(tpl.title)}</b>\n"
                "Ты уже исполнил долг странника на этом этаже."
            )
        p = dict(existing.progress or {})
        k = int(p.get("kills", 0))
        need = int(p.get("need", tpl.kills_needed))
        return True, (
            f"📜 <b>{html.escape(tpl.title)}</b>\n"
            f"Прогресс: побед над тварями башни — <b>{k}/{need}</b>.\n"
            "Продолжай сражаться."
        )

    gold, xp = reward_for_quest(floor_number, tpl.kills_needed)
    await quest_repo.create_active(
        session,
        character.id,
        tpl.quest_key,
        {
            "kills": 0,
            "need": tpl.kills_needed,
            "reward_gold": gold,
            "reward_xp": xp,
            "title": tpl.title,
        },
    )
    await session.flush()
    return True, (
        f"📜 <b>{html.escape(tpl.title)}</b>\n"
        "Странник просит низвергнуть тварей башни.\n"
        f"Цель: <b>{tpl.kills_needed}</b> побед в бою.\n"
        f"Награда: <b>{gold}</b> золота, <b>{xp}</b> опыта.\n\n"
        "✅ Квест принят."
    )


def format_quest_intro_html(floor_number: int) -> str | None:
    tpl = npc_quest_template(floor_number)
    if tpl is None:
        return None
    gold, xp = reward_for_quest(floor_number, tpl.kills_needed)
    return (
        f"📜 <b>{html.escape(tpl.title)}</b>\n"
        "У костра сидит странник в лохмотьях. Он шепчет о проклятой башне…\n"
        f"«Победи <b>{tpl.kills_needed}</b> тварей — и я отблагодарю: "
        f"<b>{gold}</b> монет и знание (+{xp} опыта).»"
    )
