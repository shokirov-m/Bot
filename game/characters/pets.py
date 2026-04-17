"""
Питомцы: призыв за золото (лавка городского хаба; редкий пул после открытия 48 этажа).
Бонусы суммируются через passive_combat_modifiers_merged (как глобальные пассивы).
"""

from __future__ import annotations

import html
import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from bot.i18n import t
from db.models.character import Character
META_KEY = "pets_v1"

# Стоимость и шансы (золото). Призыв с этажа отключён — только город (см. try_city_pet_summon).
GACHA_FLOOR_BASIC = 8
GACHA_FLOOR_RARE = 48
GACHA_COST_BASIC = 300  # было 100, +200
GACHA_COST_RARE = 550  # было 350, +200
# ×3: три одиночных + небольшая надбавка к сумме (как раньше +40 / +175 к тройному базовому).
CITY_SUMMON_COST_X3_BASIC = 940  # 3×300 + 40
CITY_SUMMON_COST_X3_RARE = 1825  # 3×550 + 175
DUPLICATE_REFUND_RATIO = 0.25  # доля от стоимости броска при дубликате

# Лимит бросков призыва из города за календарный день UTC (×3 = три броска).
CITY_PET_PULLS_LIMIT_PER_UTC_DAY = 3

# Оставлено для смены активного питомца на этажах с «алтарём» (8 и 48).
_PET_GACHA_FLOORS: dict[int, tuple[int, bool]] = {
    GACHA_FLOOR_BASIC: (GACHA_COST_BASIC, False),
    GACHA_FLOOR_RARE: (GACHA_COST_RARE, True),
}


def is_pet_gacha_floor(floor_number: int) -> bool:
    return int(floor_number) in _PET_GACHA_FLOORS


def pet_gacha_floors_for_pet_switch() -> frozenset[int]:
    return frozenset(_PET_GACHA_FLOORS.keys())


@dataclass(frozen=True, slots=True)
class PetDef:
    key: str
    name_ru: str
    emoji: str
    blurb: str
    passive: dict[str, float | int]


# Обычный пул (этаж 8)
PET_BASIC_POOL: tuple[PetDef, ...] = (
    PetDef(
        "pet_moss_sprite",
        "Моховой спрайт",
        "🌱",
        "+1 к защите в бою.",
        {"def_bonus": 1.0},
    ),
    PetDef(
        "pet_cinder_fox",
        "Угольный лис",
        "🦊",
        "+2% к шансу крита.",
        {"crit_bonus": 0.02},
    ),
    PetDef(
        "pet_drip_slime",
        "Капельный слизень",
        "💧",
        "+1 MP реген / ход (бой).",
        {"mp_regen_turn": 1},
    ),
    PetDef(
        "pet_iron_beetle",
        "Железный жук",
        "🪲",
        "+3% к магическим навыкам.",
        {"mag_bonus_percent": 3},
    ),
    PetDef(
        "pet_gloom_moth",
        "Мрачная моль",
        "🦋",
        "+2% к уклонению.",
        {"dodge_bonus": 0.02},
    ),
)

# Два редких — в пуле после открытия 48 этажа (добавляются к базовому пулу при броске)
PET_RARE_EXCLUSIVE: tuple[PetDef, ...] = (
    PetDef(
        "pet_void_wisp",
        "Осколок пустоты",
        "🌑",
        "+4% крит, +2 защита.",
        {"crit_bonus": 0.04, "def_bonus": 2.0},
    ),
    PetDef(
        "pet_sun_cub",
        "Солнечный зверёк",
        "☀️",
        "+6% магия, +1 MP/ход.",
        {"mag_bonus_percent": 6, "mp_regen_turn": 1},
    ),
)


def _all_defs() -> dict[str, PetDef]:
    out: dict[str, PetDef] = {}
    for p in PET_BASIC_POOL + PET_RARE_EXCLUSIVE:
        out[p.key] = p
    return out


