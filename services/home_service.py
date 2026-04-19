"""
Дом игрока: гардероб (портреты), верстак (бонус к заточке), алхимия (заглушка).
Состояние в character.meta_progress['home_v1'].
"""

from __future__ import annotations

from typing import Any

from db.models.character import Character

META_HOME = "home_v1"

# Уровень дома: 1 — только гардероб и передышка; 2 (+2000 💰) — верстак; 3 (+8000 💰) — алхимия.
MAX_HOME_LEVEL = 3
# Цена перехода с уровня L на L+1 (золото)
HOME_LEVEL_UPGRADE_COSTS: dict[int, int] = {
    1: 2000,
    2: 8000,
}

# Уровень верстака 0..5 (0 — не куплен базовый чертёж). Бонус к шансу успеха заточки (абсолютный).
MAX_WORKBENCH_TIER = 5
WORKBENCH_BONUS_PER_TIER = 0.022  # +2.2% за уровень, макс ~11%

# Цена улучшения с уровня tier -> tier+1 (золото)
WORKBENCH_UPGRADE_COSTS: tuple[int, ...] = (280, 520, 950, 1600, 2600)


def _load_home(character: Character) -> dict[str, Any]:
    mp = dict(character.meta_progress or {})
    raw = mp.get(META_HOME)
    if not isinstance(raw, dict):
        raw = {}
    return mp, raw


def _save_home(character: Character, mp: dict[str, Any], home: dict[str, Any]) -> None:
    mp[META_HOME] = home
    character.meta_progress = mp


def home_level(character: Character) -> int:
    """Уровень дома 1..MAX_HOME_LEVEL; для старых сохранений — миграция по верстаку/алхимии."""
    mp, h = _load_home(character)
    raw = h.get("home_level")
    if raw is None or int(raw) <= 0:
        lv = 1
        if int(h.get("alchemy_tier", 0)) > 0:
            lv = 3
        elif int(h.get("workbench_tier", 0)) > 0:
            lv = 2
        h["home_level"] = lv
        _save_home(character, mp, h)
        return lv
    return max(1, min(MAX_HOME_LEVEL, int(raw)))


def next_home_upgrade_cost(character: Character) -> int | None:
    """Стоимость следующего повышения уровня дома; None если уже максимум."""
    lv = home_level(character)
    if lv >= MAX_HOME_LEVEL:
        return None
    return int(HOME_LEVEL_UPGRADE_COSTS[lv])


def can_access_workbench(character: Character) -> bool:
    return home_level(character) >= 2


def can_access_alchemy(character: Character) -> bool:
    return home_level(character) >= 3


def try_upgrade_home_level(character: Character) -> tuple[bool, str]:
    """Повысить уровень дома за золото (открывает верстак / алхимию)."""
    lv = home_level(character)
    if lv >= MAX_HOME_LEVEL:
        return False, "Дом уже максимального уровня."
    cost = next_home_upgrade_cost(character)
    if cost is None:
        return False, "Нельзя улучшить."
    if int(character.gold) < cost:
        return False, f"Нужно {cost} 💰."
    mp, h = _load_home(character)
    character.gold = int(character.gold) - cost
    new_lv = lv + 1
    h["home_level"] = new_lv
    _save_home(character, mp, h)
    unlocked: list[str] = []
    if new_lv >= 2 and lv < 2:
        unlocked.append("🛠 Верстак")
    if new_lv >= 3 and lv < 3:
        unlocked.append("⚗️ Алхимический стол")
    extra = ""
    if unlocked:
        extra = "\nОткрыто: " + ", ".join(unlocked)
    return True, (
        f"−{cost} 💰\n<b>Дом ур. {new_lv}/{MAX_HOME_LEVEL}</b>.{extra}"
    )


def workbench_tier(character: Character) -> int:
    _, h = _load_home(character)
    return max(0, min(MAX_WORKBENCH_TIER, int(h.get("workbench_tier", 0))))


def set_workbench_tier(character: Character, tier: int) -> None:
    mp, h = _load_home(character)
    h["workbench_tier"] = max(0, min(MAX_WORKBENCH_TIER, int(tier)))
    _save_home(character, mp, h)


