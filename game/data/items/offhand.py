"""Щиты, гримуары и кинжалы — каталог v3; PNG в tower_bot/assets/items/<stem>.png."""

from __future__ import annotations

from typing import Any

from game.data.items._finalize import finalize_stub_list
from utils.image_assets import item_gear_png, item_gear_png_rarity


def shield_examples() -> list[dict[str, Any]]:
    """Щиты."""
    rows: list[dict[str, Any]] = [
        # ОБЫЧНЫЕ (1-20)
        {
            "name": "Щит Рекрута",
            "kind": "shield",
            "rarity": "common",
            "defense": 20,
            "vit": 5,
            "summary": "Деревянный круг, обитый железом. Примет на себя первый удар. Шанс блока +3%.",
            "image_url": item_gear_png_rarity("recruit_shield", "common"),
            "export_floor_note": "1–20",
        },
        {
            "name": "Баклер Дуэлянта",
            "kind": "shield",
            "rarity": "common",
            "defense": 15,
            "dex": 8,
            "summary": "Маленький и легкий. Им удобно отбивать удары, а не принимать их в блок. Шанс уклонения +2%.",
            "image_url": item_gear_png_rarity("duelist_buckler", "common"),
            "export_floor_note": "1–20",
        },
        {
            "name": "Крышка от Люка",
            "kind": "shield",
            "rarity": "common",
            "defense": 25,
            "vit": 3,
            "summary": "Тяжелая чугунная крышка с улиц города за пределами Башни. Неказистая, но невероятно прочная. Снижение урона от дробящего оружия +5.",
            "image_url": item_gear_png_rarity("manhole_cover_shield", "common"),
            "export_floor_note": "1–20",
        },
        # НЕОБЫЧНЫЕ (11-30)
        {
            "name": "Башенный Щит Стража",
            "kind": "shield",
            "rarity": "uncommon",
            "defense": 45,
            "str": 8,
            "vit": 3,
            "summary": "Тяжелая стальная плита. За ней можно переждать огненный шторм. Шанс блока +2%.",
            "image_url": item_gear_png_rarity("tower_guard_shield", "uncommon"),
            "export_floor_note": "11–30",
        },
        {
            "name": "Каппа Защитника",
            "kind": "shield",
            "rarity": "uncommon",
            "defense": 50,
            "str": 8,
            "vit": 8,
            "hp_bonus": 50,
            "summary": "Удлиненный щит. Закрывает корпус и бедра.",
            "image_url": item_gear_png_rarity("protector_kappa", "uncommon"),
            "export_floor_note": "11–30",
        },
        {
            "name": "Зеркальный Щит",
            "kind": "shield",
            "rarity": "uncommon",
            "defense": 35,
            "int": 6,
            "summary": "Полированная сталь сияет как зеркало. Имеет шанс отразить магический снаряд обратно в противника (10%).",
            "image_url": item_gear_png_rarity("mirror_shield", "uncommon"),
            "export_floor_note": "11–30",
        },
        # РЕДКИЕ (21-50)
        {
            "name": "Шипастый Отчаяние",
            "kind": "shield",
            "rarity": "rare",
            "defense": 85,
            "str": 15,
            "dex": 6,
            "summary": "Длинный шип в центре наносит ответный урон атакующему врагу. Ответный урон: 15% от полученного.",
            "image_url": item_gear_png_rarity("spiked_despair", "rare"),
            "export_floor_note": "21–50",
        },
        {
            "name": "Павез Арбалетчика",
            "kind": "shield",
            "rarity": "rare",
            "defense": 95,
            "vit": 20,
            "luck": 5,
            "summary": "Большой прямоугольный щит. Можно установить на землю как укрытие. Защита от дальних атак +15%.",
            "image_url": item_gear_png_rarity("crossbowman_pavise", "rare"),
            "export_floor_note": "21–50",
        },
        {
            "name": "Панцирь Скарабея",
            "kind": "shield",
            "rarity": "rare",
            "defense": 75,
            "vit": 18,
            "summary": "Хитиновый щит, покрытый золотистым напылением. Символ возрождения и защиты от темных сил. Сопротивление магии +20%. Регенерация ХП +5 HP/мин.",
            "image_url": item_gear_png_rarity("scarab_shell_shield", "rare"),
            "export_floor_note": "21–50",
        },
        # ЭПИЧЕСКИЕ (41-80)
        {
            "name": "Эгида Морской Пены",
            "kind": "shield",
            "rarity": "epic",
            "defense": 155,
            "int": 15,
            "vit": 25,
            "summary": "Поверхность щита всегда влажная. Гасит магические атаки, снижая их урон на 25%. Сопротивление магии +25%.",
            "image_url": item_gear_png_rarity("sea_foam_aegis", "epic"),
            "export_floor_note": "41–80",
        },
        {
            "name": "Нерушимая Стена",
            "kind": "shield",
            "rarity": "epic",
            "defense": 170,
            "str": 18,
            "vit": 30,
            "summary": "Концентрические кольца на щите создают силовое поле. Увеличивает шанс полного блока. Шанс полного блока +10%.",
            "image_url": item_gear_png_rarity("unbreakable_wall", "epic"),
            "export_floor_note": "41–80",
        },
        {
            "name": "Чешуя Дракона Пустоты",
            "kind": "shield",
            "rarity": "epic",
            "defense": 140,
            "dex": 20,
            "vit": 15,
            "summary": "Черная чешуя, поглощающая свет и звуки вокруг. Владелец движется бесшумно и становится менее заметным. Скрытность +30%. Бесшумное передвижение.",
            "image_url": item_gear_png_rarity("void_dragon_scale", "epic"),
            "export_floor_note": "41–80",
        },
        # ЛЕГЕНДАРНЫЕ (70-90)
        {
            "name": "Бастион Королей",
            "kind": "shield",
            "rarity": "legendary",
            "defense": 300,
            "str": 35,
            "vit": 50,
            "summary": "Щит, выкованный из звездного металла. Отражает 30% получаемого урона обратно в атакующего.",
            "image_url": item_gear_png_rarity("kings_bastion", "legendary"),
            "export_floor_note": "70–90",
        },
        {
            "name": "Стена Плача",
            "kind": "shield",
            "rarity": "legendary",
            "defense": 280,
            "vit": 60,
            "int": 25,
            "summary": "Древний щит, покрытый письменами на неизвестном языке. При получении смертельного урона забирает всю ману владельца, чтобы полностью восстановить здоровье (раз в 10 минут).",
            "image_url": item_gear_png_rarity("wailing_wall", "legendary"),
            "export_floor_note": "70–90",
        },
        # МИФИЧЕСКИЕ (90+)
        {
            "name": "Абсолютный Нуль",
            "kind": "shield",
            "rarity": "mythic",
            "defense": 450,
            "vit": 80,
            "summary": "Щит из вечного льда, который никогда не тает. Замораживает атакующих врагов и создает ледяную ауру вокруг владельца. Шанс заморозки атакующего: 20%. Аура: Замедление врагов на 15%.",
            "image_url": item_gear_png_rarity("absolute_zero_shield", "mythic"),
            "export_floor_note": "90+",
        },
    ]
    return finalize_stub_list(rows)


