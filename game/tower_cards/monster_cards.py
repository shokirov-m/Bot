"""
Карточки «башенной» колоды: монстры с этажей 1–20 (пул из build_spawns_for_floor).

Имя и эмодзи — из MONSTER_TEMPLATE_META; ATK/DEF — из каталога монстров с масштабом по этажу выпадения.
Стихия для дуэли нормализуется к fire / water / earth (см. duel_element).
"""

from __future__ import annotations

import html
import random
from pathlib import Path
from typing import Any

from game.data.monsters import MONSTER_TEMPLATE_META
from game.floors import floor_data, monster_catalog
from game.floors.monster_appearances_ru import APPEARANCE_RU, MONSTER_CARD_QUOTE_RU
from game.floors.monsters import FloorMonsterSpawn, build_spawns_for_floor
from game.tower_cards.card_catalog import catalog_str, merged_catalog_entry
from utils.image_assets import monster_image_for_template

RARITY_STARS_RU: dict[str, str] = {
    "common": "⭐",
    "uncommon": "⭐⭐",
    "rare": "⭐⭐⭐",
    "epic": "⭐⭐⭐⭐",
    "legendary": "⭐⭐⭐⭐⭐",
    "mythic": "⭐⭐⭐⭐⭐⭐",
}

RARITY_ORDER: tuple[str, ...] = ("mythic", "legendary", "epic", "rare", "uncommon", "common")

RARITY_LABEL_RU: dict[str, str] = {
    "common": "обычная",
    "uncommon": "необычная",
    "rare": "редкая",
    "epic": "эпическая",
    "legendary": "легендарная",
    "mythic": "мифическая",
}

RARITY_HEADER_RU: dict[str, str] = {
    "mythic": "Мифические",
    "legendary": "Легендарные",
    "epic": "Эпические",
    "rare": "Редкие",
    "uncommon": "Необычные",
    "common": "Обычные",
}

# Подпись редкости в карточке («Обычный ⭐»)
RARITY_CARD_TITLE_RU: dict[str, str] = {
    "common": "Обычный",
    "uncommon": "Необычный",
    "rare": "Редкий",
    "epic": "Эпический",
    "legendary": "Легендарный",
    "mythic": "Мифический",
}

DUPLICATE_ATK_BONUS: int = 2

DUEL_ELEMENT_RU: dict[str, str] = {
    "fire": "огонь",
    "water": "вода",
    "earth": "земля",
}

_RAW_GAME_ELEMENT_RU: dict[str, str] = {
    "fire": "огонь",
    "water": "вода",
    "ice": "лёд",
    "earth": "земля",
    "physical": "физическая",
    "dark": "тьма",
    "light": "свет",
    "air": "воздух",
    "wind": "ветер",
    "poison": "яд",
    "nature": "природа",
    "arcane": "тайная магия",
    "none": "нет",
    "neutral": "нейтральная",
    "electric": "молния",
    "lightning": "молния",
    "holy": "святость",
}


def format_wait_hm_ru(seconds: int) -> str:
    """Человекочитаемое «через N ч. M мин.» для кулдауна."""
    s = max(0, int(seconds))
    h = s // 3600
    m = (s % 3600) // 60
    if h > 0:
        return f"{h} ч. {m} мин."
    if m > 0:
        return f"{m} мин."
    return "меньше минуты"


def duel_element_ru(duel_code: str) -> str:
    k = (duel_code or "earth").strip().lower()
    return DUEL_ELEMENT_RU.get(k, DUEL_ELEMENT_RU["earth"])


def raw_game_element_ru(raw: str) -> str:
    k = (raw or "").strip().lower()
    if not k:
        return "—"
    return _RAW_GAME_ELEMENT_RU.get(k, (raw or "").strip())


def _build_pool_keys() -> frozenset[str]:
    keys: set[str] = set()
    for fl in range(1, 21):
        for s in build_spawns_for_floor(fl):
            keys.add(s.template.key)
    return frozenset(keys)


TW_POOL_KEYS: frozenset[str] = _build_pool_keys()
TW_POOL_TOTAL: int = len(TW_POOL_KEYS)


def _build_drop_percent_int() -> dict[str, int]:
    from collections import defaultdict

    acc: dict[str, float] = defaultdict(float)
    for fl in range(1, 21):
        spawns = build_spawns_for_floor(fl)
        if not spawns:
            continue
        w = (1.0 / 20.0) / float(len(spawns))
        for s in spawns:
            acc[s.template.key] += w
    return {k: max(0, min(100, round(v * 100.0))) for k, v in acc.items()}


TW_DROP_PERCENT: dict[str, int] = _build_drop_percent_int()


def base_template_key(template_key: str) -> str:
    k = (template_key or "").strip()
    if k.startswith("elite_"):
        return k[len("elite_") :]
    return k


def meta_row(template_key: str) -> dict[str, str] | None:
    bk = base_template_key(template_key)
    m = MONSTER_TEMPLATE_META.get(template_key) or MONSTER_TEMPLATE_META.get(bk)
    return m


