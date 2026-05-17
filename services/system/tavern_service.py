"""
Таверна: покупка отдыха за золото, учёт визитов.
"""

from __future__ import annotations

import html
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models.character import Character
from game.tower.progression import floor_data
from game.locations import tavern as tavern_loc
import services.progression.title_service as title_service
from utils.telegram.ui import LINE_SEP_TAVERN

LODGING_DAILY_LIMIT = 5
_LODGING_META = "lodging_daily_v1"
_LODGING_META_V2 = "lodging_daily_v2"

# Ежедневная ротация: meta_progress.tavern_daily_v1 = {date, bought_blueprints[], bought_gears[]}
_TAVERN_DAILY_META = "tavern_daily_v1"
# Известные рецепты (постоянно): meta_progress.known_recipes = ["recipe_id", ...]
META_KNOWN_RECIPES = "known_recipes"


def _lodging_city_key(character: Character) -> str:
    city = floor_data.get_city_for_floor(int(character.floor_number))
    if city is None:
        return "unknown"
    return str(int(city.floor))


def _lodging_uses_today_for_city(character: Character, city_key: str) -> int:
    """Сколько ночлегов куплено сегодня (UTC) в данном городе."""
    mp = character.meta_progress or {}
    today = datetime.now(UTC).date().isoformat()
    raw2 = mp.get(_LODGING_META_V2)
    if isinstance(raw2, dict) and raw2.get("date") == today:
        by = raw2.get("by_city") or {}
        if isinstance(by, dict):
            return int(by.get(city_key, 0))
    raw = mp.get(_LODGING_META)
    if isinstance(raw, dict) and raw.get("date") == today:
        return int(raw.get("count", 0))
    return 0


def _increment_lodging_uses_for_city(character: Character, city_key: str) -> None:
    mp = dict(character.meta_progress or {})
    today = datetime.now(UTC).date().isoformat()
    raw2 = mp.get(_LODGING_META_V2)
    if not isinstance(raw2, dict) or raw2.get("date") != today:
        raw2 = {"date": today, "by_city": {}}
    by = dict(raw2.get("by_city") or {}) if isinstance(raw2.get("by_city"), dict) else {}
    by[city_key] = int(by.get(city_key, 0)) + 1
    raw2["by_city"] = by
    mp[_LODGING_META_V2] = raw2
    character.meta_progress = mp


def format_tavern_welcome_html(character: Character) -> str:
    city = floor_data.get_city_for_floor(character.floor_number)
    cname = html.escape(city.name) if city else "Город"
    cem = city.emoji if city else "🏠"
    ck = _lodging_city_key(character)
    lodging_uses = _lodging_uses_today_for_city(character, ck)
    lines = [
        f"{cem} <b>Таверна «У усталого стража»</b> — {cname}",
        "<i>Хозяин кивает: «Этаж не прощает слабых. Поешь — и снова в бой.»</i>",
        LINE_SEP_TAVERN,
        f"💰 Твоё золото: <b>{int(character.gold):,}</b>",
        f"❤️ HP: {character.hp_current}/{character.hp_max}  "
        f"💙 MP: {character.mp_current}/{character.mp_max}  "
        f"⚡ Стамина: {character.stamina}/{settings.MAX_STAMINA}",
        LINE_SEP_TAVERN,
        "<b>Меню:</b>",
    ]
    for o in tavern_loc.tavern_offers_for_floor(int(character.floor_number)):
        extra = ""
        if o.key == "lodging":
            left = LODGING_DAILY_LIMIT - lodging_uses
            extra = f" <i>({left} из {LODGING_DAILY_LIMIT} ночлегов осталось сегодня)</i>"
        lines.append(
            f"{o.emoji} <b>{html.escape(o.name)}</b> — {o.price} 💰{extra}\n"
            f"<i>{html.escape(o.blurb)}</i>",
        )
    return "\n".join(lines)


def _heal_percent(character: Character, hp_pct: float, mp_pct: float) -> None:
    hp_add = max(1, int(int(character.hp_max) * hp_pct)) if hp_pct > 0 else 0
    mp_add = int(int(character.mp_max) * mp_pct) if mp_pct > 0 else 0
    if mp_pct > 0:
        mp_add = max(1, mp_add)
    character.hp_current = min(int(character.hp_max), int(character.hp_current) + hp_add)
    character.mp_current = min(int(character.mp_max), int(character.mp_current) + mp_add)