def _character_meta_root(character: Character) -> dict[str, Any]:
    """Корень meta_progress: иногда в БД приходит JSON-строка целиком."""
    raw = character.meta_progress
    if raw is None:
        return {}
    if isinstance(raw, str):
        try:
            obj = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}
        return dict(obj) if isinstance(obj, dict) else {}
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def _coerce_nested_dict(val: Any) -> dict[str, Any]:
    """Вложенный объект (pets_v1): dict или JSON-строка."""
    if isinstance(val, dict):
        return dict(val)
    if isinstance(val, str):
        try:
            obj = json.loads(val)
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}
        return dict(obj) if isinstance(obj, dict) else {}
    return {}


def _normalize_owned_list(val: Any) -> list[str]:
    """Список ключей питомцев: list/tuple или JSON-массив в строке."""
    if val is None:
        return []
    if isinstance(val, str):
        try:
            val = json.loads(val)
        except (json.JSONDecodeError, TypeError, ValueError):
            return []
    if isinstance(val, tuple):
        val = list(val)
    if not isinstance(val, list):
        return []
    return [str(x).strip() for x in val if str(x).strip()]


def _pets_meta(character: Character) -> tuple[dict[str, Any], dict[str, Any]]:
    mp = _character_meta_root(character)
    st = _coerce_nested_dict(mp.get(META_KEY))
    return mp, st


def owned_keys(character: Character) -> list[str]:
    _, st = _pets_meta(character)
    return _normalize_owned_list(st.get("owned"))


def repair_pet_meta_if_needed(character: Character) -> bool:
    """
    Исправить meta pets_v1 в памяти: JSON-строка, owned не list/tuple/str, active не из owned.
    Возвращает True, если нужен flush/commit.
    """
    mp0 = character.meta_progress
    mp = _character_meta_root(character)
    raw_meta = mp.get(META_KEY)
    changed = isinstance(mp0, str) or isinstance(raw_meta, str)
    if isinstance(raw_meta, dict):
        po = raw_meta.get("owned")
        if po is not None and not isinstance(po, (list, tuple, str)):
            changed = True

    st = dict(_coerce_nested_dict(raw_meta))
    for k in ("city_pull_date", "city_pulls"):
        if isinstance(raw_meta, dict) and k in raw_meta:
            st[k] = raw_meta[k]

    owned = _normalize_owned_list(st.get("owned"))
    seen: set[str] = set()
    owned = [x for x in owned if x not in seen and not seen.add(x)]
    if (owned or raw_meta is not None) and st.get("owned") != owned:
        st["owned"] = owned
        changed = True

    act = str(st.get("active") or "").strip() or None
    if act and owned and act not in owned:
        st["active"] = owned[0]
        changed = True
    elif not act and owned:
        st["active"] = owned[0]
        changed = True
    elif act and not owned:
        st["active"] = None
        changed = True

    if changed:
        mp[META_KEY] = st
        character.meta_progress = dict(mp)
        return True
    return False


def active_pet_key(character: Character) -> str | None:
    _, st = _pets_meta(character)
    a = st.get("active")
    return str(a).strip() if a else None


def active_pet_display(character: Character) -> str | None:
    key = active_pet_key(character)
    if not key:
        return None
    d = _all_defs().get(key)
    if d is None:
        return None
    return f"{d.emoji} {d.name_ru}"


def pet_passive_delta(character: Character) -> dict[str, float | int]:
    key = active_pet_key(character)
    if not key:
        return {}
    d = _all_defs().get(key)
    if d is None:
        return {}
    return dict(d.passive)


