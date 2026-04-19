"""Оружие каталога — баланс v2.0 (см. предмети 0,1.txt); картинки — заглушка."""

from __future__ import annotations

from typing import Any

from game.data.items._finalize import finalize_stub_list
from utils.image_assets import item_gear_png

_IMG = item_gear_png("placeholder_item")


def weapon_main_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Путь Новичка",
            "kind": "weapon",
            "hand": "main",
            "rarity": "common",
            "attack": 15,
            "weapon_type": "blade",
            "enchant": 0,
            "summary": "Первый клинок, прошедший закалку у врат Башни. Надежен и остр.",
            "image_url": _IMG,
        },
        {
            "name": "Копьё Дозорного",
            "kind": "weapon",
            "hand": "main",
            "rarity": "common",
            "attack": 18,
            "weapon_type": "polearm",
            "enchant": 0,
            "summary": "Длинное древко с вороненым наконечником. Держит врага на дистанции удара сердца.",
            "image_url": _IMG,
        },
        {
            "name": "Колун Башни",
            "kind": "weapon",
            "hand": "main",
            "rarity": "uncommon",
            "attack": 35,
            "weapon_type": "axe",
            "enchant": 0,
            "summary": "Тяжелое лезвие, способное пробить как хитин монстра, так и дубовую дверь.",
            "image_url": _IMG,
        },
        {
            "name": "Громовой Молот",
            "kind": "weapon",
            "hand": "main",
            "rarity": "uncommon",
            "attack": 40,
            "weapon_type": "hammer",
            "enchant": 0,
            "summary": "Каждый удар отдается глухим эхом в костях противника, оглушая его.",
            "image_url": _IMG,
        },
        {
            "name": "Лук Забытых Троп",
            "kind": "weapon",
            "hand": "main",
            "rarity": "uncommon",
            "attack": 38,
            "weapon_type": "bow",
            "two_handed": True,
            "enchant": 0,
            "summary": "Двуручный. Тетива сплетена из волос лесных духов, стрела летит абсолютно бесшумно.",
            "image_url": _IMG,
        },
        {
            "name": "Посох Раскола",
            "kind": "weapon",
            "hand": "main",
            "rarity": "rare",
            "attack": 70,
            "weapon_type": "staff",
            "enchant": 1,
            "summary": "По древку бегут трещины чистой энергии. Увеличивает резерв маны владельца.",
            "image_url": _IMG,
        },
        {
            "name": "Судный Топор",
            "kind": "weapon",
            "hand": "main",
            "rarity": "rare",
            "attack": 95,
            "weapon_type": "axe",
            "enchant": 1,
            "summary": "Лезвие пахнет озоном и старой кровью. Шанс нанести критический удар увеличен.",
            "image_url": _IMG,
        },
        {
            "name": "Сияние Абсолюта",
            "kind": "weapon",
            "hand": "main",
            "rarity": "epic",
            "attack": 160,
            "weapon_type": "blade",
            "enchant": 2,
            "summary": "Клинок из чистого света. Рассекает не только плоть, но и магические щиты.",
            "image_url": _IMG,
        },
        {
            "name": "Погибель Миров",
            "kind": "weapon",
            "hand": "main",
            "rarity": "legendary",
            "attack": 280,
            "weapon_type": "blade",
            "enchant": 3,
            "summary": "Выкован в сердце умирающей звезды. Одно его присутствие заставляет реальность дрожать.",
            "image_url": _IMG,
        },
    ]
    return finalize_stub_list(rows)


def weapon_offhand_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Заточка Теней",
            "kind": "weapon",
            "hand": "off",
            "rarity": "common",
            "attack": 12,
            "weapon_type": "dagger",
            "enchant": 0,
            "summary": "Лёгкий клинок для левой руки. Идеален для парирования и неожиданных выпадов.",
            "image_url": _IMG,
        },
        {
            "name": "Кортик Канатоходца",
            "kind": "weapon",
            "hand": "off",
            "rarity": "common",
            "attack": 14,
            "weapon_type": "dagger",
            "enchant": 0,
            "summary": "Узкое лезвие с серрейтором. Перерезает веревки и сухожилия как масло.",
            "image_url": _IMG,
        },
        {
            "name": "Стилет Безмолвия",
            "kind": "weapon",
            "hand": "off",
            "rarity": "uncommon",
            "attack": 32,
            "dex": 5,
            "weapon_type": "dagger",
            "enchant": 0,
            "summary": "Невесомый клинок. При атаке со спины игнорирует часть брони цели.",
            "image_url": _IMG,
        },
        {
            "name": "Крюк Мясника",
            "kind": "weapon",
            "hand": "off",
            "rarity": "uncommon",
            "attack": 35,
            "weapon_type": "dagger",
            "enchant": 0,
            "summary": "Изогнутая сталь. Цепляет врага, не давая ему сбежать.",
            "image_url": _IMG,
        },
        {
            "name": "Кинжал Проклятой Крови",
            "kind": "weapon",
            "hand": "off",
            "rarity": "rare",
            "attack": 68,
            "weapon_type": "dagger",
            "enchant": 1,
            "summary": "Желобок на лезвии всегда влажный. Отравляет цель при нанесении урона.",
            "image_url": _IMG,
        },
        {
            "name": "Парный Клинок Судьбы",
            "kind": "weapon",
            "hand": "off",
            "rarity": "rare",
            "attack": 75,
            "weapon_type": "blade",
            "enchant": 0,
            "summary": "Укороченная версия легендарного меча. Идеально сбалансирован для боя двумя руками.",
            "image_url": _IMG,
        },
        {
            "name": "Сокрушитель Черепов",
            "kind": "weapon",
            "hand": "off",
            "rarity": "rare",
            "attack": 72,
            "weapon_type": "hammer",
            "enchant": 1,
            "summary": "Тяжелое навершие на короткой рукояти. Оглушает врага при сильном ударе.",
            "image_url": _IMG,
        },
        {
            "name": "Кинжал Искажения",
            "kind": "weapon",
            "hand": "off",
            "rarity": "epic",
            "attack": 150,
            "luck": 15,
            "weapon_type": "dagger",
            "enchant": 2,
            "summary": "Лезвие не отбрасывает бликов, оно поглощает свет. Дает шанс полностью уклониться от атаки.",
            "image_url": _IMG,
        },
        {
            "name": "Клык Бездны",
            "kind": "weapon",
            "hand": "off",
            "rarity": "legendary",
            "attack": 255,
            "dex": 25,
            "weapon_type": "dagger",
            "enchant": 3,
            "summary": "Вырван у Древнего Змея. Каждая атака восстанавливает владельцу часть нанесенного урона.",
            "image_url": _IMG,
        },
    ]
    return finalize_stub_list(rows)