async def try_buy_offer(
    session: AsyncSession,
    character: Character,
    offer_key: str,
) -> tuple[bool, str]:
    """
    Покупка по ключу меню. Успех — (True, HTML результат).
    Провал — (False, plain text для alert).
    """
    if not tavern_loc.tavern_available_on_floor(character.floor_number):
        return False, "Таверна только в городах на этажах 31, 61 и 91."

    offer = tavern_loc.offer_by_key(offer_key, floor_number=int(character.floor_number))
    if offer is None:
        return False, "Нет такого блюда в меню."

    price = offer.price
    if int(character.gold) < price:
        return False, f"Недостаточно золота. Нужно {price:,} 💰."

    if offer.key == "lodging":
        if int(character.stamina) >= settings.MAX_STAMINA:
            return False, "Стамина уже полная — ночлег не нужен."
        ck = _lodging_city_key(character)
        uses_today = _lodging_uses_today_for_city(character, ck)
        if uses_today >= LODGING_DAILY_LIMIT:
            return False, (
                f"Лимит ночлегов в этом городе на сегодня исчерпан ({LODGING_DAILY_LIMIT}/{LODGING_DAILY_LIMIT}). "
                "Возвращайся завтра или смени город."
            )

    import services.progression.character_service as character_service
    character_service.add_gold(
        character,
        -price,
        spend_for=f"Таверна: {offer.name}",
        spend_kind="tavern",
    )
    character.tavern_visits = int(character.tavern_visits) + 1
    title_service.refresh_unlocks(character)

    if offer.key == "ale":
        _heal_percent(character, 0.12, 0.08)
        msg = (
            f"🍺 Ты осушил кружку. "
            f"HP <b>{character.hp_current}</b> / {character.hp_max}, "
            f"MP <b>{character.mp_current}</b> / {character.mp_max}."
        )
    elif offer.key == "stew":
        _heal_percent(character, 0.32, 0.25)
        msg = (
            f"🍲 Разогрел рагу до дна. "
            f"HP <b>{character.hp_current}</b> / {character.hp_max}, "
            f"MP <b>{character.mp_current}</b> / {character.mp_max}."
        )
    elif offer.key in ("mulled", "throne_cut", "star_soup"):
        hp_p, mp_p = {
            "mulled": (0.20, 0.14),
            "throne_cut": (0.40, 0.30),
            "star_soup": (0.55, 0.40),
        }[offer.key]
        _heal_percent(character, hp_p, mp_p)
        msg = (
            f"{offer.emoji} <b>{html.escape(offer.name)}</b>. "
            f"HP <b>{character.hp_current}</b> / {character.hp_max}, "
            f"MP <b>{character.mp_current}</b> / {character.mp_max}."
        )
    elif offer.key == "feast":
        character.hp_current = int(character.hp_max)
        character.mp_current = int(character.mp_max)
        msg = "🍖 Пир! HP и MP на максимуме."
    elif offer.key == "lodging":
        mx = settings.MAX_STAMINA
        before = int(character.stamina)
        character.stamina = min(mx, before + 3)
        gained = int(character.stamina) - before
        # Overnight rest also restores 50% HP and 40% MP
        hp_restore = max(0, int(character.hp_max) // 2 - int(character.hp_current))
        mp_restore = max(0, int(int(character.mp_max) * 0.4) - int(character.mp_current))
        character.hp_current = min(int(character.hp_max), int(character.hp_current) + int(character.hp_max) // 2)
        character.mp_current = min(int(character.mp_max), int(character.mp_current) + int(int(character.mp_max) * 0.4))
        hp_line = f", ❤️ +{min(hp_restore, int(character.hp_max)//2)} HP" if hp_restore > 0 else ""
        mp_line = f", 💙 +{min(mp_restore, int(int(character.mp_max)*0.4))} MP" if mp_restore > 0 else ""
        ck = _lodging_city_key(character)
        _increment_lodging_uses_for_city(character, ck)
        uses_now = _lodging_uses_today_for_city(character, ck)
        left = LODGING_DAILY_LIMIT - uses_now
        msg = (
            f"🛏️ Выспался. Стамина <b>+{gained}</b>{hp_line}{mp_line} "
            f"(⚡ {character.stamina}/{mx}).\n"
            f"<i>Ночлегов осталось сегодня: {left}/{LODGING_DAILY_LIMIT}.</i>"
        )
    else:
        return False, "Внутренняя ошибка меню."

    await session.flush()
    return True, f"−{price:,} 💰\n{msg}"


# ─── Ежедневная ротация: чертежи и снаряжение ────────────────────────────────


def _today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


def _tavern_daily_state(character: Character) -> dict:
    """Текущая дневная мета (на сегодня UTC); создаёт пустую при смене даты."""
    mp = dict(character.meta_progress or {})
    raw = mp.get(_TAVERN_DAILY_META)
    today = _today_iso()
    if not isinstance(raw, dict) or raw.get("date") != today:
        raw = {"date": today, "bought_blueprints": [], "bought_gears": []}
        mp[_TAVERN_DAILY_META] = raw
        character.meta_progress = mp
    return raw


def known_recipes(character: Character) -> list[str]:
    raw = (character.meta_progress or {}).get(META_KNOWN_RECIPES)
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return []


def _add_known_recipe(character: Character, recipe_id: str) -> bool:
    mp = dict(character.meta_progress or {})
    cur = mp.get(META_KNOWN_RECIPES)
    if not isinstance(cur, list):
        cur = []
    if recipe_id in cur:
        return False
    cur.append(recipe_id)
    mp[META_KNOWN_RECIPES] = cur
    character.meta_progress = mp
    return True


def daily_offers_for_character(character: Character) -> dict:
    return tavern_loc.daily_tavern_offers(int(character.floor_number), _today_iso())


def format_tavern_daily_html(character: Character) -> str:
    offers = daily_offers_for_character(character)
    state = _tavern_daily_state(character)
    bb = set(state.get("bought_blueprints") or [])
    bg = set(state.get("bought_gears") or [])
    known = set(known_recipes(character))
    lines = [
        "📜 <b>Дневные предложения таверны</b>",
        f"<i>Обновляются ежедневно по UTC. Сегодня: {state.get('date')}</i>",
        LINE_SEP_TAVERN,
        "<b>Чертежи (одна покупка в сутки):</b>",
    ]
    for rid, name, price in offers.get("blueprints", []):
        flag = ""
        if rid in known:
            flag = " <i>(уже известен)</i>"
        elif rid in bb:
            flag = " <i>(куплен сегодня)</i>"
        lines.append(f"{html.escape(name)} — {price}💰{flag}")
    lines.append(LINE_SEP_TAVERN)
    lines.append("<b>Снаряжение (одна покупка в сутки):</b>")
    for key, idata, price in offers.get("gears", []):
        nm = str(idata.get("name", key))
        flag = " <i>(куплено сегодня)</i>" if key in bg else ""
        lines.append(f"{html.escape(nm)} — {price}💰{flag}")
    lines.append(LINE_SEP_TAVERN)
    lines.append(f"💰 Твоё золото: <b>{int(character.gold):,}</b>")
    return "\n".join(lines)


async def try_buy_daily_blueprint(
    session: AsyncSession,
    character: Character,
    recipe_id: str,
) -> tuple[bool, str]:
    if not tavern_loc.tavern_available_on_floor(character.floor_number):
        return False, "Таверна только в городах-хабах."
    offers = daily_offers_for_character(character)
    match = next((b for b in offers.get("blueprints", []) if b[0] == recipe_id), None)
    if match is None:
        return False, "Этот чертёж сегодня не предлагается."
    rid, name, price = match
    state = _tavern_daily_state(character)
    bought = list(state.get("bought_blueprints") or [])
    if rid in bought:
        return False, "Этот чертёж сегодня уже куплен."
    if int(character.gold) < int(price):
        return False, f"Недостаточно золота. Нужно {int(price):,} 💰."

    import services.progression.character_service as character_service
    character_service.add_gold(
        character,
        -int(price),
        spend_for=f"Таверна: чертёж «{name}»",
        spend_kind="tavern",
    )
    bought.append(rid)
    state["bought_blueprints"] = bought
    mp = dict(character.meta_progress or {})
    mp[_TAVERN_DAILY_META] = state
    character.meta_progress = mp
    is_new = _add_known_recipe(character, rid)
    from game.crafting.workshop_meta import add_known_blueprint

    add_known_blueprint(character, rid)
    await session.flush()
    if is_new:
        return True, f"📜 Куплен чертёж: <b>{html.escape(name)}</b>. Теперь доступен в кузнице."
    return True, f"📜 Чертёж <b>{html.escape(name)}</b> уже был известен — золото возвращено не будет."


async def try_buy_daily_gear(
    session: AsyncSession,
    character: Character,
    gear_key: str,
) -> tuple[bool, str]:
    if not tavern_loc.tavern_available_on_floor(character.floor_number):
        return False, "Таверна только в городах-хабах."
    offers = daily_offers_for_character(character)
    match = next((g for g in offers.get("gears", []) if g[0] == gear_key), None)
    if match is None:
        return False, "Этого снаряжения сегодня не предлагается."
    key, idata, price = match
    state = _tavern_daily_state(character)
    bought = list(state.get("bought_gears") or [])
    if key in bought:
        return False, "Этот предмет сегодня уже куплен."
    if int(character.gold) < int(price):
        return False, f"Недостаточно золота. Нужно {int(price):,} 💰."

    from db.repository import inventory_repo
    import services.progression.character_service as character_service

    nm = str(idata.get("name", key))
    character_service.add_gold(
        character,
        -int(price),
        spend_for=f"Таверна: {nm}",
        spend_kind="tavern",
    )
    bought.append(key)
    state["bought_gears"] = bought
    mp = dict(character.meta_progress or {})
    mp[_TAVERN_DAILY_META] = state
    character.meta_progress = mp
    await session.flush()
    return True, f"🛒 Куплено: <b>{html.escape(nm)}</b>. Лежит в инвентаре."