def format_pet_passive_plain(passive: dict[str, float | int], *, locale: str) -> str:
    """Краткое описание пассивки питомца (RU/EN) для UI."""
    loc = "en" if str(locale).lower().startswith("en") else "ru"
    parts: list[str] = []
    if "def_bonus" in passive:
        v = float(passive["def_bonus"])
        vs = str(int(v)) if v == int(v) else str(v)
        parts.append(
            f"+{vs} {'defense in combat' if loc == 'en' else 'к защите в бою'}",
        )
    if "crit_bonus" in passive:
        p = round(float(passive["crit_bonus"]) * 100.0, 1)
        parts.append(
            f"+{p}% {'crit chance' if loc == 'en' else 'к шансу крита'}",
        )
    if "dodge_bonus" in passive:
        p = round(float(passive["dodge_bonus"]) * 100.0, 1)
        parts.append(
            f"+{p}% {'dodge' if loc == 'en' else 'к уклонению'}",
        )
    if "mp_regen_turn" in passive:
        v = int(passive["mp_regen_turn"])
        parts.append(
            f"+{v} MP/{'turn' if loc == 'en' else 'ход'}",
        )
    if "mag_bonus_percent" in passive:
        v = int(passive["mag_bonus_percent"])
        parts.append(
            f"+{v}% {'magic skills' if loc == 'en' else 'к маг. навыкам'}",
        )
    sep = " · " if loc == "en" else " · "
    return sep.join(parts)


def format_pet_passive_status_compact(passive: dict[str, float | int], *, locale: str) -> str:
    """Одна строка для статуса: «+4% крит, +2 защита»."""
    if not passive:
        return ""
    loc = "en" if str(locale).lower().startswith("en") else "ru"
    parts: list[str] = []
    if "crit_bonus" in passive:
        p = round(float(passive["crit_bonus"]) * 100.0, 1)
        ps = str(int(p)) if abs(p - int(p)) < 1e-9 else str(p)
        parts.append(f"+{ps}% crit" if loc == "en" else f"+{ps}% крит")
    if "dodge_bonus" in passive:
        p = round(float(passive["dodge_bonus"]) * 100.0, 1)
        ps = str(int(p)) if abs(p - int(p)) < 1e-9 else str(p)
        parts.append(f"+{ps}% dodge" if loc == "en" else f"+{ps}% уклон")
    if "def_bonus" in passive:
        v = float(passive["def_bonus"])
        vs = str(int(v)) if v == int(v) else str(v)
        parts.append(f"+{vs} defense" if loc == "en" else f"+{vs} защита")
    if "mp_regen_turn" in passive:
        v = int(passive["mp_regen_turn"])
        parts.append(f"+{v} MP/turn" if loc == "en" else f"+{v} MP/ход")
    if "mag_bonus_percent" in passive:
        v = int(passive["mag_bonus_percent"])
        parts.append(f"+{v}% magic" if loc == "en" else f"+{v}% маг.")
    return ", ".join(parts)


def format_pet_profile_block_html(character: Character, *, locale: str, compact_status_line: bool = False) -> str:
    """
    Блок для статуса / полных характеристик: что дают питомцы и как выбрать активного.
    """
    loc = "en" if str(locale).lower().startswith("en") else "ru"
    own = owned_keys(character)
    if not own:
        if loc == "en":
            return (
                "🐾 <b>Pets</b> — <i>summon in <b>City</b> (shop). "
                "Each has a <b>passive</b> bonus in combat; only <b>one</b> pet is active per fight. "
                "Pick the active pet in <b>Status</b> (button) or on <b>floors 8 and 48</b> once unlocked.</i>"
            )
        return (
            "🐾 <b>Питомцы</b> — <i>призыв в <b>Городе</b> (лавка). "
            "У каждого свой <b>пассивный</b> бонус в бою; в каждом бою действует только <b>один</b> активный питомец. "
            "Выбрать его — кнопка <b>«Питомец»</b> в статусе или этажи <b>8 и 48</b> (когда открыты).</i>"
        )
    disp = active_pet_display(character) or "—"
    if compact_status_line:
        label = "Pet" if loc == "en" else "Питомец"
        extras = format_pet_passive_status_compact(pet_passive_delta(character), locale=locale)
        esc_d = html.escape(disp)
        if extras:
            return f"🐾 {label}: {esc_d} {html.escape(extras)}."
        return f"🐾 {label}: {esc_d}."
    key = active_pet_key(character)
    d = _all_defs().get(key) if key else None
    blur = html.escape(d.blurb) if d else ""
    passive = format_pet_passive_plain(pet_passive_delta(character), locale=locale)
    passive_html = html.escape(passive) if passive else ""
    if loc == "en":
        switch = (
            "<i>Use the <b>Pet</b> button in <b>Status</b> to open the list and equip one; "
            "or floors <b>8 / 48</b> when unlocked.</i>"
        )
        body = (
            f"🐾 <b>Active in combat:</b> {html.escape(disp)}"
            + (f"\n<i>{blur}</i>" if blur else "")
            + (f"\n<b>Passive:</b> <i>{passive_html}</i>" if passive_html else "")
            + f"\n{switch}"
        )
        return body
    switch_ru = (
        "<i>Сменить активного: кнопка «Питомец» в <b>статусе</b> — откроется список; "
        "или этажи <b>8 и 48</b>, когда доступны.</i>"
    )
    return (
        f"🐾 <b>В бою сейчас:</b> {html.escape(disp)}"
        + (f"\n<i>{blur}</i>" if blur else "")
        + (f"\n<b>Пассив:</b> <i>{passive_html}</i>" if passive_html else "")
        + f"\n{switch_ru}"
    )