def grimoire_examples() -> list[dict[str, Any]]:
    """Гримуары."""
    rows: list[dict[str, Any]] = [
        # ОБЫЧНЫЕ (1-20)
        {
            "name": "Блокнот Подмастерья",
            "kind": "grimoire",
            "rarity": "common",
            "defense": 8,
            "int": 8,
            "mp_bonus": 30,
            "summary": "Исписанные мелким почерком страницы. Основа основ.",
            "image_url": item_gear_png_rarity("apprentice_notebook", "common"),
            "export_floor_note": "1–20",
        },
        {
            "name": "Свиток Пыльных Истин",
            "kind": "grimoire",
            "rarity": "common",
            "defense": 6,
            "int": 6,
            "luck": 3,
            "summary": "Часть формул утеряна, но суть уловить можно. Снижение затрат маны +3%.",
            "image_url": item_gear_png_rarity("dusty_truths_scroll", "common"),
            "export_floor_note": "1–20",
        },
        # НЕОБЫЧНЫЕ (11-30)
        {
            "name": "Гримуар Зеленого Пламени",
            "kind": "grimoire",
            "rarity": "uncommon",
            "defense": 18,
            "int": 10,
            "summary": "Обложка теплая на ощупь. Увеличивает урон от огненных заклинаний. Урон огненных заклинаний +12%. Регенерация маны +8%.",
            "image_url": item_gear_png_rarity("green_flame_grimoire", "uncommon"),
            "export_floor_note": "11–30",
        },
        {
            "name": "Кодекс Перил",
            "kind": "grimoire",
            "rarity": "uncommon",
            "defense": 22,
            "int": 8,
            "vit": 8,
            "summary": "Содержит схемы защитных барьеров. Усиливает магический щит. Эффективность магического щита +15%.",
            "image_url": item_gear_png_rarity("codex_of_perils", "uncommon"),
            "export_floor_note": "11–30",
        },
        # РЕДКИЕ (21-50)
        {
            "name": "Фолиант Суховея",
            "kind": "grimoire",
            "rarity": "rare",
            "defense": 45,
            "int": 20,
            "summary": "Страницы шелестят, даже когда нет ветра. Увеличивает скорость произнесения заклинаний воздуха. Урон заклинаний воздуха +15%. Скорость каста +10%.",
            "image_url": item_gear_png_rarity("dry_wind_folio", "rare"),
            "export_floor_note": "21–50",
        },
        {
            "name": "Черная Книга Ступеней",
            "kind": "grimoire",
            "rarity": "rare",
            "defense": 50,
            "int": 20,
            "luck": 10,
            "summary": "Описания ловушек и монстров с нижних этажей. Шанс избежать ловушки. Обнаружение ловушек +20%. Знание монстров +15%.",
            "image_url": item_gear_png_rarity("black_book_of_stairs", "rare"),
            "export_floor_note": "21–50",
        },
        # ЭПИЧЕСКИЕ (41-80)
        {
            "name": "Атлас Астральных Теней",
            "kind": "grimoire",
            "rarity": "epic",
            "defense": 100,
            "int": 40,
            "luck": 18,
            "summary": "Карта магических потоков Башни. Позволяет предугадать следующую атаку босса. Шанс уклонения от атак боссов +15%. Знание слабых мест +10%.",
            "image_url": item_gear_png_rarity("astral_shadow_atlas", "epic"),
            "export_floor_note": "41–80",
        },
        {
            "name": "Гримуар Золотого Рассвета",
            "kind": "grimoire",
            "rarity": "epic",
            "defense": 110,
            "int": 45,
            "vit": 15,
            "mp_bonus": 150,
            "summary": "Застежка заперта, но книга сама открывается на нужной странице в час нужды. Восстанавливает ману каждый ход в бою: +5 ед.",
            "image_url": item_gear_png_rarity("golden_dawn_grimoire", "epic"),
            "export_floor_note": "41–80",
        },
        # ЛЕГЕНДАРНЫЕ (70-90)
        {
            "name": "Библиотека Мира",
            "kind": "grimoire",
            "rarity": "legendary",
            "defense": 180,
            "int": 65,
            "vit": 35,
            "summary": "В этой книге содержится знание о всех мирах. Позволяет использовать навык «Абсолютное Заклинание» (игнорирует сопротивление цели). Урон всех заклинаний +20%.",
            "image_url": item_gear_png_rarity("world_library", "legendary"),
            "export_floor_note": "70–90",
        },
        # МИФИЧЕСКИЕ (90+)
        {
            "name": "Некрономикон Башни",
            "kind": "grimoire",
            "rarity": "mythic",
            "defense": 280,
            "int": 90,
            "vit": 60,
            "summary": "Переплет из кожи неизвестного существа, страницы исписаны кровью. Содержит запретные заклинания жизни и смерти. Позволяет воскрешать павших врагов как слуг. Вампиризм от заклинаний +12%.",
            "image_url": item_gear_png_rarity("tower_necronomicon", "mythic"),
            "export_floor_note": "90+",
        },
        {
            "name": "Книга Начала и Конца",
            "kind": "grimoire",
            "rarity": "mythic",
            "defense": 300,
            "int": 100,
            "luck": 50,
            "summary": "Первая и последняя страница соприкасаются, образуя бесконечную петлю времени. Дарует владельцу способность манипулировать временем в бою и откатывать фатальные ошибки. Эффект: Откат времени на 5 секунд при смерти (перезарядка 30 минут).",
            "image_url": item_gear_png_rarity("book_of_beginning_and_end", "mythic"),
            "export_floor_note": "90+",
        },
    ]
    return finalize_stub_list(rows)


