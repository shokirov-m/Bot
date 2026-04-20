"""
UI-хелперы: полоски HP/MP/стамины/опыта, заточка, карточка предмета (ТЗ).
"""

from __future__ import annotations

import html
from typing import Any

from game.items import enchant as enchant_rules
from game.items.equipment import (
    RARITY_EMOJI,
    RARITY_NAME_RU,
    SLOT_LABEL_RU,
    gear_icon_for_item_data,
    item_is_two_handed,
    resolve_equip_slot_for_item_data,
    ring_slot_is_explicit,
)
from game.items.rarity_scaling import (
    armor_enchant_defensive_bonus,
    scaled_armor_defense_value,
    scaled_weapon_attack_value,
)
from game.items.stat_bonuses import format_item_stat_bonus_line

# Базовый разделитель (совместимость со старыми экранами).
LINE_SEP: str = "------------------------"
# Разные экраны — разный настрой (узнаваемо в ленте).
LINE_SEP_BATTLE: str = "────────────────────"
LINE_SEP_CITY: str = "════════════════════"
LINE_SEP_TAVERN: str = "∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿"


def format_number(value: int) -> str:
    """Формат 1250 → «1,250»."""
    return f"{value:,}"


_BAR_LEN = 14


def _mono_bar(current: int, maximum: int, length: int = _BAR_LEN) -> str:
    if maximum <= 0:
        maximum = 1
    current = max(0, min(current, maximum))
    filled = int(round((current / maximum) * length))
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)


def render_hp_bar(
    current: int,
    max_hp: int,
    length: int = _BAR_LEN,
    *,
    wrap_bar_in_code: bool = True,
    spaced_numbers: bool = False,
) -> str:
    """HP: полоска + числа справа; в бою bar в <code> для моноширины."""
    bar = _mono_bar(current, max_hp, length)
    pct = (current / max_hp) * 100 if max_hp > 0 else 0
    icon = "💔" if pct < 25 else "🧡" if pct < 55 else "❤️"
    if spaced_numbers:
        n = f"{format_number(current)} / {format_number(max_hp)}"
        gap = "   "
    else:
        n = f"{format_number(current)}/{format_number(max_hp)}"
        gap = "  "
    bar_s = f"<code>{bar}</code>" if wrap_bar_in_code else bar
    return f"{icon} {bar_s}{gap}{n}"


def render_mp_bar(
    current: int,
    max_mp: int,
    length: int = _BAR_LEN,
    *,
    wrap_bar_in_code: bool = True,
    spaced_numbers: bool = False,
) -> str:
    """MP — тот же формат, что HP."""
    bar = _mono_bar(current, max_mp, length)
    pct = (current / max_mp) * 100 if max_mp > 0 else 0
    icon = "💧" if pct < 25 else "💠" if pct < 55 else "💙"
    if spaced_numbers:
        n = f"{format_number(current)} / {format_number(max_mp)}"
        gap = "   "
    else:
        n = f"{format_number(current)}/{format_number(max_mp)}"
        gap = "  "
    bar_s = f"<code>{bar}</code>" if wrap_bar_in_code else bar
    return f"{icon} {bar_s}{gap}{n}"


def render_stamina_bar(
    current: int,
    max_stam: int = 20,
    length: int = 10,
    *,
    minutes_to_next: int | None = None,
    wrap_bar_in_code: bool = True,
) -> str:
    """Полоска стамины; при 0 — подсказка о восстановлении."""
    if max_stam <= 0:
        max_stam = 1
    current = max(0, min(current, max_stam))
    filled = int(round((current / max_stam) * length))
    filled = max(0, min(length, filled))
    bar = "█" * filled + "░" * (length - filled)
    suffix = ""
    if current == 0 and minutes_to_next is not None and minutes_to_next > 0:
        suffix = f" (восст. через {minutes_to_next} мин)"
    elif current == 0:
        suffix = " (восст. по таймеру)"
    bar_s = f"<code>{bar}</code>" if wrap_bar_in_code else bar
    if wrap_bar_in_code:
        return f"⚡ {bar_s} {format_number(current)}/{format_number(max_stam)}{suffix}"
    return f"⚡ {bar_s}  {format_number(current)}/{format_number(max_stam)}{suffix}"


def render_exp_bar(
    current: int,
    needed: int,
    length: int = _BAR_LEN,
    *,
    wrap_bar_in_code: bool = True,
) -> str:
    """Опыт к следующему уровню — тот же ритм полосы, что HP/MP."""
    if needed <= 0:
        needed = 1
    bar = _mono_bar(current, needed, length)
    n = f"{format_number(current)}/{format_number(needed)}"
    bar_s = f"<code>{bar}</code>" if wrap_bar_in_code else bar
    return f"✨ {bar_s}  {n}"


def render_enchant_stars(level: int) -> str:
    """Отображение уровня заточки: ✨ / ⭐ / ⭐⭐ по вилкам ТЗ."""
    if level <= 0:
        return "+0"
    if level <= 5:
        return f"+{level} ✨"
    if level <= 9:
        return f"+{level} ✨"
    if level <= 12:
        return f"+{level} ⭐"
    return f"+{level} ⭐⭐"


