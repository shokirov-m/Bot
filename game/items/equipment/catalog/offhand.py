"""Вторая рука: щит, гримуар — примеры каталога."""

from __future__ import annotations

from typing import Any

from game.items.equipment.catalog._stub_utils import finalize_stub_list
from game.items.equipment.item_asset_paths import item_gear_png


def shield_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Щит нижнего кольца",
            "kind": "shield",
            "rarity": "common",
            "defense": 3,
            "vit": 1,
            "summary": "Круглый дуб с ободом железа.",
            "image_url": item_gear_png("catalog_shield_01"),
        },
        {
            "name": "Баклер лазутчика",
            "kind": "shield",
            "rarity": "common",
            "defense": 2,
            "dex": 1,
            "summary": "Лёгкий, не мешает бегу по ступеням.",
            "image_url": item_gear_png("catalog_shield_02"),
        },
        {
            "name": "Щит дубовых досок",
            "kind": "shield",
            "rarity": "uncommon",
            "defense": 4,
            "vit": 1,
            "summary": "Три слоя дерева склеены смолой башни.",
            "image_url": item_gear_png("catalog_shield_03"),
        },
        {
            "name": "Каппа стража",
            "kind": "shield",
            "rarity": "uncommon",
            "defense": 4,
            "str": 1,
            "summary": "Удлинённый щит для боя в коридоре.",
            "image_url": item_gear_png("catalog_shield_04"),
        },
        {
            "name": "Щит с гвоздём отчаяния",
            "kind": "shield",
            "rarity": "rare",
            "defense": 5,
            "str": 2,
            "summary": "Центральный шип для ответного толчка.",
            "image_url": item_gear_png("catalog_shield_05"),
        },
        {
            "name": "Башенный павез",
            "kind": "shield",
            "rarity": "rare",
            "defense": 6,
            "vit": 2,
            "summary": "Прямоугольник стали с вырезом под взгляд.",
            "image_url": item_gear_png("catalog_shield_06"),
        },
        {
            "name": "Эгида мокрого камня",
            "kind": "shield",
            "rarity": "epic",
            "defense": 7,
            "vit": 2,
            "int": 1,
            "summary": "Поверхность всегда слегка влажна — гасит удар.",
            "image_url": item_gear_png("catalog_shield_07"),
        },
        {
            "name": "Щит ста колец",
            "kind": "shield",
            "rarity": "epic",
            "defense": 8,
            "vit": 2,
            "luck": 1,
            "summary": "Кольца выгравированы по спирали к центру.",
            "image_url": item_gear_png("catalog_shield_08"),
        },
    ]
    return finalize_stub_list(rows)


def grimoire_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Блокнот ученика",
            "kind": "grimoire",
            "rarity": "common",
            "defense": 1,
            "int": 2,
            "summary": "Заметки по первым заклинаниям.",
            "image_url": item_gear_png("catalog_grimoire_01"),
        },
        {
            "name": "Сборник пыльных страниц",
            "kind": "grimoire",
            "rarity": "common",
            "defense": 1,
            "int": 1,
            "luck": 1,
            "summary": "Часть формул стёрта, но ядро сохранилось.",
            "image_url": item_gear_png("catalog_grimoire_02"),
        },
        {
            "name": "Гримуар зелёной искры",
            "kind": "grimoire",
            "rarity": "uncommon",
            "defense": 1,
            "int": 3,
            "summary": "Обложка светится при чтении вслух.",
            "image_url": item_gear_png("catalog_grimoire_03"),
        },
        {
            "name": "Кодекс перил",
            "kind": "grimoire",
            "rarity": "uncommon",
            "defense": 2,
            "int": 2,
            "vit": 1,
            "summary": "О защитных знаках у перил внутренних колец.",
            "image_url": item_gear_png("catalog_grimoire_04"),
        },
        {
            "name": "Фолиант сухого ветра",
            "kind": "grimoire",
            "rarity": "rare",
            "defense": 2,
            "int": 4,
            "summary": "Заклинания движения и срыва дыхания.",
            "image_url": item_gear_png("catalog_grimoire_05"),
        },
        {
            "name": "Чёрная книга ступеней",
            "kind": "grimoire",
            "rarity": "rare",
            "defense": 2,
            "int": 3,
            "dex": 1,
            "summary": "Проходы и ловушки нижних ярусов.",
            "image_url": item_gear_png("catalog_grimoire_06"),
        },
        {
            "name": "Атлас теней этажа",
            "kind": "grimoire",
            "rarity": "epic",
            "defense": 2,
            "int": 4,
            "luck": 2,
            "summary": "Карты невидимых линий маны между этажами.",
            "image_url": item_gear_png("catalog_grimoire_07"),
        },
        {
            "name": "Гримуар золотого переплёта",
            "kind": "grimoire",
            "rarity": "epic",
            "defense": 3,
            "int": 5,
            "summary": "Запретные страницы заперты на застёжку.",
            "image_url": item_gear_png("catalog_grimoire_08"),
        },
    ]
    return finalize_stub_list(rows)
