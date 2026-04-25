"""
Таверна: покупка отдыха за золото, учёт визитов.
"""

from __future__ import annotations

import html
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models.character import Character
from game.floors import floor_data
from game.locations import tavern as tavern_loc
from services import title_service
from utils.ui import LINE_SEP_TAVERN

LODGING_DAILY_LIMIT = 5
_LODGING_META = "lodging_daily_v1"


def _lodging_uses_today(character: Character) -> int:
    """Сколько раз куплен ночлег сегодня (UTC)."""
    mp = character.meta_progress or {}
    raw = mp.get(_LODGING_META)
    if not isinstance(raw, dict):
        return 0
    today = datetime.now(UTC).date().isoformat()
    if raw.get("date") != today:
        return 0
    return int(raw.get("count", 0))


def _increment_lodging_uses(character: Character) -> None:
    mp = dict(character.meta_progress or {})
    today = datetime.now(UTC).date().isoformat()
    raw = mp.get(_LODGING_META)
    if not isinstance(raw, dict) or raw.get("date") != today:
        raw = {"date": today, "count": 0}
    raw["count"] = int(raw.get("count", 0)) + 1
    mp[_LODGING_META] = raw
    character.meta_progress = mp


def format_tavern_welcome_html(character: Character) -> str:
    city = floor_data.get_city_for_floor(character.floor_number)
    cname = html.escape(city.name) if city else "Город"
    cem = city.emoji if city else "🏠"
    lodging_uses = _lodging_uses_today(character)
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
    for o in tavern_loc.TAVERN_MENU:
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

    offer = tavern_loc.offer_by_key(offer_key)
    if offer is None:
        return False, "Нет такого блюда в меню."

    price = offer.price
    if int(character.gold) < price:
        return False, f"Недостаточно золота. Нужно {price:,} 💰."

    if offer.key == "lodging":
        if int(character.stamina) >= settings.MAX_STAMINA:
            return False, "Стамина уже полная — ночлег не нужен."
        uses_today = _lodging_uses_today(character)
        if uses_today >= LODGING_DAILY_LIMIT:
            return False, (
                f"Лимит ночлегов на сегодня исчерпан ({LODGING_DAILY_LIMIT}/{LODGING_DAILY_LIMIT}). "
                "Возвращайся завтра."
            )

    character_service.add_gold(character, -price)
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
    elif offer.key == "feast":
        character.hp_current = int(character.hp_max)
        character.mp_current = int(character.mp_max)
        msg = "🍖 Пир! HP и MP на максимуме."
    elif offer.key == "lodging":
        mx = settings.MAX_STAMINA
        before = int(character.stamina)
        character.stamina = min(mx, before + 3)
        gained = int(character.stamina) - before
        _increment_lodging_uses(character)
        uses_now = _lodging_uses_today(character)
        left = LODGING_DAILY_LIMIT - uses_now
        msg = (
            f"🛏️ Выспался. Стамина <b>+{gained}</b> (сейчас {character.stamina}/{mx}).\n"
            f"<i>Ночлегов осталось сегодня: {left}/{LODGING_DAILY_LIMIT}.</i>"
        )
    else:
        return False, "Внутренняя ошибка меню."

    await session.flush()
    return True, f"−{price:,} 💰\n{msg}"
