"""
Сервис заданий от случайных путников (этажи 1–20).

Состояние хранится в character.meta_progress['wnpc_quests']:
{
    "7": {                    # ключ = номер этажа (строка)
        "npc_key": "ranger",
        "type": "kills_boss",
        "current": 0,
        "target": 1,
        "claimed": false,
        "reward_gold": 200,
        "reward_xp": 100,
        "reward_fame": 10,
        "reward_rune": 0,
        "special": ""
    },
    ...
}

У каждого этажа — не более одного активного задания от путника.
Задание берётся по кнопке, прогресс обновляется при победах в боях.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from game.tower.quests.wandering_npc_quests import (
    WanderingQuestDef,
    npc_index_for_floor,
    quest_for_npc_index,
)
import services.progression.character_service as character_service
import services.progression.fame_service as fame_service

_META_KEY = "wnpc_quests"


# ── Вспомогательные ───────────────────────────────────────────────────────────

def _all_quests(character: Character) -> dict:
    meta = character.meta_progress or {}
    raw = meta.get(_META_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def _save_all(character: Character, data: dict) -> None:
    meta = dict(character.meta_progress or {})
    meta[_META_KEY] = data
    character.meta_progress = meta


def _floor_key(floor: int) -> str:
    return str(floor)


# ── Публичный API ─────────────────────────────────────────────────────────────

def get_quest_for_floor(character: Character, floor: int) -> dict | None:
    """Возвращает состояние задания на этаже или None (если не взято)."""
    return _all_quests(character).get(_floor_key(floor))


def quest_def_for_floor(character: Character, floor: int) -> WanderingQuestDef | None:
    """Шаблон задания NPC, который появляется на данном этаже для этого персонажа."""
    idx = npc_index_for_floor(int(character.id), floor)
    return quest_for_npc_index(idx)


def is_quest_active(character: Character, floor: int) -> bool:
    q = get_quest_for_floor(character, floor)
    return q is not None and not q.get("claimed", False)


def is_quest_complete(character: Character, floor: int) -> bool:
    q = get_quest_for_floor(character, floor)
    if q is None:
        return False
    return int(q.get("current", 0)) >= int(q.get("target", 1))


def can_claim(character: Character, floor: int) -> bool:
    q = get_quest_for_floor(character, floor)
    if q is None:
        return False
    return (
        not q.get("claimed", False)
        and int(q.get("current", 0)) >= int(q.get("target", 1))
    )


def take_quest(character: Character, floor: int) -> bool:
    """
    Взять задание от путника на этаже. Возвращает False если уже взято/выполнено.
    """
    existing = get_quest_for_floor(character, floor)
    if existing is not None:
        return False  # уже взято

    defn = quest_def_for_floor(character, floor)
    if defn is None:
        return False

    all_q = _all_quests(character)
    all_q[_floor_key(floor)] = {
        "npc_key": defn.npc_key,
        "type": defn.quest_type,
        "current": 0,
        "target": defn.target,
        "claimed": False,
        "reward_gold": defn.reward_gold,
        "reward_xp": defn.reward_xp,
        "reward_fame": defn.reward_fame,
        "reward_rune": defn.reward_rune,
        "special": defn.special,
    }
    _save_all(character, all_q)
    return True


def record_battle(
    character: Character,
    *,
    is_elite: bool = False,
    is_mini_boss: bool = False,
    is_major_boss: bool = False,
    gold_gained: int = 0,
) -> None:
    """
    Вызывать после каждой победы. Обновляет прогресс всех активных заданий путников.
    """
    all_q = _all_quests(character)
    changed = False

    for floor_str, q in all_q.items():
        if q.get("claimed"):
            continue
        cur = int(q.get("current", 0))
        target = int(q.get("target", 1))
        if cur >= target:
            continue

        qt = q.get("type", "")
        inc = 0

        if qt == "kills_any":
            inc = 1
        elif qt == "kills_elite" and (is_elite or is_mini_boss):
            inc = 1
        elif qt == "kills_boss" and (is_mini_boss or is_major_boss):
            inc = 1
        elif qt == "battles_win":
            inc = 1
        elif qt == "earn_gold":
            inc = max(0, gold_gained)

        if inc > 0:
            q["current"] = min(target, cur + inc)
            changed = True

    if changed:
        _save_all(character, all_q)


async def claim_quest_reward(
    session: AsyncSession,
    character: Character,
    floor: int,
) -> tuple[bool, str]:
    """
    Забрать награду за выполненное задание на этаже.
    Возвращает (ok, html_text).
    """
    all_q = _all_quests(character)
    fk = _floor_key(floor)
    q = all_q.get(fk)

    if q is None:
        return False, "Задание не найдено."
    if q.get("claimed"):
        return False, "Награда уже получена."
    cur = int(q.get("current", 0))
    target = int(q.get("target", 1))
    if cur < target:
        return False, f"Задание не выполнено. Прогресс: {cur}/{target}."

    # Получаем шаблон для текста NPC
    defn = quest_def_for_floor(character, floor)
    complete_text = defn.complete_text if defn else "— Благодарю тебя, герой."

    gold = int(q.get("reward_gold", 0))
    xp = int(q.get("reward_xp", 0))
    fame = int(q.get("reward_fame", 0))
    runes = int(q.get("reward_rune", 0))
    special = q.get("special", "")

    character_service.add_gold(character, gold)
    lv = await character_service.add_experience_async(session, character, xp, bot=None)
    fame_service.add_fame(character, fame)

    if runes > 0:
        character.rune_stones = int(character.rune_stones or 0) + runes

    # Особый эффект: лекарь лечит HP
    heal_line = ""
    if special == "heal":
        heal_amt = max(5, int(character.hp_max * 0.25))
        character.hp_current = min(int(character.hp_max), int(character.hp_current) + heal_amt)
        heal_line = f"\n❤️ +{heal_amt} HP"

    q["claimed"] = True
    _save_all(character, all_q)
    await session.flush()

    rune_line = f"\n⚗️ +{runes} рунных камней" if runes > 0 else ""
    lv_html = character_service.level_up_notice_html(character, lv)

    return True, (
        f"<i>{complete_text}</i>\n\n"
        f"🎁 <b>Награда получена!</b>\n"
        f"💰 +{gold} золота\n"
        f"✨ +{xp} опыта\n"
        f"⭐ +{fame} Славы"
        f"{rune_line}{heal_line}{lv_html}"
    )


# ── Форматирование экрана НПС ─────────────────────────────────────────────────

def format_npc_quest_screen(character: Character, floor: int) -> str:
    """HTML-текст экрана задания путника."""
    from utils.telegram.ui import LINE_SEP

    defn = quest_def_for_floor(character, floor)
    if defn is None:
        return "Здесь никого нет."

    q = get_quest_for_floor(character, floor)

    lines = [
        LINE_SEP,
        f"{defn.npc_emoji} <b>{defn.npc_name}</b>",
        LINE_SEP,
    ]

    if q is None:
        # Задание ещё не взято — показываем вводный диалог
        lines.append(defn.intro)
        lines.append("")
        lines.append(f"<b>Задание:</b> {defn.quest_title}")
        lines.append(f"<i>{defn.quest_desc}</i>")
        lines.append("")
        rune_txt = f" · ⚗️×{defn.reward_rune}" if defn.reward_rune > 0 else ""
        lines.append(f"💰 {defn.reward_gold}  ✨ {defn.reward_xp}  ⭐ {defn.reward_fame} Слава{rune_txt}")
    elif q.get("claimed"):
        lines.append("✅ <b>Задание выполнено и награда получена.</b>")
        lines.append("<i>Путник ушёл своей дорогой...</i>")
    else:
        cur = int(q.get("current", 0))
        target = int(q.get("target", 1))
        if target > 0:
            filled = min(10, int(cur * 10 / target))
        else:
            filled = 10
        bar = "🟩" * filled + "⬜" * (10 - filled)

        if cur >= target:
            status = "🎁 Готово! Получи награду."
        else:
            status = f"⏳ Прогресс: {cur}/{target}"

        lines.append(f"<b>📜 {defn.quest_title}</b>")
        lines.append(f"<i>{defn.quest_desc}</i>")
        lines.append(f"[{bar}] {cur}/{target}")
        lines.append(status)
        lines.append("")
        rune_txt = f" · ⚗️×{q.get('reward_rune', 0)}" if int(q.get("reward_rune", 0)) > 0 else ""
        lines.append(f"Награда: 💰{q.get('reward_gold')} · ✨{q.get('reward_xp')} · ⭐{q.get('reward_fame')} Слава{rune_txt}")

    return "\n".join(lines)
