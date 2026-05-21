"""
Цепочка заданий наставника того же класса (tier‑1) → высший гримуар специализации.
"""

from __future__ import annotations

import html
from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from db.models.character import Character
from game.archetypes import manager as arch_manager
from game.archetypes.grimoires import SUPREME_GRIMOIRES, grant_grimoire, supreme_keys_for_parent

META_KEY = "class_mentor_quest_v1"

# Шаги: wins, elites, boss_floor_win
STEPS = (
    {"id": "wins", "need": 12, "label": "Побед в боях на башне"},
    {"id": "elites", "need": 5, "label": "Побед над элитами (⭐)"},
    {"id": "trials", "need": 3, "label": "Завершённых испытаний этажей"},
)


def _meta(character: Character) -> dict[str, Any]:
    return dict(character.meta_progress or {})


def _quest_state(character: Character) -> dict[str, Any]:
    raw = _meta(character).get(META_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def _save(character: Character, st: dict[str, Any]) -> None:
    mp = _meta(character)
    mp[META_KEY] = st
    character.meta_progress = mp
    try:
        flag_modified(character, "meta_progress")
    except Exception:
        pass


def parent_class_key(character: Character) -> str | None:
    arch = arch_manager.get_character_archetype(character)
    if arch.tier != 1:
        return None
    return str(character.class_key or "").lower()


def quest_available(character: Character) -> bool:
    if int(character.level or 0) < 50:
        return False
    return parent_class_key(character) is not None


def quest_completed(character: Character) -> bool:
    st = _quest_state(character)
    return bool(st.get("completed"))


def ensure_quest_started(character: Character) -> None:
    if not quest_available(character):
        return
    st = _quest_state(character)
    if st.get("started"):
        return
    st = {
        "started": True,
        "wins": 0,
        "elites": 0,
        "trials": 0,
        "completed": False,
        "reward_grimoire": "",
    }
    _save(character, st)


def record_battle_win(character: Character, *, was_elite: bool = False) -> None:
    if not quest_available(character) or quest_completed(character):
        return
    ensure_quest_started(character)
    st = _quest_state(character)
    st["wins"] = int(st.get("wins") or 0) + 1
    if was_elite:
        st["elites"] = int(st.get("elites") or 0) + 1
    _check_complete(character, st)


def record_trial_completed(character: Character) -> None:
    if not quest_available(character) or quest_completed(character):
        return
    ensure_quest_started(character)
    st = _quest_state(character)
    st["trials"] = int(st.get("trials") or 0) + 1
    _check_complete(character, st)


def _check_complete(character: Character, st: dict[str, Any]) -> None:
    for step in STEPS:
        sid = step["id"]
        if int(st.get(sid) or 0) < int(step["need"]):
            _save(character, st)
            return
    st["completed"] = True
    st["ready_pick_reward"] = True
    _save(character, st)


def grant_supreme_reward(character: Character, supreme_key: str) -> tuple[bool, str]:
    pk = parent_class_key(character)
    if not pk:
        return False, "Нужен базовый путь (tier 1)."
    st = _quest_state(character)
    if not st.get("completed") and not st.get("ready_pick_reward"):
        return False, "Сначала завершите цепочку наставника."
    sg = SUPREME_GRIMOIRES.get(supreme_key)
    if not sg or sg.parent_class_key != pk:
        return False, "Этот высший гримуар не для вашего пути."
    if not grant_grimoire(character, supreme_key, to_inventory=True):
        return False, "Не удалось выдать гримуар."
    st["reward_grimoire"] = supreme_key
    st["ready_pick_reward"] = False
    _save(character, st)
    return True, f"Награда: {sg.name_ru}. Откройте «Гримуары» в специализации."


def format_quest_html(character: Character) -> str:
    pk = parent_class_key(character)
    arch = arch_manager.get_character_archetype(character)
    if not pk:
        return (
            "🎓 <b>Наставник пути</b>\n\n"
            "<i>Цепочка доступна с 50 уровня, если у вас выбран базовый путь "
            "(Воин, Маг, Следопыт или Жрец), но ещё нет специализации tier‑2.</i>"
        )
    if int(character.level or 0) < 50:
        return (
            f"🎓 <b>Наставник — {html.escape(arch.name_ru)}</b>\n\n"
            f"Вернитесь на <b>50 уровне</b>. Сейчас: {int(character.level)}."
        )
    ensure_quest_started(character)
    st = _quest_state(character)
    lines = [
        f"🎓 <b>Наставник — {html.escape(arch.name_ru)}</b>",
        "",
        "Выполните испытания — получите <b>высший гримуар</b> специализации. "
        "Прочитав его, вы смените класс (Guardian, Berserker и т.д.).",
        "",
        "<b>Прогресс:</b>",
    ]
    for step in STEPS:
        sid = step["id"]
        cur = int(st.get(sid) or 0)
        need = int(step["need"])
        mark = "✅" if cur >= need else "⏳"
        lines.append(f"{mark} {step['label']}: <b>{cur}/{need}</b>")
    if st.get("completed"):
        lines.append("")
        if st.get("reward_grimoire"):
            sg = SUPREME_GRIMOIRES.get(str(st["reward_grimoire"]))
            nm = sg.name_ru if sg else "гримуар"
            lines.append(f"🏆 <b>Награда получена:</b> {html.escape(nm)}")
            lines.append("<i>Специализация → Гримуары → прочитать высший гримуар.</i>")
        elif st.get("ready_pick_reward"):
            lines.append("🏆 <b>Цепочка завершена!</b> Выберите специализацию ниже.")
        else:
            lines.append("🏆 Цепочка завершена.")
    return "\n".join(lines)


def can_pick_reward(character: Character) -> bool:
    st = _quest_state(character)
    return bool(st.get("ready_pick_reward")) and not st.get("reward_grimoire")