def two_handed_weapon_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "Клеймо Рекрута",
            "kind": "weapon",
            "hand": "main",
            "two_handed": True,
            "rarity": "common",
            "attack": 22,
            "weapon_type": "blade",
            "enchant": 0,
            "summary": "Тяжелый клинок, требующий двух рук. Учит воина держать строй.",
            "image_url": _IMG,
        },
        {
            "name": "Посох Странника",
            "kind": "weapon",
            "hand": "main",
            "two_handed": True,
            "rarity": "common",
            "attack": 20,
            "weapon_type": "staff",
            "enchant": 0,
            "summary": "Крепкое дерево. Помогает и в бою, и в долгом пути по этажам.",
            "image_url": _IMG,
        },
        {
            "name": "Секира Врат",
            "kind": "weapon",
            "hand": "main",
            "two_handed": True,
            "rarity": "uncommon",
            "attack": 45,
            "weapon_type": "axe",
            "enchant": 0,
            "summary": "Огромное лезвие на длинной рукояти. Сносит любые преграды.",
            "image_url": _IMG,
        },
        {
            "name": "Лук Снежных Вершин",
            "kind": "weapon",
            "hand": "main",
            "two_handed": True,
            "rarity": "uncommon",
            "attack": 42,
            "weapon_type": "bow",
            "enchant": 0,
            "summary": "Изготовлен из кости ледяного дракона. Стрелы замедляют цель.",
            "image_url": _IMG,
        },
        {
            "name": "Коса Жнеца",
            "kind": "weapon",
            "hand": "main",
            "two_handed": True,
            "rarity": "uncommon",
            "attack": 48,
            "weapon_type": "polearm",
            "enchant": 0,
            "summary": "Широкий взмах срезает все живое на своем пути.",
            "image_url": _IMG,
        },
        {
            "name": "Молот Тектонического Сдвига",
            "kind": "weapon",
            "hand": "main",
            "two_handed": True,
            "rarity": "rare",
            "attack": 85,
            "weapon_type": "hammer",
            "enchant": 1,
            "summary": "Ударная волна дробит камень под ногами врагов, сбивая их с ног.",
            "image_url": _IMG,
        },
        {
            "name": "Клеймор Северного Сияния",
            "kind": "weapon",
            "hand": "main",
            "two_handed": True,
            "rarity": "rare",
            "attack": 90,
            "weapon_type": "blade",
            "enchant": 1,
            "summary": "Лезвие переливается зеленым и синим. Наносит дополнительный магический урон.",
            "image_url": _IMG,
        },
        {
            "name": "Сотня Шрамов",
            "kind": "weapon",
            "hand": "main",
            "two_handed": True,
            "rarity": "epic",
            "attack": 175,
            "weapon_type": "blade",
            "enchant": 2,
            "summary": "Каждая зарубка на лезвии — это история о поверженном Хранителе этажа.",
            "image_url": _IMG,
        },
        {
            "name": "Разрушитель Башен",
            "kind": "weapon",
            "hand": "main",
            "two_handed": True,
            "rarity": "legendary",
            "attack": 300,
            "str": 40,
            "weapon_type": "axe",
            "enchant": 3,
            "summary": "Топор, которым был срублен Иггдрасиль. Один удар — и этаж Башни содрогается.",
            "image_url": _IMG,
        },
    ]
    return finalize_stub_list(rows)


def _build_all_weapons() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for i, row in enumerate(weapon_main_examples(), 1):
        kid = f"weapon_main_{i:02d}"
        out[kid] = {**row, "id": kid}
    for i, row in enumerate(weapon_offhand_examples(), 1):
        kid = f"weapon_off_{i:02d}"
        out[kid] = {**row, "id": kid}
    for i, row in enumerate(two_handed_weapon_examples(), 1):
        kid = f"weapon_2h_{i:02d}"
        out[kid] = {**row, "id": kid}
    return out


ALL_WEAPONS: dict[str, dict[str, Any]] = _build_all_weapons()


def get_weapon(weapon_id: str) -> dict[str, Any] | None:
    return ALL_WEAPONS.get(weapon_id)


def weapons_for_tier(tier: int) -> list[dict[str, Any]]:
    return [w for w in ALL_WEAPONS.values() if int(w.get("tier", 0)) == tier]