def workbench_enchant_bonus(character: Character) -> float:
    """Добавка к success_chance_bonus в roll_enchant_outcome."""
    if not can_access_workbench(character):
        return 0.0
    t = workbench_tier(character)
    return float(min(0.15, t * WORKBENCH_BONUS_PER_TIER))


def upgrade_workbench_cost_gold(from_tier: int) -> int | None:
    """Цена перехода from_tier -> from_tier+1; None если уже максимум."""
    i = int(from_tier)
    if i < 0 or i >= MAX_WORKBENCH_TIER:
        return None
    return int(WORKBENCH_UPGRADE_COSTS[i])


def try_upgrade_workbench(character: Character) -> tuple[bool, str]:
    """Купить следующий уровень верстака за золото (из экрана дома)."""
    if not can_access_workbench(character):
        return False, "Верстак заблокирован — сначала улучши дом до ур. 2 (кнопка «Улучшить дом»)."
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
        f"Бонус к успешной заточке: <b>≈{bonus_pct:.1f}%</b> к базовому шансу."
    )


def starter_portrait_keys_for_character(character: Character) -> list[str]:
    """Три базовых облика пола при регистрации (meta) или эвристика по текущему ключу."""
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
    """Стартовые облики своего пола + купленные; без дубликатов."""
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
    pk = str(portrait_key).strip()
    return pk in unlocked_portrait_keys(character)


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
    """Установить активный портрет профиля."""
    from utils.profile_portraits import META_PORTRAIT_KEY, portrait_title_ru

    pk = str(portrait_key).strip()[:48]
    if not pk:
        return False, "Некорректный ключ."

    allowed = set(wardrobe_all_selectable_keys(character))
    if pk not in allowed:
        return False, "Облик недоступен — купи облик в «Магазине» или выбери из базовых."

    mp = dict(character.meta_progress or {})
    mp[META_PORTRAIT_KEY] = pk
    character.meta_progress = mp
    return True, f"Выбран облик «{portrait_title_ru(pk)}»."


def alchemy_tier(character: Character) -> int:
    _, h = _load_home(character)
    return max(0, min(5, int(h.get("alchemy_tier", 0))))


def format_home_main_html(character: Character) -> str:
    from services.rest_service import format_rest_status_line_html

    hl = home_level(character)
    extras = len(unlocked_portrait_keys(character))
    cost = next_home_upgrade_cost(character)
    up_line = (
        f"Следующее улучшение дома: <b>{cost} 💰</b> "
        f"(ур. {hl} → {hl + 1})"
        if cost is not None
        else f"Дом: <b>макс. ур. {MAX_HOME_LEVEL}</b>"
    )
    lines = [
        "🏠 <b>Дом</b>",
        f"<i>Уровень дома:</i> <b>{hl}</b> / {MAX_HOME_LEVEL}",
        up_line,
        "",
        format_rest_status_line_html(character),
        "",
        "🪞 <b>Гардероб</b> и 🛏️ <b>передышка</b> доступны всегда.",
        "Новые облики для профиля покупай в главном меню → <b>«Магазин»</b> → раздел обликов.",
        "",
    ]
    if can_access_workbench(character):
        wt = workbench_tier(character)
        bonus = workbench_enchant_bonus(character) * 100
        lines.append(
            f"🛠 Верстак: <b>ур. {wt}/{MAX_WORKBENCH_TIER}</b> "
            f"(≈<b>+{bonus:.1f}%</b> к заточке)"
        )
    else:
        lines.append("🛠 Верстак: <i>откроется с домом ур. 2</i>")
    if can_access_alchemy(character):
        at = alchemy_tier(character)
        lines.append(f"⚗️ Алхимия: стол <b>ур. {at}</b> <i>(рецепты — позже)</i>")
    else:
        lines.append("⚗️ Алхимия: <i>откроется с домом ур. 3</i>")
    lines.append("")
    lines.append(f"🖼 Доп. обликов куплено: <b>{extras}</b>")
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
        f"{cost_line}\n\n"
        "🔧 <b>Разборка экипировки</b> — <i>скоро</i>.\n"
    )


def format_alchemy_stub_html(character: Character) -> str:
    t = alchemy_tier(character)
    return (
        "⚗️ <b>Алхимический стол</b>\n"
        f"<i>Уровень стола: {t}</i>\n\n"
        "Зелья и рецепты появятся в следующих обновлениях.\n"
        "<i>Следи за новостями башни.</i>"
    )