def display_name(template_key: str) -> str:
    m = meta_row(template_key)
    if m:
        return str(m.get("display_name", template_key)).strip() or template_key
    return template_key


def emoji_for(template_key: str) -> str:
    m = meta_row(template_key)
    if m:
        return str(m.get("emoji", "👾"))
    return "👾"


def raw_element(template_key: str) -> str:
    m = meta_row(template_key)
    if m:
        return str(m.get("element", "earth")).strip().lower()
    return "earth"


def duel_element(raw: str) -> str:
    """Камень-ножницы-бумага в дуэли только fire / water / earth."""
    e = (raw or "earth").strip().lower()
    if e == "fire":
        return "fire"
    if e in ("water", "ice"):
        return "water"
    return "earth"


def tier_for_spawn(spawn: FloorMonsterSpawn, floor: int) -> str:
    if spawn.is_major_boss:
        return "mythic"
    if spawn.is_mini_boss:
        return "legendary"
    if spawn.is_elite:
        return "rare"
    if floor <= 7:
        return "common"
    if floor <= 14:
        return "uncommon"
    return "epic"


def pick_random_spawn_f1_20() -> tuple[int, FloorMonsterSpawn]:
    fl = random.randint(1, 20)
    spawns = build_spawns_for_floor(fl)
    return fl, random.choice(spawns)


def scaled_atk_def(template_key: str, floor: int) -> tuple[int, int]:
    cat = monster_catalog.get_definition(template_key)
    if cat is None:
        return 8, 3
    r = monster_catalog.floor_ratio(cat, int(floor))
    atk = max(1, int(float(cat.get("atk", 10)) * r))
    deff = max(0, int(float(cat.get("def", 2)) * r))
    return atk, deff


def portrait_path(template_key: str, floor: int) -> Path | None:
    zone = floor_data.get_zone_for_floor(int(floor))
    return monster_image_for_template(template_key, zone_key=zone.key)


def template_blurb(template_key: str) -> str:
    m = meta_row(template_key)
    if not m:
        return ""
    return str(m.get("blurb", "") or "").strip()


def card_quote_ru(template_key: str) -> str:
    bk = base_template_key(template_key)
    for k in (template_key, bk):
        q = MONSTER_CARD_QUOTE_RU.get(k)
        if q and str(q).strip():
            return str(q).strip()
    return ""


def drop_percent_display(template_key: str) -> str:
    p = TW_DROP_PERCENT.get(template_key, 0)
    if p >= 1:
        return f"{p}%"
    return "<1%"


def _merge_description_blurb(blurb: str, appearance: str) -> str:
    b = (blurb or "").strip()
    a = (appearance or "").strip()
    if b and a and a not in b:
        return f"{b}\n\n{a}"
    if b:
        return b
    if a:
        return a
    return "—"


def element_line_prefix_emoji(raw: str) -> str:
    r = (raw or "").strip().lower()
    if r in ("fire", "ember", "cinder", "lava", "magma"):
        return "🔥"
    if r in ("water", "ice", "frost", "glacier", "snow"):
        return "💧"
    if r in ("earth", "nature", "plant", "wood", "stone"):
        return "🪨"
    if r in ("dark", "shadow", "void", "death", "curse"):
        return "🌑"
    if r in ("light", "holy", "gold", "solar", "radiant"):
        return "✨"
    if r in ("electric", "lightning", "thunder", "storm"):
        return "⚡"
    if r in ("air", "wind"):
        return "💨"
    if r in ("poison", "acid", "toxic", "venom"):
        return "☠️"
    if r in ("arcane", "magic", "rune"):
        return "🔮"
    if r in ("physical", "neutral", "none", ""):
        return "✨"
    return "✨"


def element_line_value_ru(raw: str, duel_code: str) -> str:
    r = (raw or "").strip().lower()
    if r == "physical":
        return "Нет"
    ru = raw_game_element_ru(raw)
    if r in ("", "none", "neutral", "???") or ru.lower() in ("нет", "нейтральная", "—"):
        return "Нет"
    raw_ru = ru
    duel_ru = duel_element_ru(duel_code)
    raw_cap = raw_ru[:1].upper() + raw_ru[1:] if raw_ru else ""
    if raw_ru.lower() == duel_ru.lower():
        return raw_cap
    return f"{raw_cap} (в дуэли как {duel_ru})"


def _format_quote_display(q: str) -> str:
    s = (q or "").strip()
    if not s or s == "—":
        return "—"
    if (s.startswith("«") and s.endswith("»")) or (s.startswith('"') and s.endswith('"')):
        return html.escape(s)
    return f"«{html.escape(s)}»"