def dagger_examples() -> list[dict[str, Any]]:
    """Кинжалы (по 1 на редкость)."""
    rows: list[dict[str, Any]] = [
        # ОБЫЧНЫЙ (1-20)
        {
            "name": "Зазубренный Кинжал",
            "kind": "dagger",
            "rarity": "common",
            "attack": 12,
            "dex": 3,
            "summary": "Простой кинжал с зазубренным лезвием. Наносит кровоточащие раны. Шанс вызвать кровотечение +5%.",
            "image_url": item_gear_png_rarity("jagged_dagger", "common"),
            "export_floor_note": "1–20",
        },
        # НЕОБЫЧНЫЙ (11-30)
        {
            "name": "Клинок Танцора Теней",
            "kind": "dagger",
            "rarity": "uncommon",
            "attack": 22,
            "dex": 12,
            "summary": "Легкий клинок с балансом у рукояти. Идеален для метания и быстрых атак. Скорость атаки +10%.",
            "image_url": item_gear_png_rarity("shadow_dancer_blade", "uncommon"),
            "export_floor_note": "11–30",
        },
        # РЕДКИЙ (21-50)
        {
            "name": "Клык Аспида",
            "kind": "dagger",
            "rarity": "rare",
            "attack": 38,
            "dex": 18,
            "vit": 5,
            "summary": "Кинжал, пропитанный ядом древнего аспида. При ударе с шансом 15% отравляет цель (урон 20% от атаки в секунду, 5 сек).",
            "image_url": item_gear_png_rarity("asp_fang", "rare"),
            "export_floor_note": "21–50",
        },
        # ЭПИЧЕСКИЙ (41-80)
        {
            "name": "Милосердие",
            "kind": "dagger",
            "rarity": "epic",
            "attack": 65,
            "dex": 30,
            "luck": 15,
            "summary": "Узкий стилет, способный найти щель в любом доспехе. Критический урон +50%. Игнорирование 20% брони цели.",
            "image_url": item_gear_png_rarity("mercy_stiletto", "epic"),
            "export_floor_note": "41–80",
        },
        # ЛЕГЕНДАРНЫЙ (70-90)
        {
            "name": "Клинок Короля-Лича",
            "kind": "dagger",
            "rarity": "legendary",
            "attack": 110,
            "dex": 40,
            "int": 30,
            "summary": "Кинжал из вечного льда, выкованный в царстве мертвых. При критическом ударе замораживает цель на 2 секунды и высасывает жизнь. Вампиризм +8%.",
            "image_url": item_gear_png_rarity("lich_king_blade", "legendary"),
            "export_floor_note": "70–90",
        },
        # МИФИЧЕСКИЙ (90+)
        {
            "name": "Последний Довод",
            "kind": "dagger",
            "rarity": "mythic",
            "attack": 180,
            "dex": 60,
            "luck": 40,
            "vit": 30,
            "summary": "Кинжал, существующий вне времени и пространства. При ударе со спины по цели с менее чем 20% здоровья — мгновенное убийство (не работает на боссов). Всегда наносит критический удар по целям с полным здоровьем.",
            "image_url": item_gear_png_rarity("last_argument", "mythic"),
            "export_floor_note": "90+",
        },
    ]
    return finalize_stub_list(rows)