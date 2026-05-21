"""Покупка гримуаров в библиотеке между 18↔19 ярусами."""

from __future__ import annotations

import html

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from game.archetypes.grimoires import SKILL_GRIMOIRES, grant_grimoire
from game.locations import grimoire_library as lib
import services.progression.character_service as character_service


def format_library_hub_html(character: Character) -> str:
    gold = int(character.gold)
    bought = len(lib._purchased_keys(character))
    lines = [
        "📚 <b>Библиотека гримуаров</b>",
        "<i>Зал между 18-м и 19-м ярусами. Здесь продают книги навыков — "
        "только за золото, без обмена и скупки.</i>",
        "",
        f"💰 Золото: <b>{gold:,}</b> · куплено книг: <b>{bought}</b>",
        "",
        "<b>Правила:</b>",
        "• цена одной книги — от <b>10 000</b> до <b>100 000</b> 💰;",
        "• каждую книгу можно купить <b>один раз</b> на героя;",
        "• передать или продать нельзя — только прочитать в «Гримуарах»;",
        "• высшие гримуары (tier‑2) здесь не продаются.",
        "",
        "Выберите <b>класс</b> для каталога:",
    ]
    return "\n".join(lines)


def format_class_catalog_html(character: Character, archetype_key: str) -> str:
    arch_lbl = lib.archetype_label_ru(archetype_key)
    lines = [
        f"📚 <b>Каталог — {html.escape(arch_lbl)}</b>",
        "<i>Нажмите книгу, чтобы увидеть описание и купить.</i>",
        "",
    ]
    for offer in lib.offers_for_archetype(archetype_key):
        g = SKILL_GRIMOIRES[offer.grimoire_key]
        st = lib.offer_status(character, offer.grimoire_key)
        if st == "изучен":
            mark = "✅"
        elif st in ("куплен", "в сумке"):
            mark = "📖"
        else:
            mark = "💰"
        price_part = f"{offer.gold_price:,} 💰" if not st else st
        lines.append(f"{mark} {html.escape(g.name_ru)} — <b>{price_part}</b>")
    if len(lines) <= 4:
        lines.append("<i>В этом разделе пока нет книг.</i>")
    return "\n".join(lines)


def format_offer_detail_html(character: Character, grimoire_key: str) -> str:
    g = SKILL_GRIMOIRES.get(grimoire_key)
    if not g:
        return "Книга не найдена."
    offer = next(
        (o for o in lib.offers_for_archetype(g.archetype_key) if o.grimoire_key == grimoire_key),
        None,
    )
    price = offer.gold_price if offer else lib._gold_for_grimoire(g)
    st = lib.offer_status(character, grimoire_key)
    ok, err = lib.can_purchase(character, grimoire_key)
    lines = [
        html.escape(g.name_ru),
        "",
        f"<i>{html.escape(g.description_ru)}</i>",
        "",
        f"💰 Цена: <b>{price:,}</b>",
        f"Путь: {html.escape(lib.archetype_label_ru(g.archetype_key))}",
    ]
    if st:
        lines.append(f"Статус: <b>{html.escape(st)}</b>")
    if ok:
        lines.append("\n<i>После покупки книга попадёт в «Гримуары» — прочитайте её там. Передать нельзя.</i>")
    else:
        lines.append(f"\n⚠️ {html.escape(err)}")
    return "\n".join(lines)


async def try_purchase(
    session: AsyncSession,
    character: Character,
    grimoire_key: str,
) -> tuple[bool, str]:
    g = SKILL_GRIMOIRES.get(grimoire_key)
    if not g:
        return False, "Нет такой книги."
    ok, err = lib.can_purchase(character, grimoire_key)
    if not ok:
        return False, err
    price = lib._gold_for_grimoire(g)
    character_service.add_gold(
        character,
        -price,
        spend_for="grimoire_library",
        spend_kind="shop",
    )
    lib.mark_purchased(character, grimoire_key)
    grant_grimoire(character, grimoire_key, to_inventory=True)
    await session.flush()
    return True, (
        f"Куплено: {g.name_ru}. Списано {price:,} 💰.\n"
        "Книга в «Гримуарах» — прочитайте, когда будете готовы."
    )
