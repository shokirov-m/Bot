"""
Дом игрока — 5 уровней с нарастающими бонусами.
Состояние хранится в character.meta_progress['home_v1'].

Уровни:
  1  🍺 Комната в таверне  (стартовый, бесплатно)
  2  🏠 Домик              (14 000 💰)
  3  🏘️ Дом в городе       (42 000 💰 + 15 трофеев босса)
  4  🏛️ Особняк            (130 000 💰 + 45 трофеев босса)
  5  🌆 Пентхаус           (380 000 💰 + 72 трофея босса)

Бонусы:
  ур.2  +5% золота с боёв
  ур.3  +8% опыта, передышка на −25% быстрее
  ур.4  +15% золота, +20% опыта, библиотека (+1 стат / сутки)
  ур.5  +2% к шансу лута, −50% время передышки, +1 материал при разборе, 👑 значок
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
import services.progression.character_service as character_service

META_HOME = "home_v1"

MAX_HOME_LEVEL = 5

HOME_LEVEL_NAMES: dict[int, str] = {
    1: "🍺 Комната в таверне",
    2: "🏠 Домик",
    3: "🏘️ Дом в городе",
    4: "🏛️ Особняк",
    5: "🌆 Пентхаус",
}

# Цена перехода с уровня L на L+1: золото
HOME_LEVEL_UPGRADE_COSTS: dict[int, int] = {
    1: 14_000,
    2: 42_000,
    3: 130_000,
    4: 380_000,
}

# Сколько трофеев босса нужно для улучшения на ур. N
HOME_TROPHY_COSTS: dict[int, int] = {
    3: 15,
    4: 45,
    5: 72,
}

# Верстак (сохраняется для обратной совместимости)
MAX_WORKBENCH_TIER = 5
WORKBENCH_BONUS_PER_TIER = 0.022
WORKBENCH_UPGRADE_COSTS: tuple[int, ...] = (280, 520, 950, 1600, 2600)

_LIBRARY_STATS = ("str", "dex", "int", "vit", "luck")
_LIBRARY_COOLDOWN_HOURS = 24


# ---------------------------------------------------------------------------
# Внутренние хелперы
# ---------------------------------------------------------------------------

def _load_home(character: Character) -> tuple[dict[str, Any], dict[str, Any]]:
    mp = dict(character.meta_progress or {})
    raw = mp.get(META_HOME)
    if not isinstance(raw, dict):
        raw = {}
    return mp, raw


def _save_home(character: Character, mp: dict[str, Any], home: dict[str, Any]) -> None:
    mp[META_HOME] = home
    character.meta_progress = mp
    # Явно помечаем JSON-колонку как изменённую (SQLAlchemy не всегда отслеживает мутации dict).
    try:
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(character, "meta_progress")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Уровень дома
# ---------------------------------------------------------------------------

def home_level(character: Character) -> int:
    """Уровень дома 1..MAX_HOME_LEVEL; миграция со старого формата."""
    mp, h = _load_home(character)
    raw = h.get("home_level")
    if raw is None or int(raw) <= 0:
        # миграция: старая версия имела верстак/алхимию вместо явного уровня
        lv = 1
        if int(h.get("alchemy_tier", 0)) > 0:
            lv = 3
        elif int(h.get("workbench_tier", 0)) > 0:
            lv = 2
        h["home_level"] = lv
        _save_home(character, mp, h)
        return lv
    return max(1, min(MAX_HOME_LEVEL, int(raw)))


def home_level_name(character: Character) -> str:
    return HOME_LEVEL_NAMES.get(home_level(character), "🏠 Дом")


def next_home_upgrade_cost(character: Character) -> int | None:
    """Стоимость следующего повышения в золоте; None — уже максимум."""
    lv = home_level(character)
    if lv >= MAX_HOME_LEVEL:
        return None
    return int(HOME_LEVEL_UPGRADE_COSTS[lv])


def next_home_trophy_cost(character: Character) -> int:
    """Сколько трофеев босса нужно для следующего уровня (0 если не требуется / максимум)."""
    lv = home_level(character)
    next_lv = lv + 1
    return int(HOME_TROPHY_COSTS.get(next_lv, 0))


def try_upgrade_home_level(
    character: Character,
    available_trophies: int = 0,
) -> tuple[bool, str, int]:
    """
    Повысить уровень дома.
    Возвращает (ok, сообщение, кол-во_трофеев_для_списания).
    Вызывающий код сам списывает трофеи из сумки, если ok=True и trophies>0.
    """
    lv = home_level(character)
    if lv >= MAX_HOME_LEVEL:
        return False, "Дом уже максимального уровня. 🏆", 0

    gold_cost = HOME_LEVEL_UPGRADE_COSTS.get(lv, 0)
    trophy_cost = HOME_TROPHY_COSTS.get(lv + 1, 0)

    if int(character.gold) < gold_cost:
        return False, f"Недостаточно золота. Нужно {gold_cost:,} 💰.", 0

    if trophy_cost > 0 and available_trophies < trophy_cost:
        return (
            False,
            f"Нужно {trophy_cost} 🏆 трофеев босса (есть: {available_trophies}).",
            0,
        )

    mp, h = _load_home(character)
    new_lv = lv + 1
    nm = HOME_LEVEL_NAMES.get(new_lv, f"Ур.{new_lv}")
    character_service.add_gold(
        character,
        -gold_cost,
        spend_for=f"Дом: уровень {new_lv} ({nm})",
        spend_kind="home",
    )
    h["home_level"] = new_lv
    _save_home(character, mp, h)

    new_name = nm
    trophy_line = f"\n−{trophy_cost} 🏆 трофеев босса" if trophy_cost > 0 else ""
    bonus_lines = _new_level_bonus_description(new_lv)
    msg = (
        f"−{gold_cost:,} 💰{trophy_line}\n"
        f"<b>Дом повышен до {new_lv}/{MAX_HOME_LEVEL}: {new_name}</b>"
        + (f"\n\nНовые бонусы:\n{bonus_lines}" if bonus_lines else "")
    )
    return True, msg, trophy_cost


def _new_level_bonus_description(new_lv: int) -> str:
    bonuses = {
        2: "💰 +5% золота с боёв",
        3: "📚 +8% опыта, 🛏️ передышка на 25% быстрее",
        4: "💰 +15% золота, 📚 +20% опыта, 🔬 Библиотека (+1 стат/сутки)",
        5: "🎁 +2% к луту, ⚡ передышка −50%, +1 материал при разборе, 👑 значок",
    }
    return bonuses.get(new_lv, "")


# ---------------------------------------------------------------------------
# Бонусы по уровню дома
# ---------------------------------------------------------------------------

def home_gold_bonus_pct(character: Character) -> float:
    """Процент прибавки золота (0.0 – 0.15)."""
    lv = home_level(character)
    if lv >= 4:
        return 0.15
    if lv >= 2:
        return 0.05
    return 0.0


def home_xp_bonus_pct(character: Character) -> float:
    """Процент прибавки опыта (0.0 – 0.20)."""
    lv = home_level(character)
    if lv >= 4:
        return 0.20
    if lv >= 3:
        return 0.08
    return 0.0


def home_loot_bonus_pct(character: Character) -> float:
    """Доп. шанс выпадения лута (+2% на ур.5)."""
    return 0.02 if home_level(character) >= 5 else 0.0


def home_disassemble_bonus(character: Character) -> int:
    """+1 материал при разборе на ур.5."""
    return 1 if home_level(character) >= 5 else 0


def home_has_crown_badge(character: Character) -> bool:
    """👑 значок владельца пентхауса."""
    return home_level(character) >= 5


def home_rest_duration_sec(character: Character, base_sec: int = 60) -> int:
    """Время передышки с учётом бонусов дома."""
    lv = home_level(character)
    if lv >= 5:
        return int(base_sec * 0.50)   # −50%
    if lv >= 3:
        return int(base_sec * 0.75)   # −25%
    return base_sec


# ---------------------------------------------------------------------------
# Библиотека (ур. 4+)
# ---------------------------------------------------------------------------

_LIBRARY_META_KEY = "library_last_use"


def can_access_library(character: Character) -> bool:
    return home_level(character) >= 4


def library_hours_until_ready(character: Character) -> float:
    """Часов до следующего использования библиотеки; 0.0 = доступна."""
    mp = character.meta_progress or {}
    raw = mp.get(_LIBRARY_META_KEY)
    if raw is None:
        return 0.0
    try:
        last = datetime.fromisoformat(str(raw))
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        delta = timedelta(hours=_LIBRARY_COOLDOWN_HOURS) - (datetime.now(UTC) - last)
        hours = delta.total_seconds() / 3600
        return max(0.0, hours)
    except Exception:
        return 0.0


def try_use_library(character: Character, stat_key: str) -> tuple[bool, str]:
    """
    Использовать библиотеку для +1 к стату. stat_key: str/dex/int/vit/luck.
    Возвращает (ok, сообщение_html).
    """
    if not can_access_library(character):
        return False, "Библиотека откроется на ур. 4 дома."

    stat_key = str(stat_key).strip().lower()
    if stat_key not in _LIBRARY_STATS:
        return False, "Неизвестный стат."

    hours_left = library_hours_until_ready(character)
    if hours_left > 0:
        h = int(hours_left)
        m = int((hours_left - h) * 60)
        return False, f"📚 Библиотека занята. Следующий сеанс через <b>{h}ч {m}м</b>."

    # Применяем бонус
    _STAT_COLUMN = {
        "str":  "stat_strength",
        "dex":  "stat_dexterity",
        "int":  "stat_intelligence",
        "vit":  "stat_vitality",
        "luck": "stat_luck",
    }
    _STAT_NAMES = {
        "str": "Сила", "dex": "Ловкость", "int": "Интеллект",
        "vit": "Телосложение", "luck": "Удача",
    }
    col = _STAT_COLUMN[stat_key]
    cur = int(getattr(character, col, 0) or 0)
    setattr(character, col, cur + 1)

    mp = dict(character.meta_progress or {})
    mp[_LIBRARY_META_KEY] = datetime.now(UTC).isoformat()
    character.meta_progress = mp
    try:
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(character, "meta_progress")
    except Exception:
        pass

    stat_name = _STAT_NAMES[stat_key]
    return True, (
        f"📚 <b>Библиотека</b>\n"
        f"+1 к <b>{stat_name}</b>! (теперь {cur + 1})\n"
        f"<i>Следующий сеанс через {_LIBRARY_COOLDOWN_HOURS} часов.</i>"
    )


# ---------------------------------------------------------------------------
# Верстак (обратная совместимость)
# ---------------------------------------------------------------------------

def can_access_workbench(character: Character) -> bool:
    return home_level(character) >= 2


def can_access_alchemy(character: Character) -> bool:
    return home_level(character) >= 3


def workbench_tier(character: Character) -> int:
    _, h = _load_home(character)
    return max(0, min(MAX_WORKBENCH_TIER, int(h.get("workbench_tier", 0))))


def set_workbench_tier(character: Character, tier: int) -> None:
    mp, h = _load_home(character)
    h["workbench_tier"] = max(0, min(MAX_WORKBENCH_TIER, int(tier)))
    _save_home(character, mp, h)


def workbench_enchant_bonus(character: Character) -> float:
    if not can_access_workbench(character):
        return 0.0
    t = workbench_tier(character)
    return float(min(0.15, t * WORKBENCH_BONUS_PER_TIER))


def upgrade_workbench_cost_gold(from_tier: int) -> int | None:
    i = int(from_tier)
    if i < 0 or i >= MAX_WORKBENCH_TIER:
        return None
    return int(WORKBENCH_UPGRADE_COSTS[i])


def try_upgrade_workbench(character: Character) -> tuple[bool, str]:
    if not can_access_workbench(character):
        return False, "Верстак заблокирован — сначала улучши дом до ур. 2."
    cur = workbench_tier(character)
    cost = upgrade_workbench_cost_gold(cur)
    if cost is None:
        return False, "Верстак уже максимального уровня."
    if int(character.gold) < cost:
        return False, f"Нужно {cost} золота."
    mp, h = _load_home(character)
    character_service.add_gold(
        character,
        -cost,
        spend_for=f"Дом: верстак ур. {cur + 1}",
        spend_kind="home",
    )
    h["workbench_tier"] = cur + 1
    _save_home(character, mp, h)
    new_t = cur + 1
    bonus_pct = min(15.0, new_t * WORKBENCH_BONUS_PER_TIER * 100)
    return True, (
        f"−{cost} 💰\nВерстак <b>уровень {new_t}/{MAX_WORKBENCH_TIER}</b>.\n"
        f"Бонус к заточке: <b>≈{bonus_pct:.1f}%</b> к базовому шансу."
    )


def alchemy_tier(character: Character) -> int:
    mp, h = _load_home(character)
    raw = mp.get("home_alchemy_tier", h.get("alchemy_tier"))
    if raw is None:
        return 1 if can_access_alchemy(character) else 0
    return max(0, min(ALCHEMY_TIER_MAX, int(raw)))


# ---------------------------------------------------------------------------
# Гардероб
# ---------------------------------------------------------------------------

def starter_portrait_keys_for_character(character: Character) -> list[str]:
    from utils.media.profile_portraits import META_PORTRAIT_KEY, META_REG_GENDER, portrait_keys_for_gender

    mp = character.meta_progress or {}
    rg = mp.get(META_REG_GENDER)
    if rg in ("male", "female"):
        return list(portrait_keys_for_gender(str(rg)))
    pk = str(mp.get(META_PORTRAIT_KEY) or "").strip().lower()
    if pk.startswith("female"):
        gender = "female"
    elif pk.startswith("male"):
        gender = "male"
    else:
        gender = "male"
    return list(portrait_keys_for_gender(gender))


def wardrobe_all_selectable_keys(character: Character) -> list[str]:
    starters = starter_portrait_keys_for_character(character)
    seen: set[str] = set()
    out: list[str] = []
    for k in starters:
        if k not in seen:
            seen.add(k)
            out.append(k)
    for k in unlocked_portrait_keys(character):
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def unlocked_portrait_keys(character: Character) -> list[str]:
    _, h = _load_home(character)
    raw = h.get("portrait_unlocks")
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for x in raw:
        s = str(x).strip()
        if s and s not in out:
            out.append(s[:48])
    return out


def has_portrait_unlock(character: Character, portrait_key: str) -> bool:
    return str(portrait_key).strip() in unlocked_portrait_keys(character)


def unlock_portrait(character: Character, portrait_key: str) -> None:
    pk = str(portrait_key).strip()[:48]
    if not pk:
        return
    mp, h = _load_home(character)
    cur = unlocked_portrait_keys(character)
    if pk not in cur:
        cur.append(pk)
    h["portrait_unlocks"] = cur
    _save_home(character, mp, h)


def try_set_portrait_key(character: Character, portrait_key: str) -> tuple[bool, str]:
    from utils.media.profile_portraits import META_PORTRAIT_KEY, portrait_title_ru

    pk = str(portrait_key).strip()[:48]
    if not pk:
        return False, "Некорректный ключ."
    allowed = set(wardrobe_all_selectable_keys(character))
    if pk not in allowed:
        return False, "Облик недоступен — купи в «Магазине» или выбери из базовых."
    mp = dict(character.meta_progress or {})
    mp[META_PORTRAIT_KEY] = pk
    character.meta_progress = mp
    return True, f"Выбран облик «{portrait_title_ru(pk)}»."


# ---------------------------------------------------------------------------
# Форматирование текстовых карточек
# ---------------------------------------------------------------------------

def format_home_main_html(character: Character) -> str:
    from services.progression.rest_service import format_rest_status_line_html

    hl = home_level(character)
    name = HOME_LEVEL_NAMES.get(hl, "🏠 Дом")
    cost_gold = next_home_upgrade_cost(character)
    cost_trophy = next_home_trophy_cost(character)

    if cost_gold is not None:
        next_name = HOME_LEVEL_NAMES.get(hl + 1, f"Ур.{hl + 1}")
        trophy_part = f" + {cost_trophy} 🏆" if cost_trophy > 0 else ""
        up_line = (
            f"Улучшение → <b>{next_name}</b>: <b>{cost_gold:,} 💰{trophy_part}</b>"
        )
    else:
        up_line = f"Дом: <b>максимальный уровень {MAX_HOME_LEVEL}</b>"

    lines = [
        f"🏠 <b>Дом</b>  —  <b>{name}</b>",
        f"<i>Уровень:</i> <b>{hl}</b> / {MAX_HOME_LEVEL}",
        up_line,
        "",
        format_rest_status_line_html(character),
        "",
    ]

    # Бонусы
    gold_pct = int(home_gold_bonus_pct(character) * 100)
    xp_pct   = int(home_xp_bonus_pct(character) * 100)
    loot_pct = int(home_loot_bonus_pct(character) * 100)
    bonus_parts: list[str] = []
    if gold_pct:
        bonus_parts.append(f"💰 +{gold_pct}% золота")
    if xp_pct:
        bonus_parts.append(f"📚 +{xp_pct}% опыта")
    if loot_pct:
        bonus_parts.append(f"🎁 +{loot_pct}% лут")
    if hl >= 3:
        bonus_parts.append("🛏️ передышка −25%")
    if hl >= 5:
        bonus_parts.append("⚡ −50% передышка, +1 материал при разборе, 👑")

    if bonus_parts:
        lines.append("✨ <b>Бонусы:</b> " + ", ".join(bonus_parts))
    else:
        lines.append("✨ Бонусы: улучши дом для получения.")
    lines.append("")

    # Фичи
    if can_access_library(character):
        h_left = library_hours_until_ready(character)
        if h_left > 0:
            hh = int(h_left)
            mm = int((h_left - hh) * 60)
            lib_line = f"🔬 <b>Библиотека:</b> готова через {hh}ч {mm}м"
        else:
            lib_line = "🔬 <b>Библиотека:</b> готова! (+1 стат)"
        lines.append(lib_line)
    else:
        lines.append("🔬 Библиотека: <i>откроется на ур. 4</i>")

    if hl >= 4:
        lines.append(mine_farm_status_line_html(character))

    if can_access_workbench(character):
        wt = workbench_tier(character)
        bonus = workbench_enchant_bonus(character) * 100
        lines.append(f"🛠 Верстак: <b>ур. {wt}/{MAX_WORKBENCH_TIER}</b> (≈<b>+{bonus:.1f}%</b> к заточке)")
        lines.append("🎰 Ремесленные материалы — <b>гача</b> в постройках дома.")
    else:
        lines.append("🛠 Верстак и гача: <i>откроются на ур. 2</i>")

    lines.append(
        "🔧 Крафт профессий — раздел <b>Мастерская</b> (меню или дом); домашний алхимический стол убран.",
    )

    extras = len(unlocked_portrait_keys(character))
    lines.append("")
    lines.append(f"🖼 Доп. обликов куплено: <b>{extras}</b>")

    if home_has_crown_badge(character):
        lines.append("\n👑 <b>Владелец Пентхауса Башни.</b>")

    return "\n".join(lines)


def portrait_preview_caption_html(character: Character, portrait_key: str) -> str:
    import html

    from utils.media.profile_portraits import META_PORTRAIT_KEY, portrait_title_ru

    mp = character.meta_progress or {}
    cur = str(mp.get(META_PORTRAIT_KEY) or "")
    pk = str(portrait_key).strip()
    title = html.escape(portrait_title_ru(pk))
    mark = " · <i>сейчас надет</i>" if pk == cur else ""
    return f"🪞 <b>Просмотр</b>\n<b>{title}</b>{mark}"


def format_wardrobe_html(character: Character) -> str:
    import html

    from utils.media.profile_portraits import META_PORTRAIT_KEY, portrait_title_ru

    mp = character.meta_progress or {}
    cur_raw = str(mp.get(META_PORTRAIT_KEY) or "").strip()
    cur_disp = portrait_title_ru(cur_raw) if cur_raw else "—"
    keys = wardrobe_all_selectable_keys(character)
    lines = [
        "🪞 <b>Гардероб</b>",
        f"<i>Сейчас:</i> <b>{html.escape(cur_disp)}</b>",
        "",
        "<b>Облики:</b> стартовые и купленные в «Магазине».",
        "",
        "<i>Нажми на название — превью, затем <b>Надеть</b> или <b>Назад</b>.</i>",
    ]
    for k in keys:
        mark = "✓ " if k == cur_raw else ""
        label = html.escape(portrait_title_ru(k))
        lines.append(f"• {mark}{label}")
    return "\n".join(lines)


def format_workbench_html(character: Character) -> str:
    wt = workbench_tier(character)
    bonus = workbench_enchant_bonus(character) * 100
    cost = upgrade_workbench_cost_gold(wt)
    cost_line = (
        f"Следующее улучшение: <b>{cost} 💰</b>" if cost is not None else "Максимальный уровень."
    )
    return (
        "🛠 <b>Верстак</b>\n"
        "<i>Повышает шанс успешной заточки предметов (кузница в городе).</i>\n\n"
        f"Уровень: <b>{wt}</b> / {MAX_WORKBENCH_TIER}\n"
        f"Бонус к заточке: <b>≈+{bonus:.1f}%</b> к базовому шансу\n"
        f"{cost_line}\n"
    )


# --- Alchemy Table ---
ALCHEMY_TIER_MAX = 5
ALCHEMY_UPGRADE_BASE_GOLD = 25_000

ELIXIRS = {
    "elixir_str": {"name": "Зелье Силы", "emoji": "🔴", "tier": 1, "cost_gold": 1000, "mats": {"common": 5}, "duration": 3, "buff": {"atk_mult": 1.15}},
    "elixir_def": {"name": "Зелье Защиты", "emoji": "🔵", "tier": 1, "cost_gold": 1000, "mats": {"common": 5}, "duration": 3, "buff": {"def_mult": 1.20}},
    "elixir_luck": {"name": "Зелье Удачи", "emoji": "🟡", "tier": 2, "cost_gold": 2000, "mats": {"uncommon": 3}, "duration": 3, "buff": {"drop_mult": 1.25}},
    "elixir_str_greater": {"name": "Вел. Зелье Силы", "emoji": "🔥", "tier": 3, "cost_gold": 5000, "mats": {"rare": 2}, "duration": 10, "buff": {"atk_mult": 1.25}},
    "elixir_def_greater": {"name": "Вел. Зелье Защиты", "emoji": "💎", "tier": 3, "cost_gold": 5000, "mats": {"rare": 2}, "duration": 10, "buff": {"def_mult": 1.35}},
}

def try_upgrade_alchemy(character: Character) -> tuple[bool, str]:
    if not can_access_alchemy(character):
        return False, "Алхимия откроется на ур. 3 дома."
    t = alchemy_tier(character)
    if t >= ALCHEMY_TIER_MAX: return False, "Максимальный уровень."
    cost = ALCHEMY_UPGRADE_BASE_GOLD * t
    if not character_service.try_spend_gold(
        character,
        cost,
        note=f"Дом: алхимический стол ур. {t + 1}",
        kind="home",
    ):
        return False, f"Нужно {cost:,} 💰."
    
    mp, h = _load_home(character)
    h["alchemy_tier"] = t + 1
    mp["home_alchemy_tier"] = t + 1
    _save_home(character, mp, h)
    return True, f"Стол улучшен до ур. {t+1}!"

def format_alchemy_menu_html(character: Character) -> str:
    t = alchemy_tier(character)
    mp = character.meta_progress or {}
    buffs = mp.get("active_elixirs", {})
    
    lines = [
        "⚗️ <b>Алхимический стол</b>",
        f"Уровень стола: <b>{t}</b>",
        "",
        "<i>Здесь можно преобразовывать материалы или варить усиливающие зелья.</i>",
        "",
    ]
    
    if buffs:
        lines.append("✨ <b>Активные эффекты:</b>")
        for k, v in buffs.items():
            edef = ELIXIRS.get(k)
            if edef:
                lines.append(f"• {edef['emoji']} {edef['name']}: {v} боёв осталось")
        lines.append("")
        
    lines.append("📜 <b>Доступные зелья:</b>")
    for k, v in ELIXIRS.items():
        m_line = " + ".join([f"{count} {k}" for k, count in v["mats"].items()])
        req = int(v.get("tier", 1))
        lock = "" if t >= req else f" <i>(стол ур. {req})</i>"
        lines.append(f"• {v['emoji']} <b>{v['name']}</b>: {v['cost_gold']}💰 + {m_line}{lock}")
        
    return "\n".join(lines)

async def try_brew_elixir(session: AsyncSession, character: Character, elixir_key: str) -> tuple[bool, str]:
    edef = ELIXIRS.get(elixir_key)
    if not edef: return False, "Неизвестный рецепт."
    if alchemy_tier(character) < int(edef.get("tier", 1)):
        return False, f"Нужен алхимический стол ур. {edef.get('tier', 1)}."
        
    # Check materials
    from db.repository import inventory_repo
    from game.items.materials import total_materials_in_bag
    bag_items = await inventory_repo.list_bag_items(session, character.id)
    
    for m_rarity, m_count in edef["mats"].items():
        if total_materials_in_bag(bag_items, m_rarity) < m_count:
            return False, f"Не хватает материалов: {m_rarity} ({m_count} шт)."

    if not character_service.try_spend_gold(
        character,
        edef["cost_gold"],
        note=f"Дом: зелье «{edef['name']}»",
        kind="home",
    ):
        return False, f"Нужно {edef['cost_gold']} 💰."
            
    # Consume materials
    remaining = dict(edef["mats"])
    for it in bag_items:
        d = it.item_data or {}
        if str(d.get("kind")) == "material":
            r = str(d.get("rarity"))
            if r in remaining and remaining[r] > 0:
                cnt = int(d.get("count", 1))
                take = min(cnt, remaining[r])
                if cnt <= take:
                    await session.delete(it)
                else:
                    d["count"] = cnt - take
                    it.item_data = d
                remaining[r] -= take
                
    # Apply buff
    mp = dict(character.meta_progress or {})
    buffs = dict(mp.get("active_elixirs") or {})
    buffs[elixir_key] = edef["duration"]
    mp["active_elixirs"] = buffs
    mp["elixirs_brewed"] = int(mp.get("elixirs_brewed", 0)) + 1
    character.meta_progress = mp
    return True, f"Сварено: <b>{edef['name']}</b>! Эффект на {edef['duration']} боёв."

async def try_transmute_materials(session: AsyncSession, character: Character, from_rarity: str) -> tuple[bool, str]:
    """3 -> 1 transmutation."""
    rarity_order = ["common", "uncommon", "rare", "epic", "legendary", "mythic"]
    if from_rarity not in rarity_order[:-1]: return False, "Нельзя преобразовать этот тип."
    
    idx = rarity_order.index(from_rarity)
    to_rarity = rarity_order[idx+1]
    
    from db.repository import inventory_repo
    from game.items.materials import total_materials_in_bag, material_payload
    bag_items = await inventory_repo.list_bag_items(session, character.id)
    
    if total_materials_in_bag(bag_items, from_rarity) < 3:
        return False, f"Нужно минимум 3 материала {from_rarity}."
        
    # Consume
    remaining = 3
    for it in bag_items:
        d = it.item_data or {}
        if str(d.get("kind")) == "material" and str(d.get("rarity")) == from_rarity:
            cnt = int(d.get("count", 1))
            take = min(cnt, remaining)
            if cnt <= take:
                await session.delete(it)
            else:
                d["count"] = cnt - take
                it.item_data = d
            remaining -= take
            if remaining <= 0: break
            
    # Add new
    slot = await inventory_repo.first_free_bag_slot(session, character.id)
    if slot is not None:
        await inventory_repo.add_bag_item(session, character.id, material_payload(to_rarity, 1), bag_slot=slot)
    else:
        # Fallback to pending or just add (already checked 3 consumed, so at least 1 slot is freed?)
        # Actually if we consumed a stack, we might have freed a slot or just reduced count.
        # But since we just deleted/modified items, there is room.
        await inventory_repo.add_bag_item(session, character.id, material_payload(to_rarity, 1))

    return True, f"Трансмутация успешна! Получен 1 {to_rarity} материал."


def format_library_html(character: Character) -> str:
    h_left = library_hours_until_ready(character)
    if h_left > 0:
        hh = int(h_left)
        mm = int((h_left - hh) * 60)
        ready_line = f"⏳ Следующий сеанс через <b>{hh}ч {mm}м</b>."
    else:
        ready_line = "✅ Библиотека готова! Выбери стат для изучения."
    return (
        "🔬 <b>Библиотека особняка</b>\n"
        "<i>Раз в 24 часа можно получить +1 к любому стату.</i>\n\n"
        + ready_line
    )


# ---------------------------------------------------------------------------
# Шахта / ферма (AFK) — с ур. 4; meta home_mine_farm_v1
# ---------------------------------------------------------------------------

META_MINE_FARM = "home_mine_farm_v1"
_MINE_INTERVAL_BASE = 3 * 3600  # 3 ч — 1 ед. руды и 1 ед. корма
_MINE_CAP_BASE = 8

MINE_PURCHASE_GOLD = 50_000
NPC_HIRE_GOLD = 25_000
MINE_UPGRADE_BASE_GOLD = 30_000

def is_mine_unlocked(character: Character) -> bool:
    """Шахта доступна для покупки на 4 уровне дома."""
    return home_level(character) >= 4

def _mine_farm_block(character: Character) -> tuple[dict[str, Any], dict[str, Any]]:
    mp = dict(character.meta_progress or {})
    b = dict(mp.get(META_MINE_FARM) or {})
    return mp, b

def is_mine_bought(character: Character) -> bool:
    _, b = _mine_farm_block(character)
    return bool(b.get("bought", False))

def is_npc_hired(character: Character) -> bool:
    _, b = _mine_farm_block(character)
    return bool(b.get("npc_hired", False))

def mine_level(character: Character) -> int:
    _, b = _mine_farm_block(character)
    return max(1, int(b.get("level", 1)))

def try_buy_mine(character: Character) -> tuple[bool, str]:
    if not is_mine_unlocked(character):
        return False, "Нужен особняк (ур. 4) для открытия шахты."
    if is_mine_bought(character):
        return False, "Шахта уже куплена."
    if int(character.gold) < MINE_PURCHASE_GOLD:
        return False, f"Нужно {MINE_PURCHASE_GOLD:,} 💰."
    
    mp, b = _mine_farm_block(character)
    character_service.add_gold(
        character,
        -MINE_PURCHASE_GOLD,
        spend_for="Дом: покупка шахты и фермы",
        spend_kind="home",
    )
    b["bought"] = True
    b["ts"] = int(time.time())
    b["level"] = 1
    mp[META_MINE_FARM] = b
    character.meta_progress = mp
    return True, f"−{MINE_PURCHASE_GOLD:,} 💰\n<b>Шахта и ферма открыты!</b> Теперь они будут приносить ресурсы."

def try_hire_npc(character: Character) -> tuple[bool, str]:
    if not is_mine_bought(character):
        return False, "Сначала купи шахту."
    if is_npc_hired(character):
        return False, "Рабочий уже нанят."
    if int(character.gold) < NPC_HIRE_GOLD:
        return False, f"Нужно {NPC_HIRE_GOLD:,} 💰."
    
    mp, b = _mine_farm_block(character)
    character_service.add_gold(
        character,
        -NPC_HIRE_GOLD,
        spend_for="Дом: найм рабочего на шахте",
        spend_kind="home",
    )
    b["npc_hired"] = True
    mp[META_MINE_FARM] = b
    character.meta_progress = mp
    return True, f"−{NPC_HIRE_GOLD:,} 💰\n<b>Рабочий нанят!</b> Скорость добычи и вместимость склада увеличены."

def mine_upgrade_cost(character: Character) -> int | None:
    lv = mine_level(character)
    if lv >= 5: return None
    return MINE_UPGRADE_BASE_GOLD * lv

def try_upgrade_mine(character: Character) -> tuple[bool, str]:
    if not is_mine_bought(character):
        return False, "Сначала купи шахту."
    lv = mine_level(character)
    cost = mine_upgrade_cost(character)
    if cost is None:
        return False, "Максимальный уровень шахты."
    if int(character.gold) < cost:
        return False, f"Нужно {cost:,} 💰."
    
    mp, b = _mine_farm_block(character)
    character_service.add_gold(
        character,
        -cost,
        spend_for=f"Дом: улучшение шахты (ур. {lv + 1})",
        spend_kind="home",
    )
    b["level"] = lv + 1
    mp[META_MINE_FARM] = b
    character.meta_progress = mp
    return True, f"−{cost:,} 💰\n<b>Шахта улучшена до уровня {lv+1}!</b>"


def tick_mine_farm_stores(character: Character) -> tuple[int, int]:
    """
    Накопление в фоне; возвращает (ore, food) после тика.
    """
    if not is_mine_bought(character):
        return 0, 0
    mp, b = _mine_farm_block(character)
    
    lv = mine_level(character)
    npc = is_npc_hired(character)
    
    # NPC ускоряет добычу на 30%, каждый уровень шахты снижает интервал на 10%
    interval = _MINE_INTERVAL_BASE * (0.9 ** (lv - 1))
    if npc:
        interval *= 0.7
    
    # Вместимость: база 8 + 4 за уровень, +10 если есть NPC
    cap = _MINE_CAP_BASE + (lv - 1) * 4
    if npc:
        cap += 10
        
    now = int(time.time())
    last = int(b.get("ts", 0) or 0)
    ore = int(b.get("ore", 0) or 0)
    food = int(b.get("food", 0) or 0)
    
    if last <= 0:
        b["ts"] = now
        b["ore"] = 0
        b["food"] = 0
        mp[META_MINE_FARM] = b
        character.meta_progress = mp
        return 0, 0
        
    dt = max(0, now - last)
    n = int(dt // interval)
    if n > 0:
        ore = min(cap, ore + n)
        food = min(cap, food + n)
        b["ore"] = ore
        b["food"] = food
        b["ts"] = last + int(n * interval)
        mp[META_MINE_FARM] = b
        character.meta_progress = mp
    return ore, food


def mine_farm_status_line_html(character: Character) -> str:
    if not is_mine_unlocked(character):
        return ""
    if not is_mine_bought(character):
        return f"⛏ <b>Шахта:</b> можно купить за {MINE_PURCHASE_GOLD:,} 💰"
    
    o, f = tick_mine_farm_stores(character)
    lv = mine_level(character)
    npc_icon = "👷" if is_npc_hired(character) else "❌"
    
    # Расчет макс капа для отображения
    cap = _MINE_CAP_BASE + (lv - 1) * 4
    if is_npc_hired(character): cap += 10
    
    return (
        f"⛏ <b>Шахта (ур. {lv}):</b> руда <b>{o}</b>/{cap} · "
        f"корм <b>{f}</b>/{cap} {npc_icon}"
    )


async def collect_mine_farm_rewards(
    session: AsyncSession,
    character: Character,
) -> tuple[bool, str]:
    """Забрать накопленное: common-материалы + корм питомцу."""
    if not is_mine_bought(character):
        return False, "Шахта не куплена."
    o, f = tick_mine_farm_stores(character)
    if o <= 0 and f <= 0:
        return False, "Пока пусто. Ресурсы копятся со временем."
    
    from sqlalchemy.orm.attributes import flag_modified
    from services.economy.forge_service import add_materials_to_bag

    lines: list[str] = []
    ore_ok = True
    if o > 0:
        ore_ok = await add_materials_to_bag(session, int(character.id), "common", o)
        if ore_ok:
            lines.append(f"🪨 +{o} <b>осколка стали</b>")
        else:
            lines.append(
                f"⚠️ Руда ({o} ед.) не поместилась в сумку — нет свободной ячейки. Освободи место и нажми «Забрать» снова."
            )
    if f > 0:
        # Прямое начисление корма в meta питомцев (полностью заменяет meta_progress внутри функции)
        from game.characters import pets as pets_mod
        pets_mod.add_pet_treats(character, f)
        lines.append(f"🥕 +{f} <b>корма</b>")

    # После add_pet_treats нужно брать свежий meta_progress — иначе затрём питомцев и прочие ключи старым mp.
    mp, b = _mine_farm_block(character)
    if ore_ok:
        b["ore"] = 0
    if f > 0:
        b["food"] = 0
    b["ts"] = int(time.time())
    mp[META_MINE_FARM] = b
    character.meta_progress = mp
    try:
        flag_modified(character, "meta_progress")
    except Exception:
        pass
    await session.flush()

    if o > 0 and not ore_ok and f <= 0:
        return False, lines[0] if lines else "Сумка полна."
    return True, " ".join(lines)


# ---------------------------------------------------------------------------
# Тренировка питомцев (прокачка за корм из фермы)
# ---------------------------------------------------------------------------

def try_feed_pet_for_xp(character: Character, pet_key: str) -> tuple[bool, str]:
    """Потратить 1 ед. корма (из запаса treats) для +50 XP питомцу."""
    from game.characters import pets as pets_mod
    mp, st = pets_mod._pets_meta(character)
    
    treats = int(st.get("treats") or 0)
    if treats <= 0:
        return False, "Нет корма. Собери его на ферме (ур. 4 дома)."
    
    owned = pets_mod.owned_keys(character)
    if pet_key not in owned:
        return False, "У тебя нет этого питомца."
    
    px = st.get("pet_xp") or {}
    if not isinstance(px, dict): px = {}
    cur_xp = int(px.get(pet_key) or 0)
    
    # Лимит уровня 10 (2000 XP)
    if cur_xp >= 2000:
        return False, "Питомец уже максимального уровня."
    
    # Тратим 1 корм -> +50 XP
    st["treats"] = treats - 1
    px[pet_key] = cur_xp + 50
    st["pet_xp"] = px
    mp[pets_mod.META_KEY] = st
    character.meta_progress = mp
    
    d = pets_mod._all_defs().get(pet_key)
    p_name = d.name_ru if d else pet_key
    return True, f"🍱 Ты покормил <b>{p_name}</b>! +50 XP (теперь {cur_xp + 50})."


def format_mine_farm_menu_html(character: Character) -> str:
    if not is_mine_unlocked(character):
        return "Шахта и ферма открываются в <b>Особняке</b> (ур. 4 дома)."
    
    if not is_mine_bought(character):
        return (
            "⛏ <b>Заброшенная шахта</b>\n\n"
            "На заднем дворе твоего особняка есть вход в старую шахту. "
            "Если расчистить завалы, она начнет приносить ценную руду и ресурсы для фермы.\n\n"
            f"Цена расчистки: <b>{MINE_PURCHASE_GOLD:,} 💰</b>"
        )
    
    o, f = tick_mine_farm_stores(character)
    lv = mine_level(character)
    npc = is_npc_hired(character)

    cap = _MINE_CAP_BASE + (lv - 1) * 4
    if npc:
        cap += 10

    ore_line = f"• Руда: <b>{o}/{cap}</b> ед."
    food_line = f"• Корм: <b>{f}/{cap}</b> ед."
    if o >= cap:
        ore_line += " ⚠️ <b>Склад полон!</b> Забери руду — иначе новая не копится."
    if f >= cap:
        food_line += " ⚠️ <b>Склад полон!</b> Забери корм."

    lines = [
        f"⛏ <b>Шахта и Ферма (уровень {lv})</b>",
        f"Статус рабочего: {'👷 Нанят' if npc else '❌ Не нанят'}",
        "",
        "📦 <b>Склад:</b>",
        ore_line,
        food_line,
        "",
        "📌 <b>Куда идут ресурсы после сбора?</b>",
        "• <b>Руда</b> → в твою сумку как материал для заточки (Кузница → Заточить).",
        "• <b>Корм</b> → запас для тренировки питомцев (кнопка «Питомцы»).",
        "",
        "<i>Ресурсы копятся автоматически. Рабочий ускоряет процесс и увеличивает склад.</i>",
    ]

    if not npc:
        lines.append(f"\n🤝 Можно нанять рабочего за <b>{NPC_HIRE_GOLD:,} 💰</b>")

    up_cost = mine_upgrade_cost(character)
    if up_cost:
        lines.append(f"⬆ Улучшение шахты: <b>{up_cost:,} 💰</b>")

    return "\n".join(lines)
