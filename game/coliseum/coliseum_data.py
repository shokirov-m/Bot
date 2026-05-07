"""
Данные бойцов Колизея (50 подряд). Стихии ТЗ маппятся на движок в ELEMENT_TO_ENGINE.
Чемпионы: каждый 10-й — множитель ×2 к золоту/опыту в coliseum_service (не дублировать в таблице).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from game.floors.monsters import FloorMonsterSpawn, MonsterTemplate

# ─── Стихии из ТЗ → элемент монстра в бою (fire|ice|lightning|dark|light|earth)
ELEMENT_TO_ENGINE: dict[str, str] = {
    "fire": "fire",
    "water": "ice",
    "ice": "ice",
    "wind": "lightning",
    "lightning": "lightning",
    "poison": "earth",  # яд в ТЗ: визуально/хуки, базовый резист — earth
    "dark": "dark",
    "light": "light",
    "earth": "earth",
    "none": "earth",
}

SpecialId = Literal[
    "none",
    "blind_2",  # 6 Ива
    "fear_30",  # 11 Зара
    "sleep_first",  # 15 Айша
    "monster_evasion_30",  # 20 Аргус — игрок чаще промахивается
    "gust_20",  # 25 Зефир
    "aid_barrier",  # 29 Аид
    "mulan_pet",  # 33 Мулан
    "wukong_rage",  # 39 Сунь Укун
    "loki_illusion",  # 43 Локи
    "fenrir_pet",  # 48 Фенрир
    "kronos_skip",  # 49 Кронос
    "zeus_bolt",  # 50 Зевс
]


@dataclass(frozen=True, slots=True)
class ColiseumFighter:
    id: int
    name: str
    phrase: str
    victory_quote: str
    hp: int
    atk: int
    defense: int
    exp_reward: int
    gold_reward: int
    required_level: int
    element_tz: str
    is_champion: bool
    special: SpecialId
    loot_id: str  # ключ в coliseum_rewards


# Множитель ATK всех бойцов колизея в бою (баланс).
# Баланс урона бойцов колизея по игроку (база атаки × множитель).
COLISEUM_ENEMY_ATK_MULT = 5.0

COLISEUM_TEMPLATE_KEY = "coliseum_gladiator"

COLISEUM_TEMPLATE = MonsterTemplate(
    COLISEUM_TEMPLATE_KEY,
    "Боец Колизея",
    "⚔️",
    "earth",
    "Колизей не прощает слабых.",
)

# Имена и фразы; статы — сглаженная кривая 1–50
_NAMES: dict[int, str] = {
    1: "Кассий Пепельный",
    2: "Дорн Железный",
    3: "Лира Скорпия",
    4: "Ганнок Костяной",
    5: "Серена Клинок",
    6: "Ива Теневая",
    7: "Торин Молот",
    8: "Мира Остроглазая",
    9: "Векс Тихий",
    10: "Громовержец Карн",
    11: "Зара Длань",
    12: "Руфус Кольчуга",
    13: "Найла Пепел",
    14: "Орикс Скиталец",
    15: "Айша Сновидица",
    16: "Петра Каменная",
    17: "Кай Кольцо",
    18: "Селин Лёд",
    19: "Морд Крюк",
    20: "Аргус Всевидящий",
    21: "Тея Вихрь",
    22: "Драско Пламя",
    23: "Ирин Тьма",
    24: "Люк Светоносный",
    25: "Зефир Ускользающий",
    26: "Борн Камень",
    27: "Сив Коготь",
    28: "Астра Уголь",
    29: "Аид Некромант",
    30: "Титан Киран",
    31: "Юн Фонарь",
    32: "Хель Туман",
    33: "Мулан Стальная",
    34: "Рагнар Безликий",
    35: "Элира Шип",
    36: "Горн Багряный",
    37: "Сильва Корень",
    38: "Неро Цепь",
    39: "Сунь Укун Подражатель",
    40: "Валькирия Фрейя",
    41: "Один Странник",
    42: "Тор Молотобой",
    43: "Локи Обманщик",
    44: "Йормунганд Колечко",
    45: "Хель Холод",
    46: "Бальдур Сияние",
    47: "Тюр Длань",
    48: "Фенрир Разрыватель",
    49: "Кронос Древний",
    50: "Зевс Олимпийский",
}

_SPECIAL_BY_ID: dict[int, SpecialId] = {
    6: "blind_2",
    11: "fear_30",
    15: "sleep_first",
    20: "monster_evasion_30",
    25: "gust_20",
    29: "aid_barrier",
    33: "mulan_pet",
    39: "wukong_rage",
    43: "loki_illusion",
    48: "fenrir_pet",
    49: "kronos_skip",
    50: "zeus_bolt",
}

# Одна реплика соперника / трибуна после твоей победы над этим бойцом.
_VICTORY_QUOTES: dict[int, str] = {
    1: "Пепел на арене — мой след. Ты прошёл по нему… значит, жар в тебе сильнее.",
    2: "Железо сломалось раньше воли. Признаю — удар был честным.",
    3: "Жало не успело. Ты быстрее яда — это редкость.",
    4: "Кости хрустят не так громко, как твоя победа. Иди дальше.",
    5: "Клинок не сказал последнее слово — сказал ты. Так и запомнят зрители.",
    6: "Тьма отступила… или ты просто умеешь видеть в ней дорогу.",
    7: "Молот замолчал. Значит, нашёлся кто-то тяжелее удара.",
    8: "Я целилась в промах — промахнулась сама. Острота твоя, не моя.",
    9: "Тихий конец — не про меня. Но сегодня арена громче тебя.",
    10: "Гром обошёл меня стороной… или ты был молнией первой. Чемпион сменился.",
    11: "Страх не подчинился мне — зато подчинился твоему ритму. Длань опущена.",
    12: "Кольчуга дрогнула. Ржавчина в сердце — нет, в сердце у тебя сталь.",
    13: "Пепел оседает на побеждённых. Сегодня он на мне — и это справедливо.",
    14: "Скиталец нашёл конец пути. Пусть твой путь будет длиннее моего.",
    15: "Сон разбился… как иллюзия. Ты разбудил меня ударом — благодарю за ясность.",
    16: "Камень треснул. Значит, воля в тебе — неослабевающая.",
    17: "Кольцо замкнуто не вокруг тебя — вокруг моего поражения. Честная игра.",
    18: "Лёд растаял от жара боя. Твой жар оказался сильнее мороза.",
    19: "Крюк не удержал. У тебя цепь посильнее — из побед.",
    20: "Я видел всё… кроме этой концовки. Всевидящий ослеплён твоей настойчивостью.",
    21: "Вихрь утих. Ты оказался центром шторма, а не я.",
    22: "Пламя погасло не от ветра — от твоего натиска. Жги дальше.",
    23: "Тьма не забрала тебя — ты вырвал свет из неё. Уважаю.",
    24: "Свет не ослепил — значит, ты смотрел прямо. Редкая для арены черта.",
    25: "Ускользнул бы ещё раз… если бы не твоя хватка на долю секунды.",
    26: "Камень крошится. Ты тяжелее гор — подкопайся под следующего.",
    27: "Коготь сломался о твою защиту… или о твоё упрямство. Оба достойны уважения.",
    28: "Уголь догорает ровно. Сегодня погас я — осталась жизнь в тебе.",
    29: "Барьер пал. Некромантия не спасла — спасать было некого, кроме чести.",
    30: "Титан пошатнулся. Земля запомнит твой шаг громче моего.",
    31: "Фонарь погас в шуме трибун — зато зажёгся твой.",
    32: "Туман рассеялся. Шаг за шагом ты вывел меня из слепоты поражения.",
    33: "Сталь звенит по-другому, когда её сбивают с ног. Ты сбил ритм — я сдаюсь.",
    34: "Лицо не спасло — узнал арену твоё, не моё. Пусть им запомнят тебя.",
    35: "Шип сломался. Боль останется у меня — триумф у тебя.",
    36: "Багрянец бледнеет перед твоей победой. Кровь боя — на твоей стороне счёта.",
    37: "Корни не удержали — вырвался ты, как бурей. Лесной дух кланяется.",
    38: "Цепь лопнула звеном. Свободен ты — и этим опаснее любого пленника.",
    39: "Ярость утихла… бамбук всё ещё гнётся, но пал под твоей волей.",
    40: "Крылья сложены. Валькирия выбирает победителя — сегодня это ты.",
    41: "Один глаз видел много — но не эту точку. Странник уступает дорогу.",
    42: "Молот не пробил твою стойкость. Тор отступает с уважением.",
    43: "Обман рассеялся, как дым. Остаётся правда: ты сильнее иллюзий.",
    44: "Кольцо сжалось не вокруг тебя — вокруг моего дыхания. Ты вышел наружу.",
    45: "Холод не победил жар схватки. Твоё сердце согрело трибуны.",
    46: "Сияние не спасло — ты ударил честнее слепоты славы. Бальдур кивает.",
    47: "Длань судьбы на этот раз пала на плечо победителю — на твоё.",
    48: "Клыки не удержали. Зверь внутри согласен: охотник — ты.",
    49: "Время остановилось… для меня. Для тебя оно бежит вперёд — беги.",
    50: "Олимп на миг замолчал. Даже гром уступает тому, кто стоит последним.",
}

_ELEMENTS_CYCLE = (
    "fire",
    "earth",
    "ice",
    "lightning",
    "dark",
    "light",
    "water",
    "wind",
    "poison",
    "none",
)


def _scaled_stats(fid: int) -> tuple[int, int, int, int, int]:
    """hp, atk, defense, exp_reward, gold_reward — база без чемпионского ×2."""
    t = (fid - 1) / 49.0
    hp = int(280 + t * 92800)
    atk = int(7 + t * 795)
    defense = int(t * 188)
    exp = int(45 + t * 46500)
    gold = int(28 + t * 10800)
    return hp, atk, defense, exp, gold


def _build_all_fighters() -> tuple[ColiseumFighter, ...]:
    out: list[ColiseumFighter] = []
    for fid in range(1, 51):
        hp, atk, dfn, exp, gold = _scaled_stats(fid)
        ch = fid % 10 == 0
        el = _ELEMENTS_CYCLE[(fid - 1) % len(_ELEMENTS_CYCLE)]
        # Боец №10: заданный итог ATK в бою (× COLISEUM_ENEMY_ATK_MULT) и стихия молнии.
        if fid == 10:
            atk = 210  # 210 × 5.0 → 1050 в карточке и в расчёте урона монстра
            el = "lightning"
        if fid == 18:
            atk = 460  # 460 × 5.0 → 2300
        spec = _SPECIAL_BY_ID.get(fid, "none")
        phrase = (
            f"«{_NAMES[fid].split()[0]} не отступит!»"
            if fid not in (10, 20, 30, 40, 50)
            else f"«Я — стена Колизея №{fid}!»"
        )
        vq = _VICTORY_QUOTES.get(fid, "Арена хранит тишину — сегодня в ней победитель только ты.")
        out.append(
            ColiseumFighter(
                id=fid,
                name=_NAMES[fid],
                phrase=phrase,
                victory_quote=vq,
                hp=hp,
                atk=atk,
                defense=dfn,
                exp_reward=exp,
                gold_reward=gold,
                required_level=max(1, min(50, fid)),
                element_tz=el,
                is_champion=ch,
                special=spec,
                loot_id=f"loot_{fid}",
            ),
        )
    return tuple(out)


COLISEUM_FIGHTERS: tuple[ColiseumFighter, ...] = _build_all_fighters()
_BY_ID: dict[int, ColiseumFighter] = {f.id: f for f in COLISEUM_FIGHTERS}


def fighter_by_id(fid: int) -> ColiseumFighter | None:
    return _BY_ID.get(int(fid))


def normalized_battle_element(element_tz: str) -> str:
    k = (element_tz or "none").strip().lower()
    return ELEMENT_TO_ENGINE.get(k, "earth")


def coliseum_slot_code(fighter_id: int) -> str:
    return f"col:f{int(fighter_id):02d}"


def scaled_coliseum_atk(fighter: ColiseumFighter) -> int:
    """ATK в бою и в карточке бойца — база × COLISEUM_ENEMY_ATK_MULT."""
    return max(1, int(round(int(fighter.atk) * COLISEUM_ENEMY_ATK_MULT)))


def build_coliseum_spawn(fighter_id: int) -> FloorMonsterSpawn:
    return FloorMonsterSpawn(
        slot_code=coliseum_slot_code(fighter_id),
        template=COLISEUM_TEMPLATE,
        is_elite=False,
        is_mini_boss=False,
        is_major_boss=False,
    )


def build_coliseum_monster_bundle(fighter: ColiseumFighter) -> dict[str, Any]:
    elem = normalized_battle_element(fighter.element_tz)
    return {
        "name": fighter.name,
        "emoji": "⚔️",
        "template_key": COLISEUM_TEMPLATE_KEY,
        "hp": fighter.hp,
        "max_hp": fighter.hp,
        "atk": scaled_coliseum_atk(fighter),
        "defense": fighter.defense,
        "element": elem,
        "is_elite": False,
        "is_mini_boss": False,
        "is_major_boss": False,
        "catalog_phrases": [fighter.phrase],
        "coliseum_fighter_id": fighter.id,
    }
