"""
Сервис цепочки заданий кузнеца.

Состояние: meta_progress['forge_q_{hub}'] например 'forge_q_3':
{
    "step": 1,           # текущий активный шаг (1–3, 4 = все шаги сданы)
    "1_cur": 0,          # прогресс шага 1
    "1_done": false,     # шаг 1 выполнен (цель достигнута)
    "1_claimed": false,  # шаг 1 — промежуточная награда получена
    "2_cur": 0,
    "2_done": false,
    "2_claimed": false,
    "3_cur": 0,
    "3_done": false,
    "3_claimed": false,
    "final_claimed": false
}
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.repository import inventory_repo
from game.quests.forge_quests import ForgeQuestChain, ForgeQuestStep, chain_for_hub
from services import character_service, fame_service

_KEY_PREFIX = "forge_q_"


# ── Вспомогательные ───────────────────────────────────────────────────────────

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


# ── Публичный API ─────────────────────────────────────────────────────────────

def is_started(character: Character, hub_floor: int) -> bool:
    return bool(_get_state(character, hub_floor))


def is_final_claimed(character: Character, hub_floor: int) -> bool:
    return bool(_get_state(character, hub_floor).get("final_claimed"))


def start_chain(character: Character, hub_floor: int) -> bool:
    """Начать цепочку заданий. False если уже начата."""
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
    """Обновить прогресс активного шага цепочки."""
    state = _get_state(character, hub_floor)
    if not state:
        return
    if state.get("final_claimed"):
        return

    chain = chain_for_hub(hub_floor)
    if chain is None:
        return

    current_step = int(state.get("step", 1))
    if current_step > 3:
        return

    step_def: ForgeQuestStep = chain.steps[current_step - 1]

    # Если шаг уже выполнен — ждём сдачи
    if state.get(f"{current_step}_done"):
        return

    cur = int(state.get(f"{current_step}_cur", 0))
    target = step_def.target
    qt = step_def.quest_type
    inc = 0

    if qt == "earn_gold":
        inc = max(0, gold_gained)
    elif qt == "kills_elite" and (is_elite or is_mini_boss):
        inc = 1
    elif qt == "kills_boss" and (is_mini_boss or is_major_boss):
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
    """
    Сдать промежуточный шаг и получить небольшую награду.
    После сдачи открывается следующий шаг.
    """
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

    step_def: ForgeQuestStep = chain.steps[step - 1]

    character_service.add_gold(character, step_def.reward_gold)
    lv = await character_service.add_experience_async(
        session, character, step_def.reward_xp, bot=None
    )
    fame_service.add_fame(character, step_def.reward_fame)

    state[f"{step}_claimed"] = True
    # Переходим к следующему шагу или в состояние «все шаги сданы»
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
    """Получить финальную награду (предмет) после завершения всех трёх шагов."""
    state = _get_state(character, hub_floor)
    if not state:
        return False, "Цепочка не начата."

    chain = chain_for_hub(hub_floor)
    if chain is None:
        return False, "Нет цепочки для этого хаба."

    # Все 3 шага должны быть сданы
    for s in (1, 2, 3):
        if not state.get(f"{s}_claimed"):
            return False, f"Сначала сдайте шаг {s}."

    if state.get("final_claimed"):
        return False, "Финальная награда уже получена."

    # Выдаём финальную награду
    character_service.add_gold(character, chain.final_gold)
    lv = await character_service.add_experience_async(
        session, character, chain.final_xp, bot=None
    )
    fame_service.add_fame(character, chain.final_fame)

    # Добавляем предмет в инвентарь
    slot = await inventory_repo.first_free_bag_slot(session, character.id)
    item_added = False
    if slot is not None:
        await inventory_repo.add_bag_item(
            session, character.id, chain.final_item, bag_slot=slot
        )
        item_added = True

    state["final_claimed"] = True
    _save_state(character, hub_floor, state)
    await session.flush()

    lv_html = character_service.level_up_notice_html(character, lv)
    item_line = f"\n🎁 <b>{chain.final_item['name']}</b> [{chain.final_item['rarity']}] добавлен в сумку!" if item_added else "\n⚠️ Сумка полна — предмет потерян."

    return True, (
        f"<i>{chain.final_text}</i>\n\n"
        f"🏆 <b>Цепочка завершена!</b>\n"
        f"💰 +{chain.final_gold}  ✨ +{chain.final_xp}  ⭐ +{chain.final_fame} Слава"
        f"{item_line}{lv_html}"
    )


# ── Форматирование экрана ─────────────────────────────────────────────────────

def format_forge_quest_html(character: Character, hub_floor: int) -> str:
    """HTML-экран цепочки заданий кузнеца."""
    from utils.ui import LINE_SEP

    chain = chain_for_hub(hub_floor)
    if chain is None:
        return "Нет цепочки заданий для этого города."

    state = _get_state(character, hub_floor)

    lines = [
        LINE_SEP,
        f"{chain.npc_emoji} <b>{chain.npc_name} — {chain.chain_title}</b>",
        LINE_SEP,
    ]

    if not state:
        # Не начато
        lines.append(f"<i>{chain.intro}</i>")
        lines.append("")
        lines.append("<b>Задания цепочки:</b>")
        for step_def in chain.steps:
            lines.append(f"  {step_def.step}. {step_def.title} — <i>{step_def.desc}</i>")
        lines.append("")
        item = chain.final_item
        lines.append(
            f"🏆 Финал: <b>{item['name']}</b> [{item['rarity']}] "
            f"+ 💰{chain.final_gold} + ⭐{chain.final_fame} Слава"
        )
        return "\n".join(lines)

    if state.get("final_claimed"):
        lines.append("🏆 <b>Цепочка полностью завершена!</b>")
        lines.append(f"<i>Возвращайтесь в следующем городе.</i>")
        return "\n".join(lines)

    current_step = int(state.get("step", 1))

    for step_def in chain.steps:
        s = step_def.step
        done = state.get(f"{s}_done", False)
        claimed = state.get(f"{s}_claimed", False)
        cur = int(state.get(f"{s}_cur", 0))
        target = step_def.target

        if claimed:
            lines.append(f"✅ Шаг {s}: <b>{step_def.title}</b>")
        elif done and not claimed:
            lines.append(f"🎁 Шаг {s}: <b>{step_def.title}</b> — <b>ГОТОВО, сдай!</b>")
        elif s == current_step:
            filled = min(10, int(cur * 10 / max(1, target)))
            bar = "🟩" * filled + "⬜" * (10 - filled)
            lines.append(f"⏳ Шаг {s}: <b>{step_def.title}</b>")
            lines.append(f"   <i>{step_def.desc}</i>")
            lines.append(f"   [{bar}] {cur}/{target}")
        else:
            lines.append(f"🔒 Шаг {s}: <b>{step_def.title}</b> — <i>заблокировано</i>")

    lines.append("")
    item = chain.final_item
    if current_step > 3 and all(state.get(f"{s}_claimed") for s in (1, 2, 3)):
        lines.append(
            f"🏆 <b>Все шаги сданы!</b> Получи финальную награду: "
            f"<b>{item['name']}</b> [{item['rarity']}]"
        )
    else:
        lines.append(
            f"🏆 Финал: <b>{item['name']}</b> [{item['rarity']}] "
            f"+ 💰{chain.final_gold} + ⭐{chain.final_fame} Слава"
        )

    return "\n".join(lines)