def format_pet_combat_highlight_line_html(character: Character, *, locale: str) -> str:
    """
    Короткая строка «Питомец: +N% …» для экрана боя (видно без раскрытия пассива).
    Приоритет: маг. %, затем крит/уклонение как проценты.
    """
    d = pet_passive_delta(character)
    if not d:
        return ""
    loc = "en" if str(locale).lower().startswith("en") else "ru"
    mag = int(d.get("mag_bonus_percent") or 0)
    if mag > 0:
        if loc == "en":
            return f"🐾 <b>Pet:</b> +{mag}% magic skill damage."
        return f"🐾 <b>Питомец:</b> +{mag}% к урону маг. навыков."
    if "crit_bonus" in d:
        p = round(float(d["crit_bonus"]) * 100.0, 1)
        if p > 0:
            if loc == "en":
                return f"🐾 <b>Pet:</b> +{p}% crit chance."
            return f"🐾 <b>Питомец:</b> +{p}% к шансу крита."
    if "dodge_bonus" in d:
        p = round(float(d["dodge_bonus"]) * 100.0, 1)
        if p > 0:
            if loc == "en":
                return f"🐾 <b>Pet:</b> +{p}% dodge."
            return f"🐾 <b>Питомец:</b> +{p}% к уклонению."
    if "def_bonus" in d:
        v = float(d["def_bonus"])
        vs = str(int(v)) if v == int(v) else str(v)
        if loc == "en":
            return f"🐾 <b>Pet:</b> +{vs} defense in combat."
        return f"🐾 <b>Питомец:</b> +{vs} к защите в бою."
    return ""


def format_pet_battle_line_html(character: Character, *, locale: str) -> str:
    """Строка в экране боя: активный питомец и краткий эффект."""
    disp = active_pet_display(character)
    if not disp:
        return ""
    passive = format_pet_passive_plain(pet_passive_delta(character), locale=locale)
    passive_html = f" — <i>{html.escape(passive)}</i>" if passive else ""
    return f"🐾 <b>{html.escape(disp)}</b>{passive_html}"


def pet_choice_button_caption(key: str, *, locale: str, is_active: bool) -> str:
    """Подпись кнопки выбора питомца (лимит длины для Telegram)."""
    d = _all_defs().get(key)
    if d is None:
        return str(key)[:64]
    loc = "en" if str(locale).lower().startswith("en") else "ru"
    label = f"{d.emoji} {d.name_ru}"
    if is_active:
        label += " ✓" if loc == "ru" else " ✓"
    return label[:64]


def build_pet_picker_html(character: Character, *, locale: str) -> str:
    """Экран выбора: все открытые питомцы и пассивки."""
    from utils.ui import LINE_SEP

    loc = locale if locale in ("ru", "en") else "ru"
    own = owned_keys(character)
    act = active_pet_key(character)
    lines: list[str] = [
        t(loc, "profile_pets_pick_header"),
        LINE_SEP,
    ]
    for key in own:
        d = _all_defs().get(key)
        if d is None:
            continue
        passive_plain = format_pet_passive_plain(d.passive, locale=loc)
        passive_html = html.escape(passive_plain)
        nm = html.escape(d.name_ru)
        blur = html.escape(d.blurb) if d.blurb else ""
        mark = f" {t(loc, 'profile_pet_active_mark')}" if act == key else ""
        lines.append(f"{d.emoji} <b>{nm}</b>{mark}")
        if blur:
            lines.append(f"<i>{blur}</i>")
        lines.append(f"<b>{t(loc, 'profile_pet_passive_label')}</b> <i>{passive_html}</i>")
        lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    lines.append(LINE_SEP)
    lines.append(f"<i>{html.escape(t(loc, 'profile_pets_pick_footer'))}</i>")
    return "\n".join(lines)


