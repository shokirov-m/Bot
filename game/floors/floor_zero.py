"""
Этаж 0 — Туториал «Призыв». Игрок выбирает реакцию → получает постоянную пассивку.
"""
from __future__ import annotations

from typing import Any

from db.models.character import Character

META_FLOOR0_DONE = "floor0_done"
META_FLOOR0_PASSIVE = "floor0_passive"

# Три варианта выбора и соответствующие пассивки
FLOOR0_CHOICES: dict[str, dict[str, Any]] = {
    "fighter": {
        "button": "⚔️ Бросаюсь в бой",
        "passive_key": "warrior_instinct",
        "passive_name": "Инстинкт Воина",
        "passive_desc": "+10% к физическому урону навсегда.",
        "passive_emoji": "⚔️",
        "lore": (
            "Ты не размышляешь — ты действуешь. "
            "Тело само принимает боевую стойку. "
            "Башня запомнила твой порыв."
        ),
        # atk_mult применяется в engine (apply_elixir_buffs/attack_player_turn) как множитель урона
        "modifiers": {"atk_mult": 1.10},
    },
    "observer": {
        "button": "🔍 Изучаю обстановку",
        "passive_key": "keen_eye",
        "passive_name": "Зоркий Взгляд",
        "passive_desc": "+10% к шансу критического удара навсегда.",
        "passive_emoji": "🔍",
        "lore": (
            "Ты замечаешь то, что другие игнорируют. "
            "Тонкая трещина в броне, задержка перед атакой... "
            "Башня оценила твою наблюдательность."
        ),
        # crit_bonus используется в engine: roll_crit(luck, crit_bonus_flat=...)
        "modifiers": {"crit_bonus": 0.10},
    },
    "helper": {
        "button": "🤝 Зову на помощь",
        "passive_key": "survivors_bond",
        "passive_name": "Узы Выживших",
        "passive_desc": "+50 к максимальному HP навсегда.",
        "passive_emoji": "🤝",
        "lore": (
            "Ты понимаешь — одному не выжить. "
            "Связь с другими призванными укрепляет тебя изнутри. "
            "Башня запомнила твою мудрость."
        ),
        # hp_max_bonus_flat добавляется через merge_passive_row; combat_service применяет extra HP
        "modifiers": {"hp_max_bonus_flat": 50},
    },
}

FLOOR0_INTRO_TEXT = (
    "🗼 <b>ПРИЗЫВ</b>\n\n"
    "Сирена. Ослепительная вспышка.\n"
    "Ты стоишь у подножия огромной башни в незнакомом мире.\n\n"
    "Голос звучит прямо в голове:\n"
    "<i>«Призванный. Ты выбран. Башня испытает тебя. "
    "Лишь достойные покорят её вершину — и встанут против внешних демонов.»</i>\n\n"
    "Рядом — такие же растерянные незнакомцы. "
    "Один уже вступает в схватку с тенью. "
    "Другой внимательно изучает каменные стены. "
    "Третий кричит, собирая людей вместе.\n\n"
    "<b>Что делаешь ты?</b>"
)

FLOOR0_PASSIVE_RECEIVED_TEXT = (
    "✨ <b>Система зафиксировала твой выбор.</b>\n\n"
    "Пассивный навык: <b>{passive_emoji} {passive_name}</b>\n"
    "<i>{passive_desc}</i>\n\n"
    "{lore}\n\n"
    "━━━━━━━━━━━\n"
    "Этот навык останется с тобой навсегда.\n"
    "Добро пожаловать в Башню, Призванный.\n\n"
    "<i>Нажми кнопку, чтобы войти в Башню.</i>"
)


def is_floor0_done(character: Character) -> bool:
    mp = dict(character.meta_progress or {})
    return bool(mp.get(META_FLOOR0_DONE))


def apply_floor0_passive(character: Character, choice_key: str) -> str:
    """
    Применяет выбранную пассивку этажа 0.
    Возвращает текст для отображения.
    """
    choice = FLOOR0_CHOICES.get(choice_key)
    if choice is None:
        return "Неизвестный выбор."

    mp = dict(character.meta_progress or {})
    mp[META_FLOOR0_PASSIVE] = choice_key
    mp[META_FLOOR0_DONE] = True
    character.meta_progress = mp

    return FLOOR0_PASSIVE_RECEIVED_TEXT.format(
        passive_emoji=choice["passive_emoji"],
        passive_name=choice["passive_name"],
        passive_desc=choice["passive_desc"],
        lore=choice["lore"],
    )


def get_floor0_passive_modifiers(character: Character) -> dict[str, float]:
    """Возвращает модификаторы пассивки этажа 0 для применения в бою."""
    mp = dict(character.meta_progress or {})
    choice_key = mp.get(META_FLOOR0_PASSIVE)
    if not choice_key:
        return {}
    choice = FLOOR0_CHOICES.get(str(choice_key))
    if choice is None:
        return {}
    return dict(choice.get("modifiers", {}))


def get_floor0_passive_display(character: Character) -> str | None:
    """Возвращает отображаемое название пассивки или None."""
    mp = dict(character.meta_progress or {})
    choice_key = mp.get(META_FLOOR0_PASSIVE)
    if not choice_key:
        return None
    choice = FLOOR0_CHOICES.get(str(choice_key))
    if choice is None:
        return None
    return f"{choice['passive_emoji']} {choice['passive_name']}"
