"""
Сервис цепочки заданий Скупщика Орина в таверне.

Состояние: meta_progress['buyer_q_{hub}']:
{
    "step": 1,
    "1_cur": 0, "1_done": false, "1_claimed": false,
    "2_cur": 0, "2_done": false, "2_claimed": false,
    "3_cur": 0, "3_done": false, "3_claimed": false,
    "final_claimed": false
}
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.repository import inventory_repo
from game.quests.tavern_buyer_quests import BuyerQuestStep, chain_for_hub
from services import character_service, fame_service

_KEY_PREFIX = "buyer_q_"


def _meta_key(hub_floor: int) -> str:
    return f"{_KEY_PREFIX}{hub_floor}"


def _get_state(character: Character, hub_floor: int) -> dict:
    meta = character.meta_progress or {}
    raw = meta.get(_meta_key(hub_floor))
    return dict(raw) if isinstance(raw, dict) else {}


def _save_state(character: Character, hub_floor: int, state: dict) -> None:
    meta = dict(character.meta_progress or {})
    meta[_meta_key(hub_floor)] = state
    character.meta_progress = meta


def _init_state() -> dict:
    return {
        "step": 1,
        "1_cur": 0, "1_done": False, "1_claimed": False,
        "2_cur": 0, "2_done": False, "2_claimed": False,
        "3_cur": 0, "3_done": False, "3_claimed": False,
        "final_claimed": False,
    }


def is_started(character: Character, hub_floor: int) -> bool:
    return bool(_get_state(character, hub_floor))


def is_final_claimed(character: Character, hub_floor: int) -> bool:
    return bool(_get_state(character, hub_floor).get("final_claimed"))


def start_chain(character: Character, hub_floor: int) -> bool:
    if _get_state(character, hub_floor):
        return False
    if chain_for_hub(hub_floor) is None:
        return False
    _save_state(character, hub_floor, _init_state())
    return True


def record_battle(
    character: Character,
    hub_floor: int,
    *,
    is_elite: bool = False,
    is_mini_boss: bool = False,
    is_major_boss: bool = False,
    gold_gained: int = 0,
) -> None:
    state = _get_state(character, hub_floor)
    if not state or state.get("final_claimed"):
        return

    chain = chain_for_hub(hub_floor)
    if chain is None:
        return

    current_step = int(state.get("step", 1))
    if current_step > 3:
        return
    if state.get(f"{current_step}_done"):
        return

    step_def: BuyerQuestStep = chain.steps[current_step - 1]
    cur = int(state.get(f"{current_step}_cur", 0))
    target = step_def.target
    qt = step_def.quest_type
    inc = 0

    if qt == "kills_any":
        inc = 1
    elif qt == "earn_gold":
        inc = max(0, gold_gained)
    elif qt == "kills_elite" and (is_elite or is_mini_boss):
        inc = 1
    elif qt == "kills_boss" and (is_mini_boss or is_major_boss):
        inc = 1
    elif qt == "battles_win":
        inc = 1

    if inc > 0:
        new_cur = min(target, cur + inc)
        state[f"{current_step}_cur"] = new_cur
        if new_cur >= target:
            state[f"{current_step}_done"] = True
        _save_state(character, hub_floor, state)


async def claim_step(
    session: AsyncSession,
    character: Character,
    hub_floor: int,
    step: int,
) -> tuple[bool, str]:
    state = _get_state(character, hub_floor)
    if not state:
        return False, "Цепочка не начата."

    chain = chain_for_hub(hub_floor)
    if chain is None:
        return False, "Нет цепочки для этого хаба."

    if step < 1 or step > 3:
        return False, "Неверный шаг."

    current_step = int(state.get("step", 1))
    if step != current_step:
        return False, f"Сейчас активен шаг {current_step}."

    if not state.get(f"{step}_done"):
        return False, "Шаг ещё не выполнен."

    if state.get(f"{step}_claimed"):
        return False, "Награда за этот шаг уже получена."

    step_def: BuyerQuestStep = chain.steps[step - 1]

    character_service.add_gold(character, step_def.reward_gold)
    lv = await character_service.add_experience_async(
        session, character, step_def.reward_xp, bot=None
    )
    fame_service.add_fame(character, step_def.reward_fame)

    state[f"{step}_claimed"] = True
    state["step"] = step + 1
    _save_state(character, hub_floor, state)
    await session.flush()

    lv_html = character_service.level_up_notice_html(character, lv)
    next_info = ""
    if step < 3:
        nxt = chain.steps[step]
        next_info = f"\n\n▶ <b>Следующий шаг:</b> {nxt.title}\n<i>{nxt.desc}</i>"

    return True, (
        f"✅ <b>Шаг {step}: {step_def.title}</b> — выполнен!\n"
        f"💰 +{step_def.reward_gold}  ✨ +{step_def.reward_xp}  ⭐ +{step_def.reward_fame} Слава"
        f"{lv_html}{next_info}"
    )


async def claim_final_reward(
    session: AsyncSession,
    character: Character,
    hub_floor: int,
) -> tuple[bool, str]:
    state = _get_state(character, hub_floor)
    if not state:
        return False, "Цепочка не начата."

    chain = chain_for_hub(hub_floor)
    if chain is None:
        return False, "Нет цепочки для этого хаба."

    for s in (1, 2, 3):
        if not state.get(f"{s}_claimed"):
            return False, f"Сначала сдайте шаг {s}."

    if state.get("final_claimed"):
        return False, "Финальная награда уже получена."

    # Сначала проверяем место в сумке
    slot = await inventory_repo.first_free_bag_slot(session, character.id)
    if slot is None:
        return False, (
            "⚠️ <b>Сумка полна!</b>\n"
            "Освободи хотя бы одно место и возвращайся за финальной наградой.\n"
            "<i>Золото и опыт будут выданы вместе с предметом.</i>"
        )

    character_service.add_gold(character, chain.final_gold)
    lv = await character_service.add_experience_async(
        session, character, chain.final_xp, bot=None
    )
    fame_service.add_fame(character, chain.final_fame)

    await inventory_repo.add_bag_item(
        session, character.id, chain.final_item, bag_slot=slot
    )

    state["final_claimed"] = True
    _save_state(character, hub_floor, state)
    await session.flush()

    lv_html = character_service.level_up_notice_html(character, lv)

    return True, (
        f"<i>{chain.final_text}</i>\n\n"
        f"🏆 <b>Цепочка завершена!</b>\n"
        f"💰 +{chain.final_gold}  ✨ +{chain.final_xp}  ⭐ +{chain.final_fame} Слава\n"
        f"🎁 <b>{chain.final_item['name']}</b> [{chain.final_item['rarity']}] добавлен в сумку!"
        f"{lv_html}"
    )


def format_buyer_quest_html(character: Character, hub_floor: int) -> str:
    """HTML-экран цепочки скупщика."""
    from utils.ui import LINE_SEP

    chain = chain_for_hub(hub_floor)
    if chain is None:
        return "Скупщик здесь не появляется."

    state = _get_state(character, hub_floor)

    lines = [
        LINE_SEP,
        f"{chain.npc_emoji} <b>{chain.npc_name} — {chain.chain_title}</b>",
        LINE_SEP,
    ]

    if not state:
        lines.append(f"<i>{chain.intro}</i>")
        lines.append("")
        lines.append("<b>Задания цепочки:</b>")
        for sd in chain.steps:
            lines.append(f"  {sd.step}. {sd.title} — <i>{sd.desc}</i>")
        lines.append("")
        item = chain.final_item
        lines.append(
            f"🏆 Финал: <b>{item['name']}</b> [{item['rarity']}] "
            f"+ 💰{chain.final_gold} + ⭐{chain.final_fame} Слава"
        )
        return "\n".join(lines)

    if state.get("final_claimed"):
        lines.append("🏆 <b>Цепочка полностью завершена!</b>")
        lines.append("<i>Орин подмигивает тебе — до следующего города.</i>")
        return "\n".join(lines)

    current_step = int(state.get("step", 1))

    for sd in chain.steps:
        s = sd.step
        done = state.get(f"{s}_done", False)
        claimed = state.get(f"{s}_claimed", False)
        cur = int(state.get(f"{s}_cur", 0))
        target = sd.target

        if claimed:
            lines.append(f"✅ Шаг {s}: <b>{sd.title}</b>")
        elif done and not claimed:
            lines.append(f"🎁 Шаг {s}: <b>{sd.title}</b> — <b>ГОТОВО, сдай!</b>")
        elif s == current_step:
            filled = min(10, int(cur * 10 / max(1, target)))
            bar = "🟩" * filled + "⬜" * (10 - filled)
            lines.append(f"⏳ Шаг {s}: <b>{sd.title}</b>")
            lines.append(f"   <i>{sd.desc}</i>")
            lines.append(f"   [{bar}] {cur}/{target}")
        else:
            lines.append(f"🔒 Шаг {s}: <b>{sd.title}</b> — <i>заблокировано</i>")

    lines.append("")
    item = chain.final_item
    if current_step > 3 and all(state.get(f"{s}_claimed") for s in (1, 2, 3)):
        lines.append(
            f"🏆 <b>Все шаги сданы!</b> Получи: <b>{item['name']}</b> [{item['rarity']}]"
        )
    else:
        lines.append(
            f"🏆 Финал: <b>{item['name']}</b> [{item['rarity']}] "
            f"+ 💰{chain.final_gold} + ⭐{chain.final_fame} Слава"
        )

    return "\n".join(lines)