def format_city_hub_pets_hint_html(*, locale: str) -> str:
    """Абзац для экрана города про призыв и выбор питомца."""
    loc = "en" if str(locale).lower().startswith("en") else "ru"
    if loc == "en":
        return (
            "🐾 <b>Pets:</b> summon below for gold (max <b>3 pulls</b> per UTC day; ×3 uses three). "
            "Each pet adds a <b>passive</b> in combat — <b>only one</b> is active; "
            "pick the active one from <b>Status</b> (Pet button → list) or on <b>floors 8 / 48</b>."
        )
    return (
        "🐾 <b>Питомцы:</b> призыв ниже за золото (не больше <b>3 бросков</b> за сутки UTC; ×3 = три броска). "
        "Каждый даёт <b>пассивный</b> бонус в бою — в бою действует только <b>один</b>; "
        "выбрать активного: <b>статус</b> (кнопка «Питомец» → список) или этажи <b>8 и 48</b>."
    )


def _save_meta(character: Character, mp: dict[str, Any], st: dict[str, Any]) -> None:
    mp[META_KEY] = st
    character.meta_progress = mp


def try_grant_promo_pet(character: Character, key: str) -> tuple[str, str]:
    """
    Выдать питомца по промокоду (один ключ в коллекцию owned).
    Возвращает ("new"|"dup"|"bad", имя для сообщения или пусто при bad).
    """
    defs = _all_defs()
    if key not in defs:
        return "bad", ""
    mp, st = _pets_meta(character)
    owned = _normalize_owned_list(st.get("owned"))
    seen: set[str] = set()
    owned = [x for x in owned if x not in seen and not seen.add(x)]
    if key in owned:
        return "dup", defs[key].name_ru
    owned.append(key)
    st["owned"] = owned
    if not str(st.get("active") or "").strip():
        st["active"] = key
    mp = dict(mp)
    st = dict(st)
    _save_meta(character, mp, st)
    return "new", defs[key].name_ru


def set_active_pet(character: Character, key: str) -> tuple[bool, str]:
    if key not in _all_defs():
        return False, "Неизвестный питомец."
    owned = set(owned_keys(character))
    if key not in owned:
        return False, "Сначала получи питомца в призыве (город)."
    mp, st = _pets_meta(character)
    st["active"] = key
    _save_meta(character, mp, st)
    return True, _all_defs()[key].name_ru


def cycle_active_pet(character: Character) -> str | None:
    """Следующий из открытых (кольцо). Возвращает display или None."""
    own = owned_keys(character)
    if not own:
        return None
    mp, st = _pets_meta(character)
    cur = active_pet_key(character)
    if cur is None or cur not in own:
        st["active"] = own[0]
        _save_meta(character, mp, st)
        return active_pet_display(character)
    i = own.index(cur)
    nxt = own[(i + 1) % len(own)]
    st["active"] = nxt
    _save_meta(character, mp, st)
    return active_pet_display(character)


def _roll_pet_choice(*, rare_exclusive: bool) -> PetDef:
    pool = list(PET_BASIC_POOL)
    weights = [1.0] * len(pool)
    if rare_exclusive:
        pool.extend(PET_RARE_EXCLUSIVE)
        weights.extend([0.35, 0.35])
    total_w = sum(weights)
    r = random.uniform(0, total_w)
    acc = 0.0
    chosen: PetDef | None = None
    for p, w in zip(pool, weights):
        acc += w
        if r <= acc:
            chosen = p
            break
    return chosen if chosen is not None else pool[-1]


