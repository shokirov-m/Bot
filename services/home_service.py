"""
Дом игрока: гардероб (портреты), верстак (бонус к заточке), алхимия (заглушка).
Состояние в character.meta_progress['home_v1'].
"""

from __future__ import annotations

from typing import Any

from db.models.character import Character

META_HOME = "home_v1"

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


def workbench_tier(character: Character) -> int:
    _, h = _load_home(character)
    return max(0, min(MAX_WORKBENCH_TIER, int(h.get("workbench_tier", 0))))


def set_workbench_tier(character: Character, tier: int) -> None:
    mp, h = _load_home(character)
    h["workbench_tier"] = max(0, min(MAX_WORKBENCH_TIER, int(tier)))
    _save_home(character, mp, h)


def workbench_enchant_bonus(character: Character) -> float:
    """Добавка к success_chance_bonus в roll_enchant_outcome."""
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
    """Установить портрет (ключ файла в assets/images/profile/)."""
    from utils.profile_portraits import META_PORTRAIT_KEY, PORTRAIT_ORDER

    pk = str(portrait_key).strip()[:48]
    if not pk:
        return False, "Некорректный ключ."

    allowed = set(PORTRAIT_ORDER) | set(unlocked_portrait_keys(character))
    if pk not in allowed:
        return False, "Облик недоступен — купи в лавке или выбери из базовых."

    mp = dict(character.meta_progress or {})
    mp[META_PORTRAIT_KEY] = pk
    character.meta_progress = mp
    return True, f"Портрет сменён на «{pk}»."


def alchemy_tier(character: Character) -> int:
    _, h = _load_home(character)
    return max(0, min(5, int(h.get("alchemy_tier", 0))))


def format_home_main_html(character: Character) -> str:
    wt = workbench_tier(character)
    bonus = workbench_enchant_bonus(character) * 100
    at = alchemy_tier(character)
    extras = len(unlocked_portrait_keys(character))
    return (
        "🏠 <b>Дом</b>\n"
        "<i>Здесь гардероб, мастерская и алхимия. Лавка с обликами и расходниками — кнопка ниже.</i>\n\n"
        f"🛠 Верстак: <b>ур. {wt}/{MAX_WORKBENCH_TIER}</b> "
        f"(≈<b>+{bonus:.1f}%</b> к шансу успеха заточки)\n"
        f"⚗️ Алхимический стол: <b>ур. {at}</b> <i>(скоро рецепты)</i>\n"
        f"🖼 Доп. обликов куплено: <b>{extras}</b>"
    )


def format_wardrobe_html(character: Character) -> str:
    from utils.profile_portraits import META_PORTRAIT_KEY, PORTRAIT_ORDER

    mp = character.meta_progress or {}
    cur = str(mp.get(META_PORTRAIT_KEY) or "—")
    keys = list(PORTRAIT_ORDER) + [k for k in unlocked_portrait_keys(character) if k not in PORTRAIT_ORDER]
    lines = ["👗 <b>Гардероб</b>", f"<i>Сейчас:</i> <code>{cur}</code>", "", "<b>Доступные облики:</b>"]
    for k in keys:
        mark = "✓ " if k == cur else ""
        lines.append(f"• {mark}<code>{k}</code>")
    lines.append("")
    lines.append("<i>Новые портреты — в лавке (Дом → Магазин). Положи PNG в assets/images/profile/</i>")
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
