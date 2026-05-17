"""
Цепочка миссий «Странник» при славе 150+.
"""

from __future__ import annotations

import html
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from db.models.character import Character
from game.quests.wanderer_fame_quests import (
    META_WANDERER_FAME_CHAIN,
    WANDERER_FAME_STEPS,
    WandererFameStep,
)
from services.progression.fame_bonuses import F_WANDERER_ACCESS, wanderer_content_unlocked
from services.progression.fame_service import get_fame


def _block(character: Character) -> dict[str, Any]:
    raw = (character.meta_progress or {}).get(META_WANDERER_FAME_CHAIN)
    return dict(raw) if isinstance(raw, dict) else {}


def _save_block(character: Character, block: dict[str, Any]) -> None:
    meta = dict(character.meta_progress or {})
    meta[META_WANDERER_FAME_CHAIN] = block
    character.meta_progress = meta
    flag_modified(character, "meta_progress")


def chain_done(character: Character) -> bool:
    if not wanderer_content_unlocked(character):
        return False
    return bool(_block(character).get("done"))


def current_step_index(character: Character) -> int:
    """0..len(STEPS)-1 пока не завершено; len(STEPS) если done."""
    if chain_done(character):
        return len(WANDERER_FAME_STEPS)
    return max(0, min(int(_block(character).get("idx", 0)), len(WANDERER_FAME_STEPS) - 1))


def current_step(character: Character) -> WandererFameStep | None:
    if chain_done(character):
        return None
    idx = current_step_index(character)
    if idx >= len(WANDERER_FAME_STEPS):
        return None
    return WANDERER_FAME_STEPS[idx]


def current_progress(character: Character) -> int:
    return max(0, int(_block(character).get("prog", 0)))


def _ensure_started(character: Character) -> dict[str, Any]:
    block = _block(character)
    if not block and wanderer_content_unlocked(character):
        block = {"idx": 0, "prog": 0, "done": False}
        _save_block(character, block)
    return block


def _complete_step(character: Character, step: WandererFameStep) -> str:
    import services.progression.character_service as character_service

    character_service.add_gold(character, step.reward_gold)
    if step.reward_xp > 0:
        character_service.add_experience(character, step.reward_xp)
    block = _block(character)
    idx = int(block.get("idx", 0)) + 1
    if idx >= len(WANDERER_FAME_STEPS):
        block = {"idx": idx, "prog": 0, "done": True}
    else:
        block = {"idx": idx, "prog": 0, "done": False}
    _save_block(character, block)

    if step.reward_runes > 0:
        character.rune_stones = int(character.rune_stones or 0) + int(step.reward_runes)

    rune_line = f", ⚗️ +{step.reward_runes}" if step.reward_runes > 0 else ""
    return (
        f"🧙 <b>Странник:</b> «{html.escape(step.title)}» выполнено.\n"
        f"+{step.reward_gold} 💰, +{step.reward_xp} опыта{rune_line}"
    )


def _try_advance(character: Character, step: WandererFameStep) -> str:
    prog = current_progress(character)
    if prog < step.target:
        return ""
    return _complete_step(character, step)


def on_combat_kill(character: Character, *, is_elite: bool) -> str:
    if not wanderer_content_unlocked(character) or chain_done(character):
        return ""
    _ensure_started(character)
    step = current_step(character)
    if step is None:
        return ""
    block = _block(character)
    if step.quest_type == "kills_any":
        block["prog"] = int(block.get("prog", 0)) + 1
        _save_block(character, block)
        return _try_advance(character, step)
    if step.quest_type == "kills_elite" and is_elite:
        block["prog"] = int(block.get("prog", 0)) + 1
        _save_block(character, block)
        return _try_advance(character, step)
    return ""


def on_daily_quest_claimed(character: Character) -> str:
    if not wanderer_content_unlocked(character) or chain_done(character):
        return ""
    _ensure_started(character)
    step = current_step(character)
    if step is None or step.quest_type != "daily_claim":
        return ""
    block = _block(character)
    block["prog"] = int(block.get("prog", 0)) + 1
    _save_block(character, block)
    return _try_advance(character, step)


def on_arena_win(character: Character) -> str:
    if not wanderer_content_unlocked(character) or chain_done(character):
        return ""
    _ensure_started(character)
    step = current_step(character)
    if step is None or step.quest_type != "arena_win":
        return ""
    block = _block(character)
    block["prog"] = 1
    _save_block(character, block)
    return _try_advance(character, step)


async def claim_seal(
    session: AsyncSession,
    character: Character,
) -> tuple[bool, str]:
    """Финальный шаг «Печать странника» (кнопка в хабе заданий)."""
    if get_fame(character) < F_WANDERER_ACCESS:
        return False, "Нужна слава 150+."
    if chain_done(character):
        return False, "Завет странника уже получен."
    _ensure_started(character)
    step = current_step(character)
    if step is None:
        return False, "Все миссии уже выполнены."
    if step.quest_type != "seal_claim":
        return False, f"Сначала заверши шаг: «{step.title}»."
    import services.progression.character_service as character_service

    msg = _complete_step(character, step)
    await session.flush()
    return True, msg


def format_chain_summary_html(character: Character) -> str:
    """Краткий блок для экрана ежедневных заданий."""
    if not wanderer_content_unlocked(character):
        return ""
    if chain_done(character):
        return (
            "\n🧙 <b>Особые миссии Странника</b>\n"
            "<i>Завет принят. Путь исполнен.</i>"
        )
    _ensure_started(character)
    step = current_step(character)
    if step is None:
        return ""
    prog = current_progress(character)
    need = step.target
    if step.quest_type == "seal_claim":
        prog_line = "Готово к получению печати."
    else:
        prog_line = f"Прогресс: <b>{prog}/{need}</b>"
    idx = current_step_index(character)
    total = len(WANDERER_FAME_STEPS)
    return (
        f"\n🧙 <b>Особые миссии Странника</b> "
        f"(шаг <b>{idx + 1}/{total}</b>)\n"
        f"<b>{html.escape(step.title)}</b> — {html.escape(step.description)}\n"
        f"<i>{prog_line}</i>"
    )


def format_chain_detail_html(character: Character) -> str:
    from utils.telegram.ui import LINE_SEP

    if not wanderer_content_unlocked(character):
        return "Нужна слава <b>150+</b>, чтобы слышать зов Странника."
    if chain_done(character):
        return (
            f"{LINE_SEP}\n"
            "🧙 <b>Завет Странника</b>\n"
            "<i>Все пять испытаний пройдены. Башня помнит твоё имя.</i>"
        )
    _ensure_started(character)
    cur = current_step_index(character)
    lines = [
        LINE_SEP,
        "🧙 <b>ОСОБЫЕ МИССИИ СТРАННИКА</b>",
        "<i>Доступно при славе 150+. Награды за каждый шаг.</i>",
        LINE_SEP,
        "",
    ]
    for i, st in enumerate(WANDERER_FAME_STEPS):
        if i < cur:
            mark = "✅"
        elif i == cur:
            mark = "▶️"
        else:
            mark = "🔒"
        lines.append(f"{mark} <b>{html.escape(st.title)}</b> — {html.escape(st.description)}")
        if i == cur and st.quest_type != "seal_claim":
            lines.append(f"   <i>Прогресс: {current_progress(character)}/{st.target}</i>")
        elif i == cur and st.quest_type == "seal_claim":
            lines.append("   <i>Нажми «Получить печать» ниже.</i>")
    return "\n".join(lines)