def format_inventory_item_html(data: dict[str, Any] | None) -> str:
    """Карточка предмета: русский тип слота, редкость с эмодзи, статы, набор."""
    if not data:
        return "<i>Нет данных</i>"
    lines: list[str] = []
    name = html.escape(str(data.get("name", "Предмет")))
    r = str(data.get("rarity") or "common").lower()
    em = RARITY_EMOJI.get(r, "⚪")
    ru = RARITY_NAME_RU.get(r, html.escape(r))
    gi = gear_icon_for_item_data(data)
    lines.append(f"{em} {gi} <b>{name}</b> · <i>{html.escape(ru)}</i>")
    kind = data.get("kind")
    if str(kind).lower() == "weapon":
        if item_is_two_handed(data):
            lines.append("⚙️ <b>Двуручное</b> — вторая рука занята этим оружием.")
        elif str(data.get("hand") or "main").lower() in ("off", "offhand", "second", "left"):
            lines.append("⚙️ Надевается во <b>вторую руку</b>.")
    slot = resolve_equip_slot_for_item_data(data)
    if str(kind).lower() == "ring" and slot and not ring_slot_is_explicit(data):
        lines.append("📌 Тип: 💍 Кольцо (первый свободный слот I или II)")
    elif slot and slot in SLOT_LABEL_RU:
        lines.append(f"📌 Тип: {SLOT_LABEL_RU[slot]}")
    elif kind:
        lines.append(f"📌 Тип: {html.escape(str(kind))}")
    ench = enchant_rules.current_enchant_level(data)
    atk = data.get("attack", data.get("atk"))
    if atk is not None:
        eff_atk = scaled_weapon_attack_value(int(atk), data) + ench
        lines.append(f"⚔️ Атака: <b>{eff_atk}</b>")
    defense = data.get("defense", data.get("armor"))
    if defense is not None:
        bd = int(defense)
        eff_def = scaled_armor_defense_value(bd, data) + armor_enchant_defensive_bonus(ench, data)
        lines.append(f"🛡️ Защита: <b>{eff_def}</b>")
    hpb = max(0, int(data.get("hp_bonus", 0) or 0))
    if hpb > 0:
        lines.append(f"❤️ Макс. HP: <b>+{hpb}</b>")
    if ench > 0:
        lines.append(f"✨ Заточка: {html.escape(render_enchant_stars(ench))}")
    st_line = format_item_stat_bonus_line(data)
    if st_line:
        lines.append(st_line)
    sk = data.get("set_key")
    if sk:
        set_titles = {"messenger": "Посланник башни"}
        st = set_titles.get(str(sk), str(sk))
        piece = data.get("set_piece")
        pc = f" · часть: <i>{html.escape(str(piece))}</i>" if piece else ""
        lines.append(f"🧩 <b>Набор:</b> {html.escape(st)}{pc}")
    summary = data.get("summary")
    if summary:
        lines.append(f"<i>{html.escape(str(summary))}</i>")
    return "\n".join(lines)


def item_bag_button_label(data: dict[str, Any] | None, _bag_slot: int | None = None) -> str:
    """Короткая подпись для inline-кнопки сумки/аукциона (лимит Telegram; без номера ячейки)."""
    data = data or {}
    gi = gear_icon_for_item_data(data)
    r = str(data.get("rarity") or "common").lower()
    em = RARITY_EMOJI.get(r, "⚪")
    name = str(data.get("name", "?"))[:11]
    atk = data.get("attack", data.get("atk"))
    if atk is not None:
        s = f"{gi}{em} {name} {atk}"
    else:
        s = f"{gi}{em} {name}"
    return s[:30]


def render_item_card(item: Any) -> str:
    """
    Краткая карточка предмета. Принимает dict или объект с полями name, rarity, stats.
    Полная версия — на шаге инвентаря/кузницы.
    """
    if item is None:
        return "📦 <i>Пусто</i>"
    if isinstance(item, dict):
        name = html.escape(str(item.get("name", "Предмет")))
        r = str(item.get("rarity") or "common").lower()
        em = RARITY_EMOJI.get(r, "⚪")
        ru = RARITY_NAME_RU.get(r, r)
        extra = item.get("summary")
        lines = [f"📦 <b>{name}</b> · {em} {html.escape(ru)}"]
        if extra:
            lines.append(html.escape(str(extra)))
        return "\n".join(lines)
    name = html.escape(str(getattr(item, "name", "Предмет")))
    return f"📦 <b>{name}</b>"


def element_label(element_key: str | None) -> str:
    """Человекочитаемый элемент для профиля."""
    if not element_key:
        return "—"
    mapping = {
        "fire": "🔥 Огонь",
        "ice": "❄️ Лёд",
        "lightning": "⚡ Молния",
        "dark": "🌑 Тьма",
        "light": "✨ Свет",
        "earth": "🌿 Земля",
    }
    return mapping.get(element_key, html.escape(element_key))


def element_profile_line(element_key: str | None) -> str:
    """Строка профиля «Элемент» с бонусом по ТЗ (упрощённые проценты для UI)."""
    if not element_key:
        return "🔮 Элемент: <i>нейтральный</i>"
    bonuses: dict[str, tuple[str, str]] = {
        "fire": ("Огонь", "+12% урон огнём"),
        "ice": ("Лёд", "+12% урон льдом"),
        "lightning": ("Молния", "+12% урон молнией"),
        "dark": ("Тьма", "+12% урон тьмой"),
        "light": ("Свет", "+12% урон светом"),
        "earth": ("Земля", "+12% физ. урон / контроль"),
    }
    name, bonus = bonuses.get(
        element_key,
        (html.escape(element_key), "+10% стихийный урон"),
    )
    emoji_map = {
        "fire": "🔥",
        "ice": "❄️",
        "lightning": "⚡",
        "dark": "🌑",
        "light": "✨",
        "earth": "🌿",
    }
    em = emoji_map.get(element_key, "🔮")
    return f"{em} Элемент: {name} ({bonus})"
