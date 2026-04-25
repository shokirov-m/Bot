"""
Сервис ежедневных заданий.

Состояние хранится в character.meta_progress['daily_quests_v1']:
{
    "date": "2026-04-25",   — UTC-дата генерации квестов
    "tier": 3,              — тир на момент генерации
    "quests": [
        {
            "slot": 0,
            "key": "dq_t3_k25",
            "type": "kills_any",
            "title": "Тенеборец",
            "desc": "Победи 25 монстров в башне.",
            "target": 25,
            "current": 7,
            "claimed": false,
            "reward_gold": 280,
            "reward_xp": 140,
            "reward_rune": 0
        },
        ...  (slot 1, slot 2)
    ]
}

Каждый день в 00:00 UTC квесты пересоздаются (новые 3 из пула тира).
Квесты детерминированы: seed = int(date) * 1000 + character_id → повторяемость при рестарте.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from db.models.character import Character
from game.quests.daily_quests import (
    DailyQuestTemplate,
    pool_for_tier,
    tier_for_floor,
    type_label,
)
from services import character_service
from services.fame_bonuses import daily_quest_slots_count

META_KEY = "daily_quests_v1"
QUESTS_PER_DAY = 3  # база; с славой ≥ 25 — см. daily_quest_slots_count


def _utc_today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


# ── Загрузка/сохранение состояния ─────────────────────────────────────────────

def _load(character: Character) -> tuple[dict, dict]:
    """Возвращает (meta, state)."""
    meta = dict(character.meta_progress or {})
    raw = meta.get(META_KEY)
    if not isinstance(raw, dict):
        raw = {}
    return meta, raw


def _save(character: Character, meta: dict, state: dict) -> None:
    meta[META_KEY] = state
    character.meta_progress = meta
    # In-place меняет вложенные dict/list — явно помечаем JSON-колонку.
    flag_modified(character, "meta_progress")


# ── Генерация заданий ──────────────────────────────────────────────────────────

def _generate_quests(
    date_iso: str,
    character_id: int,
    tier: int,
    n_slots: int,
) -> list[dict]:
    """Детерминированно выбирает n шаблонов из пула тира."""
    pool = pool_for_tier(tier)
    date_int = int(date_iso.replace("-", ""))
    rng = random.Random(date_int * 10000 + character_id)
    take = min(max(1, n_slots), len(pool))
    selected: list[DailyQuestTemplate] = rng.sample(pool, take)

    quests = []
    for i, tpl in enumerate(selected):
        quests.append({
            "slot": i,
            "key": tpl.key,
            "type": tpl.type,
            "title": tpl.title,
            "desc": tpl.desc,
            "target": tpl.target,
            "current": 0,
            "claimed": False,
            "reward_gold": tpl.reward_gold,
            "reward_xp": tpl.reward_xp,
            "reward_rune": tpl.reward_rune,
        })
    return quests


def _extend_quests_to_count(
    character: Character,
    meta: dict,
    state: dict[str, Any],
    quests: list[dict],
    need: int,
    today: str,
    tier: int,
) -> None:
    """Добавить квесты, если слава дала 4-й слот при тех же date/tier."""
    pool = pool_for_tier(tier)
    used = {str(q.get("key")) for q in quests}
    free_tpl = [p for p in pool if p.key not in used]
    if not free_tpl:
        return
    date_int = int(today.replace("-", ""))
    rng = random.Random(date_int * 10000 + int(character.id) + 777)
    i = len(quests)
    while len(quests) < need and free_tpl:
        tpl = rng.choice(free_tpl)
        free_tpl = [p for p in free_tpl if p.key != tpl.key]
        quests.append(
            {
                "slot": i,
                "key": tpl.key,
                "type": tpl.type,
                "title": tpl.title,
                "desc": tpl.desc,
                "target": tpl.target,
                "current": 0,
                "claimed": False,
                "reward_gold": tpl.reward_gold,
                "reward_xp": tpl.reward_xp,
                "reward_rune": tpl.reward_rune,
            },
        )
        i += 1
    state["quests"] = quests
    _save(character, meta, state)


def _ensure_today(character: Character) -> dict:
    """
    Гарантирует, что у персонажа есть актуальные (сегодняшние) ежедневные задания.
    Если дата изменилась — пересоздаёт. Возвращает state.
    """
    today = _utc_today_iso()
    meta, state = _load(character)
    tier = tier_for_floor(int(character.highest_floor_reached))
    need = daily_quest_slots_count(character)

    if state.get("date") == today and state.get("tier") == tier:
        qlist: list[dict] = list(state.get("quests") or [])
        if len(qlist) < need:
            _extend_quests_to_count(character, meta, state, qlist, need, today, tier)
        return state

    new_state: dict = {
        "date": today,
        "tier": tier,
        "quests": _generate_quests(today, int(character.id), tier, need),
    }
    _save(character, meta, new_state)
    return new_state


# ── Публичный API ──────────────────────────────────────────────────────────────

def get_daily_quests(character: Character) -> list[dict]:
    """Возвращает список из QUESTS_PER_DAY заданий (актуальных на сегодня)."""
    state = _ensure_today(character)
    return list(state.get("quests") or [])


def can_claim(quest: dict) -> bool:
    """Задание выполнено, но ещё не забрано."""
    return (
        not quest.get("claimed", False)
        and int(quest.get("current", 0)) >= int(quest.get("target", 1))
    )


def is_done(quest: dict) -> bool:
    """Задание выполнено (независимо от того, забрана ли награда)."""
    return int(quest.get("current", 0)) >= int(quest.get("target", 1))


def record_battle_result(
    character: Character,
    *,
    is_elite: bool = False,
    is_mini_boss: bool = False,
    is_major_boss: bool = False,
    gold_gained: int = 0,
) -> None:
    """
    Вызывать после победы в бою.
    Обновляет прогресс всех активных ежедневных заданий.
    """
    state = _ensure_today(character)
    quests: list[dict] = state.get("quests") or []
    changed = False

    for q in quests:
        if q.get("claimed"):
            continue
        cur = int(q.get("current", 0))
        target = int(q.get("target", 1))
        if cur >= target:
            continue  # уже выполнено

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
        meta = dict(character.meta_progress or {})
        _save(character, meta, state)


async def claim_quest(
    session: AsyncSession,
    character: Character,
    slot: int,
) -> tuple[bool, str]:
    """
    Забирает награду за задание с индексом slot (0, 1, 2).
    Возвращает (ok, html_message).
    """
    # Сериализация параллельных нажатий «Забрать» и актуальные meta из БД.
    await session.execute(select(Character.id).where(Character.id == character.id).with_for_update())
    await session.refresh(character)

    state = _ensure_today(character)
    quests: list[dict] = state.get("quests") or []

    quest = next((q for q in quests if q.get("slot") == slot), None)
    if quest is None:
        return False, "Задание не найдено."

    if quest.get("claimed") is True:
        return False, "Награда за это задание уже получена."

    cur = int(quest.get("current", 0))
    target = int(quest.get("target", 1))
    if cur < target:
        remaining = target - cur
        return False, f"Задание не выполнено. Осталось: {remaining}."

    # Выдаём награду
    gold = int(quest.get("reward_gold", 0))
    xp = int(quest.get("reward_xp", 0))
    runes = int(quest.get("reward_rune", 0))

    character_service.add_gold(character, gold)
    lv = await character_service.add_experience_async(session, character, xp, bot=None)

    if runes > 0:
        character.rune_stones = int(character.rune_stones or 0) + runes

    quest["claimed"] = True
    meta = dict(character.meta_progress or {})
    _save(character, meta, state)
    await session.flush()

    lv_html = character_service.level_up_notice_html(character, lv)
    rune_html = f"\n⚗️ +{runes} рунных камней" if runes > 0 else ""
    return True, (
        f"🎁 <b>{quest['title']}</b>\n"
        f"Награда получена!\n"
        f"💰 +{gold} золота  ✨ +{xp} опыта{rune_html}{lv_html}"
    )


# ── Форматирование экрана ─────────────────────────────────────────────────────

def format_daily_quests_html(character: Character) -> str:
    """HTML-текст экрана ежедневных заданий."""
    from utils.ui import LINE_SEP
    quests = get_daily_quests(character)
    tier = tier_for_floor(int(character.highest_floor_reached))
    today = _utc_today_iso()

    tier_names = {
        1: "🌿 Лес (1–10)",
        2: "🌿 Болота (11–20)",
        3: "🕳️ Пещеры теней (21–30)",
        4: "⚔️ Средние ярусы (31–50)",
        5: "🏔️ Высшие ярусы (51–100)",
    }

    lines = [
        LINE_SEP,
        "📅 <b>ЕЖЕДНЕВНЫЕ ЗАДАНИЯ</b>",
        f"<i>Тир: {tier_names.get(tier, str(tier))} · Сброс в 00:00 UTC</i>",
        LINE_SEP,
        "",
    ]

    all_claimed = all(q.get("claimed") for q in quests)
    if all_claimed:
        lines.append("🏆 <b>Все задания выполнены!</b>")
        lines.append("<i>Возвращайся завтра — будут новые.</i>")
        return "\n".join(lines)

    for q in quests:
        cur = int(q.get("current", 0))
        target = int(q.get("target", 1))
        claimed = q.get("claimed", False)
        title = q.get("title", "")
        desc = q.get("desc", "")
        gold = q.get("reward_gold", 0)
        xp = q.get("reward_xp", 0)
        rune = q.get("reward_rune", 0)
        qt = q.get("type", "")

        # Прогресс-бар (10 клеток)
        if target > 0:
            filled = min(10, int(cur * 10 / target))
        else:
            filled = 10
        bar = "🟩" * filled + "⬜" * (10 - filled)

        if claimed:
            status = "✅ Выполнено"
            bar_line = f"[{bar}] {target}/{target}"
        elif cur >= target:
            status = "🎁 Готово к получению!"
            bar_line = f"[{bar}] {cur}/{target}"
        else:
            status = f"⏳ {cur}/{target}"
            bar_line = f"[{bar}] {cur}/{target}"

        rune_txt = f" · ⚗️×{rune}" if rune > 0 else ""
        reward_txt = f"💰{gold} · ✨{xp}{rune_txt}"

        lines.append(f"<b>{type_label(qt)} — {title}</b>")
        lines.append(f"<i>{desc}</i>")
        lines.append(f"{bar_line}  {status}")
        lines.append(f"Награда: {reward_txt}")
        lines.append("")

    lines.append("<i>⏳ Обновление в 00:00 UTC</i>")
    return "\n".join(lines)


def daily_quest_keyboard_rows(
    character: Character,
    floor_number: int,
) -> list[list[Any]]:
    """
    Возвращает список рядов кнопок для ежедневных заданий.
    Используется в сборке InlineKeyboardMarkup снаружи.
    """
    from aiogram.types import InlineKeyboardButton

    quests = get_daily_quests(character)
    rows = []
    for q in quests:
        slot = q.get("slot", 0)
        if can_claim(q):
            rows.append([
                InlineKeyboardButton(
                    text=f"🎁 Забрать: {q['title'][:22]}",
                    callback_data=f"qdcl:{slot}",
                )
            ])
    return rows
