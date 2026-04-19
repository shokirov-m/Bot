"""Щиты и гримуары — баланс v2.0; картинка — заглушка."""

from __future__ import annotations

from typing import Any

from game.data.items._finalize import finalize_stub_list
from utils.image_assets import item_gear_png

_IMG = item_gear_png("placeholder_item")


def shield_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Щит Рекрута",
            "kind": "shield",
            "rarity": "common",
            "defense": 20,
            "vit": 10,
            "summary": "Деревянный круг, обитый железом. Примет на себя первый удар.",
            "image_url": _IMG,
        },
        {
            "name": "Баклер Дуэлянта",
            "kind": "shield",
            "rarity": "common",
            "defense": 15,
            "dex": 12,
            "summary": "Маленький и легкий. Им удобно отбивать удары, а не принимать их в блок.",
            "image_url": _IMG,
        },
        {
            "name": "Башенный Щит Стража",
            "kind": "shield",
            "rarity": "uncommon",
            "defense": 45,
            "vit": 20,
            "str": 10,
            "summary": "Тяжелая стальная плита. За ней можно переждать огненный шторм.",
            "image_url": _IMG,
        },
        {
            "name": "Каппа Защитника",
            "kind": "shield",
            "rarity": "uncommon",
            "defense": 50,
            "str": 15,
            "vit": 10,
            "summary": "Удлиненный щит. Закрывает корпус и бедра.",
            "image_url": _IMG,
        },
        {
            "name": "Шипастый Отчаяние",
            "kind": "shield",
            "rarity": "rare",
            "defense": 85,
            "str": 25,
            "dex": 10,
            "summary": "Длинный шип в центре наносит ответный урон атакующему врагу.",
            "image_url": _IMG,
        },
        {
            "name": "Павез Арбалетчика",
            "kind": "shield",
            "rarity": "rare",
            "defense": 95,
            "vit": 30,
            "luck": 10,
            "summary": "Большой прямоугольный щит. Можно установить на землю как укрытие.",
            "image_url": _IMG,
        },
        {
            "name": "Эгида Морской Пены",
            "kind": "shield",
            "rarity": "epic",
            "defense": 155,
            "int": 20,
            "vit": 35,
            "summary": "Поверхность щита всегда влажная. Гасит магические атаки, снижая их урон на 25%.",
            "image_url": _IMG,
        },
        {
            "name": "Нерушимая Стена",
            "kind": "shield",
            "rarity": "epic",
            "defense": 170,
            "vit": 45,
            "str": 25,
            "luck": 10,
            "summary": "Концентрические кольца на щите создают силовое поле. Увеличивает шанс полного блока.",
            "image_url": _IMG,
        },
        {
            "name": "Бастион Королей",
            "kind": "shield",
            "rarity": "legendary",
            "defense": 300,
            "vit": 70,
            "str": 50,
            "summary": "Щит, выкованный из звездного металла. Отражает 30% получаемого урона обратно в атакующего.",
            "image_url": _IMG,
        },
    ]
    return finalize_stub_list(rows)


def grimoire_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Блокнот Подмастерья",
            "kind": "grimoire",
            "rarity": "common",
            "defense": 10,
            "int": 15,
            "summary": "Исписанные мелким почерком страницы. Основа основ.",
            "image_url": _IMG,
        },
        {
            "name": "Свиток Пыльных Истин",
            "kind": "grimoire",
            "rarity": "common",
            "defense": 12,
            "int": 12,
            "luck": 5,
            "summary": "Часть формул утеряна, но суть уловить можно.",
            "image_url": _IMG,
        },
        {
            "name": "Гримуар Зеленого Пламени",
            "kind": "grimoire",
            "rarity": "uncommon",
            "defense": 25,
            "int": 30,
            "summary": "Обложка теплая на ощупь. Увеличивает урон от огненных заклинаний.",
            "image_url": _IMG,
        },
        {
            "name": "Кодекс Перил",
            "kind": "grimoire",
            "rarity": "uncommon",
            "defense": 30,
            "int": 25,
            "vit": 15,
            "summary": "Содержит схемы защитных барьеров. Усиливает магический щит.",
            "image_url": _IMG,
        },
        {
            "name": "Фолиант Суховея",
            "kind": "grimoire",
            "rarity": "rare",
            "defense": 65,
            "int": 45,
            "summary": "Страницы шелестят, даже когда нет ветра. Увеличивает скорость произнесения заклинаний воздуха.",
            "image_url": _IMG,
        },
        {
            "name": "Черная Книга Ступеней",
            "kind": "grimoire",
            "rarity": "rare",
            "defense": 70,
            "int": 40,
            "luck": 20,
            "summary": "Описания ловушек и монстров с нижних этажей. Шанс избежать ловушки.",
            "image_url": _IMG,
        },
        {
            "name": "Атлас Астральных Теней",
            "kind": "grimoire",
            "rarity": "epic",
            "defense": 140,
            "int": 55,
            "luck": 30,
            "summary": "Карта магических потоков Башни. Позволяет предугадать следующую атаку босса.",
            "image_url": _IMG,
        },
        {
            "name": "Гримуар Золотого Рассвета",
            "kind": "grimoire",
            "rarity": "epic",
            "defense": 155,
            "int": 65,
            "vit": 20,
            "summary": "Застежка заперта, но книга сама открывается на нужной странице в час нужды. Восстанавливает ману при убийстве врага.",
            "image_url": _IMG,
        },
        {
            "name": "Библиотека Мира",
            "kind": "grimoire",
            "rarity": "legendary",
            "defense": 250,
            "int": 90,
            "vit": 50,
            "summary": "В этой книге содержится знание о всех мирах. Позволяет использовать навык «Абсолютное Заклинание» (игнорирует сопротивление цели).",
            "image_url": _IMG,
        },
    ]
    return finalize_stub_list(rows)
