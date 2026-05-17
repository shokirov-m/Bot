"""
Поручения стражи в городах: принятие, прогресс по победам, награда.
"""

from __future__ import annotations

import copy
import html

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.repository import inventory_repo, quest_repo
from game.quests.city_quests import city_quest_template
import services.progression.character_service as character_service


async def apply_kill_progress(session: AsyncSession, character: Character) -> str:
    """После победы: +1 к активным city_task_*."""
    rows = await quest_repo.list_active_city_quests(session, character.id)
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
            gear_raw = p.get("reward_gear")
            await quest_repo.mark_completed(session, row)
            character_service.add_gold(character, gold)
            lv = await character_service.add_experience_async(session, character, xp, bot=None)
            mp = dict(character.meta_progress or {})
            mp["city_quests_done"] = int(mp.get("city_quests_done", 0)) + 1
            character.meta_progress = mp
            t = html.escape(str(p.get("title", "Поручение")))
            gear_note = ""
            if isinstance(gear_raw, dict) and gear_raw:
                free = await inventory_repo.first_free_bag_slot(session, character.id)
                gname = html.escape(str(gear_raw.get("name", "предмет")))
                if free is None:
                    # [FIX] Сохраняем награду в pending, чтобы не потерять
                    mp = dict(character.meta_progress or {})
                    pending = list(mp.get("pending_gear_rewards") or [])
                    pending.append(copy.deepcopy(gear_raw))
                    mp["pending_gear_rewards"] = pending
                    character.meta_progress = mp

                    gear_note = (
                        f"\n   ⚠️ Награда <b>{gname}</b> не поместилась в сумку — "
                        "освободи место, она сохранена в «ожидающие» (забери позже у стражи)."
                    )
                else:
                    await inventory_repo.add_bag_item(
                        session,
                        character.id,
                        copy.deepcopy(gear_raw),
                        bag_slot=free,
                    )
                    gear_note = f"\n   🎁 В сумку: <b>{gname}</b> (ячейка {free})."
            lines.append(
                f"\n🏛️ <b>Город:</b> поручение выполнено — {t}\n"
                f"   +{gold} 💰, +{xp} опыта.{gear_note}"
                f"{character_service.level_up_notice_html(character, lv)}",
            )

    await session.flush()
    return "".join(lines)


async def try_accept_quest(
    session: AsyncSession,
    character: Character,
    floor_number: int,
) -> tuple[bool, str]:
    tpl = city_quest_template(floor_number)
    if tpl is None:
        return False, "Здесь нет стражи с поручением."

    existing = await quest_repo.get_by_key(session, character.id, tpl.quest_key)
    if existing is not None:
        if existing.status == "completed":
            return True, (
                f"🏛️ <b>{html.escape(tpl.title)}</b>\n"
                "Ты уже исполнил это поручение в этом городе."
            )
        p = dict(existing.progress or {})
        k = int(p.get("kills", 0))
        need = int(p.get("need", tpl.kills_needed))
        return True, (
            f"🏛️ <b>{html.escape(tpl.title)}</b>\n"
            f"Прогресс: побед в башне — <b>{k}/{need}</b>.\n"
            "Возвращайся после охоты."
        )

    progress: dict = {
        "kills": 0,
        "need": tpl.kills_needed,
        "reward_gold": tpl.reward_gold,
        "reward_xp": tpl.reward_xp,
        "title": tpl.title,
    }
    if tpl.reward_gear is not None:
        progress["reward_gear"] = copy.deepcopy(tpl.reward_gear)

    await quest_repo.create_active(
        session,
        character.id,
        tpl.quest_key,
        progress,
    )
    await session.flush()
    gear_line = ""
    if tpl.reward_gear:
        gn = html.escape(str(tpl.reward_gear.get("name", "предмет")))
        gear_line = f", экипировка: <b>{gn}</b>"
    return True, (
        f"🏛️ <b>{html.escape(tpl.title)}</b>\n"
        f"{tpl.intro_html}\n\n"
        f"<b>Награда:</b> {tpl.reward_gold} золота, {tpl.reward_xp} опыта{gear_line}.\n\n"
        "✅ Поручение принято. Одолей врагов на любом этаже башни."
    )


def offer_screen_html(floor_number: int) -> str | None:
    tpl = city_quest_template(floor_number)
    if tpl is None:
        return None
    gear_line = ""
    if tpl.reward_gear:
        gn = html.escape(str(tpl.reward_gear.get("name", "предмет")))
        gear_line = f", экипировка: <b>{gn}</b>"
    return (
        f"{tpl.intro_html}\n\n"
        f"<b>Награда:</b> {tpl.reward_gold} золота, {tpl.reward_xp} опыта{gear_line}."
    )


async def try_claim_pending_rewards(session: AsyncSession, character: Character) -> str:
    """
    Проверяет наличие невыданных наград (pending_gear_rewards) в meta_progress.
    Пытается выдать их в свободные слоты. Возвращает текст результата.
    """
    mp = dict(character.meta_progress or {})
    pending = list(mp.get("pending_gear_rewards") or [])
    if not pending:
        return ""

    lines: list[str] = ["\n🎁 <b>Ожидающие награды:</b>"]
    still_pending: list[dict] = []
    granted_count = 0

    for gear_raw in pending:
        free = await inventory_repo.first_free_bag_slot(session, character.id)
        gname = html.escape(str(gear_raw.get("name", "предмет")))
        if free is None:
            still_pending.append(gear_raw)
            lines.append(f"   ❌ <b>{gname}</b> — всё ещё нет места в сумке.")
        else:
            await inventory_repo.add_bag_item(
                session,
                character.id,
                copy.deepcopy(gear_raw),
                bag_slot=free,
            )
            lines.append(f"   ✅ <b>{gname}</b> (выдано в ячейку {free})")
            granted_count += 1

    if granted_count > 0:
        mp["pending_gear_rewards"] = still_pending
        character.meta_progress = mp
        await session.flush()
        return "\n".join(lines) + "\n"

    if still_pending:
        return "\n".join(lines) + "\n"

    return ""