def format_monster_card_html(
    *,
    template_key: str,
    floor: int,
    name_ru: str,
    emoji: str,
    tier: str,
    atk: int,
    deff: int,
    raw_element: str,
    duel_element_code: str,
    blurb: str,
    description_max_len: int | None = None,
) -> str:
    _ = floor  # этаж влияет на ATK/DEF снаружи; на карте не выводим отдельной строкой
    tk = (template_key or "").strip()
    bk = base_template_key(tk)
    cat = merged_catalog_entry(tk, bk)
    nm = (name_ru or "").strip() or display_name(tk)
    emo = (emoji or "").strip() or emoji_for(tk)
    if catalog_str(cat, "name_ru"):
        nm = catalog_str(cat, "name_ru") or nm
    if catalog_str(cat, "emoji"):
        emo = catalog_str(cat, "emoji") or emo
    stars = RARITY_STARS_RU.get(tier, "⭐")
    rare_title = RARITY_CARD_TITLE_RU.get(tier, str(tier).capitalize())
    if catalog_str(cat, "description_ru"):
        desc_src = catalog_str(cat, "description_ru") or "—"
    else:
        desc_src = _merge_description_blurb(blurb, APPEARANCE_RU.get(bk, ""))
    cap_len = 680 if description_max_len is None else min(680, int(description_max_len))
    if len(desc_src) > cap_len:
        desc_src = desc_src[: cap_len - 1] + "…"
    desc_final = desc_src if desc_src else "—"
    desc_esc = "—" if desc_final == "—" else html.escape(desc_final)
    elem_val = element_line_value_ru(raw_element, duel_element_code)
    elem_pre = element_line_prefix_emoji(raw_element)
    quote_raw = catalog_str(cat, "quote_ru") or card_quote_ru(tk)
    q_display = _format_quote_display(quote_raw)
    pct_s = drop_percent_display(tk)
    spec = catalog_str(cat, "special_ru")
    comb = catalog_str(cat, "combo_ru")
    spec_line = f"✨ <b>ОСОБОЕ:</b> {html.escape(spec)}" if spec else "✨ <b>ОСОБОЕ:</b> Нет"
    combo_line = f"💫 <b>КОМБО:</b> {html.escape(comb)}" if comb else "💫 <b>КОМБО:</b> Нет"

    lines = [
        f"{html.escape(emo)} <b>ИМЯ:</b> {html.escape(nm)}",
        f"💎 <b>РЕДКОСТЬ:</b> {html.escape(rare_title)} {stars}",
        f"⚔️ <b>СИЛА:</b> {int(atk)} ATK",
        f"🛡️ <b>ЗАЩИТА:</b> {int(deff)}",
        f"{elem_pre} <b>СТИХИЯ:</b> {html.escape(elem_val)}",
        spec_line,
        combo_line,
        f"📖 <b>ОПИСАНИЕ:</b> {desc_esc}",
        f"🎯 <b>ШАНС ВЫПАДЕНИЯ:</b> {html.escape(pct_s)}",
        f"📊 <b>ДУБЛИКАТ:</b> +{DUPLICATE_ATK_BONUS} ATK к силе",
        f"💬 <b>ФРАЗА:</b> {q_display}",
    ]
    return "\n".join(lines)


def format_monster_card_spawn_html(
    spawn: FloorMonsterSpawn,
    floor: int,
    *,
    atk: int | None = None,
    deff: int | None = None,
    description_max_len: int | None = None,
) -> str:
    sid = spawn.template.key
    base_a, base_d = scaled_atk_def(sid, int(floor))
    a = int(atk) if atk is not None else base_a
    d = int(deff) if deff is not None else base_d
    tier = tier_for_spawn(spawn, int(floor))
    raw = spawn.template.element
    du = duel_element(raw)
    bl = (spawn.template.blurb or "").strip() or template_blurb(sid)
    return format_monster_card_html(
        template_key=sid,
        floor=int(floor),
        name_ru=spawn.template.name,
        emoji=spawn.template.emoji,
        tier=tier,
        atk=a,
        deff=d,
        raw_element=raw,
        duel_element_code=du,
        blurb=bl,
        description_max_len=description_max_len,
    )


def format_monster_card_from_collection_row(
    template_key: str,
    row: dict[str, Any],
    *,
    description_max_len: int | None = None,
) -> str:
    floor = int(row.get("source_floor", 10))
    atk = int(row.get("atk", 0))
    deff = int(row.get("def", 0))
    tier = str(row.get("rarity", "common"))
    raw_el = str(row.get("raw_element") or raw_element(template_key))
    duel_c = str(row.get("element") or duel_element(raw_el))
    name_ru = str(row.get("name_ru") or display_name(template_key))
    emo = str(row.get("emoji") or emoji_for(template_key))
    bl = template_blurb(template_key)
    return format_monster_card_html(
        template_key=template_key,
        floor=floor,
        name_ru=name_ru,
        emoji=emo,
        tier=tier,
        atk=atk,
        deff=deff,
        raw_element=raw_el,
        duel_element_code=duel_c,
        blurb=bl,
        description_max_len=description_max_len,
    )


def filtered_collection(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Только карты из пула 1–20 этажа (старые sticker id отбрасываем)."""
    return {k: dict(v) for k, v in raw.items() if k in TW_POOL_KEYS and isinstance(v, dict)}