def _apply_pet_pull_after_payment(
    character: Character,
    chosen: PetDef,
    *,
    cost_for_refund: int,
) -> str:
    mp, st = _pets_meta(character)
    owned = list(st.get("owned") or [])
    if not isinstance(owned, list):
        owned = []
    owned_set = {str(x) for x in owned}

    if chosen.key in owned_set:
        refund = max(1, int(cost_for_refund * DUPLICATE_REFUND_RATIO))
        character.gold = int(character.gold) + refund
        return (
            f"Повтор: <b>{chosen.emoji} {chosen.name_ru}</b> уже с тобой. "
            f"Возврат <b>{refund}</b> золота."
        )

    owned.append(chosen.key)
    st["owned"] = owned
    if not st.get("active"):
        st["active"] = chosen.key
    _save_meta(character, mp, st)
    return f"Новый питомец: <b>{chosen.emoji} {chosen.name_ru}</b>\n<i>{chosen.blurb}</i>"


def _utc_today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


def city_pet_pulls_used_today(character: Character) -> int:
    _, st = _pets_meta(character)
    if str(st.get("city_pull_date") or "") != _utc_today_iso():
        return 0
    return int(st.get("city_pulls", 0) or 0)


def city_pet_pulls_remaining_today(character: Character) -> int:
    return max(0, CITY_PET_PULLS_LIMIT_PER_UTC_DAY - city_pet_pulls_used_today(character))


def _increment_city_pet_pulls(character: Character, n: int) -> None:
    mp, st = _pets_meta(character)
    today = _utc_today_iso()
    if str(st.get("city_pull_date") or "") != today:
        st["city_pull_date"] = today
        st["city_pulls"] = 0
    st["city_pulls"] = int(st.get("city_pulls", 0) or 0) + int(n)
    _save_meta(character, mp, st)


def city_summon_price_band(character: Character) -> tuple[int, int, bool]:
    """
    (цена ×1, цена ×3, редкий_пул).
    Редкий пул — если когда-либо открыт 48-й этаж (highest_floor_reached).
    """
    hi = int(character.highest_floor_reached)
    if hi >= GACHA_FLOOR_RARE:
        return GACHA_COST_RARE, CITY_SUMMON_COST_X3_RARE, True
    return GACHA_COST_BASIC, CITY_SUMMON_COST_X3_BASIC, False


def try_city_pet_summon(character: Character, *, pulls: int, locale: str = "ru") -> tuple[bool, str]:
    """Призыв из городского хаба: 1 или 3 броска одной оплатой."""
    if pulls not in (1, 3):
        return False, "Неверный запрос."
    loc = locale if locale in ("ru", "en") else "ru"
    left = city_pet_pulls_remaining_today(character)
    if pulls > left:
        return False, t(loc, "pet_city_summon_limit", left=left, limit=CITY_PET_PULLS_LIMIT_PER_UTC_DAY)
    c1, c3, rare = city_summon_price_band(character)
    total = c1 if pulls == 1 else c3
    if int(character.gold) < total:
        return False, f"Нужно {total} золота."
    character.gold = int(character.gold) - total
    per_refund = max(1, total // pulls)
    parts = [_apply_pet_pull_after_payment(character, _roll_pet_choice(rare_exclusive=rare), cost_for_refund=per_refund) for _ in range(pulls)]
    _increment_city_pet_pulls(character, pulls)
    return True, "\n\n".join(parts)


def try_gacha_pull(character: Character, *, floor_number: int) -> tuple[bool, str]:
    """
    Совместимость: призыв с этажа (если остались старые кнопки) — перенаправляет логику на этажные цены.
    """
    spec = _PET_GACHA_FLOORS.get(int(floor_number))
    if spec is None:
        return False, "Призыв питомцев — в городе (лавка хаба)."
    cost, rare_exclusive = spec
    if int(character.gold) < cost:
        return False, f"Нужно {cost} золота."
    chosen = _roll_pet_choice(rare_exclusive=rare_exclusive)
    character.gold = int(character.gold) - cost
    return True, _apply_pet_pull_after_payment(character, chosen, cost_for_refund=cost)
