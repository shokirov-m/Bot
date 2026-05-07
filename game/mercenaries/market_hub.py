"""Хаб чёрного рынка: локации, NPC, тексты диалогов и мини-квесты."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MarketLocation:
    key: str
    title_ru: str
    intro_ru: str
    npc_name: str


LOCATIONS: tuple[MarketLocation, ...] = (
    MarketLocation(
        key="lots",
        title_ru="Площадь лотов",
        intro_ru="Жабс хрустит монетами и смотрит на тебя жадным, но внимательным взглядом.",
        npc_name="Жабс",
    ),
    MarketLocation(
        key="guard",
        title_ru="Пост охраны",
        intro_ru="Молчун стоит у колонны. Его рука лежит на эфесе — не угроза, а напоминание.",
        npc_name="Молчун",
    ),
    MarketLocation(
        key="forge_shadow",
        title_ru="Лавка теней",
        intro_ru="Кузнец без лица выставляет клинки, что не отражают света.",
        npc_name="Кузнец Тени",
    ),
    MarketLocation(
        key="alchemy",
        title_ru="Закоулок алхимика",
        intro_ru="Пузыри с тёмной жидкостью тихо переливаются на полках.",
        npc_name="алхимик Варен",
    ),
    MarketLocation(
        key="contracts",
        title_ru="Доска контрактов",
        intro_ru="Деревянная доска забита гвоздями и обрывками пергамента.",
        npc_name="писарь контрактов",
    ),
    MarketLocation(
        key="rumors",
        title_ru="Угол слухов",
        intro_ru="Старушка с закрытыми глазами что-то шепчет — возможно, тебе.",
        npc_name="Невидимка",
    ),
)


def dialog_pool(location_key: str) -> list[str]:
    if location_key == "guard":
        return [
            "Молчун кивает в сторону прохода — порядок держится железом, не словами.",
            "«Тишина — лучший союзник», — едва слышно, будто это не он сказал.",
        ]
    if location_key == "forge_shadow":
        return [
            "«Сталь помнит руку. Выбери, кому служить будет клинок.»",
            "На прилавке — три ножны, все пустые. Товар под заказ.",
        ]
    if location_key == "alchemy":
        return [
            "«Это зелье восстанавливает не плоть — а дух наёмника после тяжёлого боя.»",
            "Реагенты пахнут грозой и старой кровью.",
        ]
    if location_key == "contracts":
        return [
            "«Доставь печать на 31-й — и получишь не только золото.»",
            "Контракт помечен сургучом с символом башни.",
        ]
    if location_key == "rumors":
        return [
            "«На 40-м этаже слышат стук… не от сердца камня, а от чего-то заключённого.»",
            "«Ищущий тайник пусть смотрит под плиты, где вода не течёт.»",
        ]
    return [
        "Жабс широко улыбается: «Сегодня удачный день — для меня. А для тебя?»",
        "«Пленники? Нет-нет… только добровольцы с долгами», — он хрипло смеётся.",
    ]
