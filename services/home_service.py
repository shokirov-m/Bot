"""
Дом игрока — 5 уровней с нарастающими бонусами.
Состояние хранится в character.meta_progress['home_v1'].

Уровни:
  1  🍺 Комната в таверне  (стартовый, бесплатно)
  2  🏠 Домик              (10 000 💰)
  3  🏘️ Дом в городе       (30 000 💰 + 10 трофеев босса)
  4  🏛️ Особняк            (100 000 💰 + 30 трофеев босса)
  5  🌆 Пентхаус           (300 000 💰 + 50 трофеев босса)

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

from db.models.character import Character

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
    1: 10_000,
    2: 30_000,
    3: 100_000,
    4: 300_000,
}

# Сколько трофеев босса нужно для улучшения на ур. N
HOME_TROPHY_COSTS: dict[int, int] = {
    3: 10,
    4: 30,
    5: 50,
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
    character.gold = int(character.gold) - gold_cost
    new_lv = lv + 1
    h["home_level"] = new_lv
    _save_home(character, mp, h)

    new_name = HOME_LEVEL_NAMES.get(new_lv, f"Ур.{new_lv}")
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
    character.gold = int(character.gold) - cost
    h["workbench_tier"] = cur + 1
    _save_home(character, mp, h)
    new_t = cur + 1
    bonus_pct = min(15.0, new_t * WORKBENCH_BONUS_PER_TIER * 100)
    return True, (
        f"−{cost} 💰\nВерстак <b>уровень {new_t}/{MAX_WORKBENCH_TIER}</b>.\n"
        f"Бонус к заточке: <b>≈{bonus_pct:.1f}%</b> к базовому шансу."
    )


def alchemy_tier(character: Character) -> int:
    _, h = _load_home(character)
    return max(0, min(5, int(h.get("alchemy_tier", 0))))


# ---------------------------------------------------------------------------
# Гардероб
# ---------------------------------------------------------------------------

def starter_portrait_keys_for_character(character: Character) -> list[str]:
    from utils.profile_portraits import META_PORTRAIT_KEY, META_REG_GENDER, portrait_keys_for_gender

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
    from utils.profile_portraits import META_PORTRAIT_KEY, portrait_title_ru

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
    from services.rest_service import format_rest_status_line_html

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
    else:
        lines.append("🛠 Верстак: <i>откроется на ур. 2</i>")

    if can_access_alchemy(character):
        at = alchemy_tier(character)
        lines.append(f"⚗️ Алхимия: стол <b>ур. {at}</b> <i>(рецепты — позже)</i>")
    else:
        lines.append("⚗️ Алхимия: <i>откроется на ур. 3</i>")

    extras = len(unlocked_portrait_keys(character))
    lines.append("")
    lines.append(f"🖼 Доп. обликов куплено: <b>{extras}</b>")

    if home_has_crown_badge(character):
        lines.append("\n👑 <b>Владелец Пентхауса Башни.</b>")

    return "\n".join(lines)


def portrait_preview_caption_html(character: Character, portrait_key: str) -> str:
    import html

    from utils.profile_portraits import META_PORTRAIT_KEY, portrait_title_ru

    mp = character.meta_progress or {}
    cur = str(mp.get(META_PORTRAIT_KEY) or "")
    pk = str(portrait_key).strip()
    title = html.escape(portrait_title_ru(pk))
    mark = " · <i>сейчас надет</i>" if pk == cur else ""
    return f"🪞 <b>Просмотр</b>\n<b>{title}</b>{mark}"


def format_wardrobe_html(character: Character) -> str:
    import html

    from utils.profile_portraits import META_PORTRAIT_KEY, portrait_title_ru

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


def format_alchemy_stub_html(character: Character) -> str:
    t = alchemy_tier(character)
    return (
        "⚗️ <b>Алхимический стол</b>\n"
        f"<i>Уровень стола: {t}</i>\n\n"
        "Зелья и рецепты появятся в следующих обновлениях.\n"
        "<i>Следи за новостями башни.</i>"
    )


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
_MINE_INTERVAL = 3 * 3600  # 3 ч — 1 ед. руды и 1 ед. корма
_MINE_CAP = 8


def _mine_farm_block(character: Character) -> tuple[dict[str, Any], dict[str, Any]]:
    mp = dict(character.meta_progress or {})
    b = dict(mp.get(META_MINE_FARM) or {})
    return mp, b


def tick_mine_farm_stores(character: Character) -> tuple[int, int]:
    """
    Накопление в фоне; возвращает (ore, food) после тика.
    """
    if home_level(character) < 4:
        return 0, 0
    mp, b = _mine_farm_block(character)
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
    n = int(dt // _MINE_INTERVAL)
    if n > 0:
        ore = min(_MINE_CAP, ore + n)
        food = min(_MINE_CAP, food + n)
        b["ore"] = ore
        b["food"] = food
        b["ts"] = last + n * _MINE_INTERVAL
        mp[META_MINE_FARM] = b
        character.meta_progress = mp
    return ore, food


def mine_farm_status_line_html(character: Character) -> str:
    if home_level(character) < 4:
        return ""
    o, f = tick_mine_farm_stores(character)
    return (
        f"⛏ <b>Шахта / ферма:</b> руда <b>{o}</b> / {_MINE_CAP} · "
        f"корм <b>{f}</b> / {_MINE_CAP} <i>(~3 ч / ед.)</i>"
    )


async def collect_mine_farm_rewards(
    session: AsyncSession,
    character: Character,
) -> tuple[bool, str]:
    """Забрать накопленное: common-материалы + корм питомцу."""
    if home_level(character) < 4:
        return False, "Нужен <b>особняк (ур. 4+)</b>."
    o, f = tick_mine_farm_stores(character)
    if o <= 0 and f <= 0:
        return False, "Пока пусто. Накопится через время (каждые 3 ч +1 к запасу)."
    from db.repository import inventory_repo
    from services.forge_service import add_materials_to_bag

    mp, b = _mine_farm_block(character)
    lines: list[str] = []
    if o > 0:
        await add_materials_to_bag(session, int(character.id), "common", o)
        lines.append(f"🪨 +{o} <b>осколка стали</b> (common)")
    if f > 0:
        from game.characters import pets as pets_mod
        pets_mod.add_pet_treats(character, f)
        lines.append(f"🥕 +{f} <b>корма</b> питомцу (запас лакомств)")

    b["ore"] = 0
    b["food"] = 0
    b["ts"] = int(time.time())
    mp[META_MINE_FARM] = b
    character.meta_progress = mp
    await session.flush()
    return True, " ".join(lines)
