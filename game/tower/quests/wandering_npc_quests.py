"""
Задания от случайных путников на этажах 1–20.

Каждый из 24 типов NPC предлагает уникальное задание.
Выбор NPC детерминирован по (character_id, floor_number) — тот же алгоритм, что в wandering_npcs.py.

Типы заданий:
  kills_any   — убить N любых монстров
  kills_elite — убить N элитных монстров
  kills_boss  — победить N боссов (мини или мажор)
  battles_win — выиграть N боёв
  earn_gold   — заработать N золота в боях

Награды включают золото, опыт и Славу (fame).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WanderingQuestDef:
    npc_index: int       # 0–11, совпадает с индексом в _POOL из wandering_npcs.py
    npc_key: str         # короткий ключ NPC
    npc_emoji: str
    npc_name: str        # полное имя NPC
    intro: str           # приветственный текст NPC
    quest_title: str     # заголовок задания
    quest_desc: str      # описание для игрока
    quest_type: str      # kills_any | kills_elite | kills_boss | battles_win | earn_gold
    target: int          # цель
    reward_gold: int
    reward_xp: int
    reward_fame: int
    reward_rune: int     # рунных камней (0 = нет)
    complete_text: str   # текст при выполнении
    special: str         # "" | "heal" — доп. эффект при получении награды


# ── Определения 24 путников ────────────────────────────────────────────────────

WANDERING_QUESTS: tuple[WanderingQuestDef, ...] = (
    # 0 — Старик с фонарём
    WanderingQuestDef(
        npc_index=0,
        npc_key="old_man",
        npc_emoji="👴",
        npc_name="Старик с фонарём",
        intro=(
            "— Сынок... мой внук убежал вглубь башни три дня назад.\n"
            "Я слишком стар, чтобы идти за ним. Но если ты очистишь путь\n"
            "от тварей — я найду дорогу домой.\n\n"
            "<i>Убей 5 монстров и вернись.</i>"
        ),
        quest_title="Найди дорогу",
        quest_desc="Убей 5 монстров в башне.",
        quest_type="kills_any",
        target=5,
        reward_gold=240,
        reward_xp=120,
        reward_fame=5,
        reward_rune=0,
        complete_text="— Благодарю тебя, странник. Вот всё, что у меня осталось.",
        special="",
    ),
    # 1 — Торговка с тележкой
    WanderingQuestDef(
        npc_index=1,
        npc_key="merchant",
        npc_emoji="🛒",
        npc_name="Торговка с тележкой",
        intro=(
            "— Эй! Не уходи! Разбойники напали на мой обоз\n"
            "и угнали половину товара. Помоги мне — разберись с элитными бандитами!\n\n"
            "<i>Победи 3 элитных монстра.</i>"
        ),
        quest_title="Защита обоза",
        quest_desc="Победи 3 элитных монстра.",
        quest_type="kills_elite",
        target=3,
        reward_gold=450,
        reward_xp=210,
        reward_fame=8,
        reward_rune=0,
        complete_text="— Вот твоя доля! Ты спас мой товар — и мою жизнь.",
        special="",
    ),
    # 2 — Следопыт из гильдии
    WanderingQuestDef(
        npc_index=2,
        npc_key="ranger",
        npc_emoji="🏹",
        npc_name="Следопыт из гильдии",
        intro=(
            "— Тихо. Я выследил вожака стаи, что терроризирует весь ярус.\n"
            "Он сильный — мини-босс или хуже. Гильдия заплатит за его голову.\n\n"
            "<i>Победи 1 мини-босса или мажор-босса.</i>"
        ),
        quest_title="Контракт гильдии",
        quest_desc="Победи 1 мини-босса или сильного босса.",
        quest_type="kills_boss",
        target=1,
        reward_gold=600,
        reward_xp=300,
        reward_fame=10,
        reward_rune=0,
        complete_text="— Чисто. Гильдия будет довольна. Держи вознаграждение.",
        special="",
    ),
    # 3 — Монах-аскет
    WanderingQuestDef(
        npc_index=3,
        npc_key="monk",
        npc_emoji="🧘",
        npc_name="Монах-аскет",
        intro=(
            "— Путник. Я чувствую скверну в этих стенах.\n"
            "Уничтожь 8 нечестивых существ — очисти путь духа.\n"
            "Медитация не может начаться, пока злоба бродит рядом.\n\n"
            "<i>Убей 8 монстров.</i>"
        ),
        quest_title="Очищение пути",
        quest_desc="Убей 8 монстров в башне.",
        quest_type="kills_any",
        target=8,
        reward_gold=300,
        reward_xp=150,
        reward_fame=6,
        reward_rune=0,
        complete_text="— Тишина... наконец-то. Прими это как знак благодарности.",
        special="",
    ),
    # 4 — Ребёнок с куклой
    WanderingQuestDef(
        npc_index=4,
        npc_key="child",
        npc_emoji="🧸",
        npc_name="Ребёнок с куклой",
        intro=(
            "— Дядя герой... мама ушла за угол три часа назад.\n"
            "Куколка сказала, что ты сможешь помочь. Прогони плохих?\n\n"
            "<i>Выиграй 5 боёв.</i>"
        ),
        quest_title="Обещание ребёнку",
        quest_desc="Выиграй 5 боёв в башне.",
        quest_type="battles_win",
        target=5,
        reward_gold=360,
        reward_xp=180,
        reward_fame=12,
        reward_rune=0,
        complete_text="— Ты вернулся! Куколка была права. Держи — это мамино.",
        special="",
    ),
    # 5 — Странствующий кузнец
    WanderingQuestDef(
        npc_index=5,
        npc_key="smith",
        npc_emoji="⚒️",
        npc_name="Странствующий кузнец",
        intro=(
            "— Хорошая сталь? Ха! В этой башне всё ржавеет.\n"
            "Мне нужен уголь, а за уголь нужны монеты.\n"
            "Заработай 250 золота — и я сделаю тебе скидку на ремонт.\n\n"
            "<i>Заработай 250 золота в боях.</i>"
        ),
        quest_title="Монеты на уголь",
        quest_desc="Заработай 250 золота в боях.",
        quest_type="earn_gold",
        target=250,
        reward_gold=270,
        reward_xp=135,
        reward_fame=7,
        reward_rune=0,
        complete_text="— Неплохо! Я починю твоё снаряжение. Держи сдачу.",
        special="",
    ),
    # 6 — Беженец с узлом
    WanderingQuestDef(
        npc_index=6,
        npc_key="refugee",
        npc_emoji="🎒",
        npc_name="Беженец с узлом",
        intro=(
            "— Стой! Не уходи... нас шесть семей, мы пытаемся выбраться.\n"
            "Прикрой наш отход. Победи в шести схватках — дай нам время.\n\n"
            "<i>Выиграй 6 боёв.</i>"
        ),
        quest_title="Прикрытие отхода",
        quest_desc="Выиграй 6 боёв в башне.",
        quest_type="battles_win",
        target=6,
        reward_gold=330,
        reward_xp=165,
        reward_fame=8,
        reward_rune=0,
        complete_text="— Мы успели. Ты спас нас всех. Это всё, что мы можем дать.",
        special="",
    ),
    # 7 — Полевой лекарь
    WanderingQuestDef(
        npc_index=7,
        npc_key="healer",
        npc_emoji="🌿",
        npc_name="Полевой лекарь",
        intro=(
            "— Мне нужны компоненты для зелья — они падают с монстров этой зоны.\n"
            "Убей 4 существа. Я заберу что нужно с туш, а тебя починю.\n\n"
            "<i>Убей 4 монстра.</i>"
        ),
        quest_title="Сбор компонентов",
        quest_desc="Убей 4 монстра в башне.",
        quest_type="kills_any",
        target=4,
        reward_gold=240,
        reward_xp=120,
        reward_fame=5,
        reward_rune=0,
        complete_text="— Вот что нужно. И возьми — я перевязал твои раны заодно.",
        special="heal",
    ),
    # 8 — Бард с лютней
    WanderingQuestDef(
        npc_index=8,
        npc_key="bard",
        npc_emoji="🎶",
        npc_name="Бард с лютней",
        intro=(
            "— О, странник! Мне нужен подвиг для новой баллады!\n"
            "Без подвига нет песни, без песни нет монет.\n"
            "Убей элитного врага — и я увековечу твоё имя!\n\n"
            "<i>Победи 1 элитного монстра.</i>"
        ),
        quest_title="Подвиг для баллады",
        quest_desc="Победи 1 элитного монстра.",
        quest_type="kills_elite",
        target=1,
        reward_gold=180,
        reward_xp=90,
        reward_fame=15,
        reward_rune=0,
        complete_text="— Великолепно! Твоё имя будет звучать во всех тавернах! Скромная монета — мне не до жиру.",
        special="",
    ),
    # 9 — Картограф-неудачник
    WanderingQuestDef(
        npc_index=9,
        npc_key="cartographer",
        npc_emoji="🗺️",
        npc_name="Картограф-неудачник",
        intro=(
            "— О нет, снова я заблудился... Помоги мне составить карту!\n"
            "Пока ты убиваешь монстров — я зарисую местность.\n"
            "Мне нужно время и... тишина.\n\n"
            "<i>Убей 6 монстров.</i>"
        ),
        quest_title="Карта местности",
        quest_desc="Убей 6 монстров в башне.",
        quest_type="kills_any",
        target=6,
        reward_gold=270,
        reward_xp=135,
        reward_fame=6,
        reward_rune=0,
        complete_text="— Готово! Карта составлена! Вот твоя часть, и извини за... кривые линии.",
        special="",
    ),
    # 10 — Охотник на тварей
    WanderingQuestDef(
        npc_index=10,
        npc_key="hunter",
        npc_emoji="🐺",
        npc_name="Охотник на тварей",
        intro=(
            "— Хе. Редкий трофей — с босса этих этажей.\n"
            "Заказчик платит хорошо. Ты явно сильнее меня сейчас.\n"
            "Убей вожака — я возьму трофей, ты возьмёшь монеты.\n\n"
            "<i>Победи 1 мини-босса или сильного босса.</i>"
        ),
        quest_title="Трофейная охота",
        quest_desc="Победи 1 мини-босса или сильного босса.",
        quest_type="kills_boss",
        target=1,
        reward_gold=540,
        reward_xp=270,
        reward_fame=12,
        reward_rune=0,
        complete_text="— Чисто. Трофей мой — монеты твои. Приятно работать с профессионалом.",
        special="",
    ),
    # 11 — Отшельник в тряпье
    WanderingQuestDef(
        npc_index=11,
        npc_key="hermit",
        npc_emoji="🌑",
        npc_name="Отшельник в тряпье",
        intro=(
            "— Башня... она дышит. Я слышу её ритм.\n"
            "Сыграй в игру судьбы — победи в десяти схватках.\n"
            "Если выживешь — получишь нечто ценное из тайника.\n\n"
            "<i>Выиграй 10 боёв.</i>"
        ),
        quest_title="Игра судьбы",
        quest_desc="Выиграй 10 боёв в башне.",
        quest_type="battles_win",
        target=10,
        reward_gold=150,
        reward_xp=75,
        reward_fame=20,
        reward_rune=1,
        complete_text="— Башня приняла тебя... Вот — рунный камень из глубин. Береги его.",
        special="",
    ),
    # 12 — Норна у узла судьбы
    WanderingQuestDef(
        npc_index=12,
        npc_key="norn",
        npc_emoji="🧵",
        npc_name="Норна у узла судьбы",
        intro=(
            "— Я вижу нить, что ведёт тебя вверх. Но у нити есть цена.\n"
            "Сделай выбор в бою: победи — и не отступи ни разу.\n\n"
            "<i>Выиграй 4 боя.</i>"
        ),
        quest_title="Узел выбора",
        quest_desc="Выиграй 4 боя в башне.",
        quest_type="battles_win",
        target=4,
        reward_gold=260,
        reward_xp=140,
        reward_fame=9,
        reward_rune=0,
        complete_text="— Нить натянулась — и не порвалась. Значит, ты действительно идёшь.",
        special="",
    ),
    # 13 — Анубисов жрец
    WanderingQuestDef(
        npc_index=13,
        npc_key="anubis",
        npc_emoji="⚖️",
        npc_name="Анубисов жрец",
        intro=(
            "— Твари Башни не умирают… они возвращаются. Мне нужна печать.\n"
            "Победи босса. Сердце будет взвешено — и отмечено.\n\n"
            "<i>Победи 1 мини-босса или сильного босса.</i>"
        ),
        quest_title="Печать взвешенного сердца",
        quest_desc="Победи 1 мини-босса или сильного босса.",
        quest_type="kills_boss",
        target=1,
        reward_gold=520,
        reward_xp=260,
        reward_fame=14,
        reward_rune=1,
        complete_text="— Вес оказался… приемлемым. Забирай печать. Не показывай её лишним глазам.",
        special="",
    ),
    # 14 — Морриган в вороньей мантии
    WanderingQuestDef(
        npc_index=14,
        npc_key="morrigan",
        npc_emoji="🪶",
        npc_name="Морриган в вороньей мантии",
        intro=(
            "— Я не предсказываю. Я фиксирую.\n"
            "Принеси мне ряд побед — не ради славы, а ради долга.\n\n"
            "<i>Выиграй 7 боёв.</i>"
        ),
        quest_title="Долг победителя",
        quest_desc="Выиграй 7 боёв в башне.",
        quest_type="battles_win",
        target=7,
        reward_gold=340,
        reward_xp=190,
        reward_fame=18,
        reward_rune=0,
        complete_text="— Достаточно. Запомни: Башня забирает то, что ты называешь «случаем».",
        special="",
    ),
    # 15 — Локи-насмешник
    WanderingQuestDef(
        npc_index=15,
        npc_key="loki",
        npc_emoji="🃏",
        npc_name="Локи-насмешник",
        intro=(
            "— Ставка простая: ты приносишь золото, а я делаю вид, что помог.\n"
            "Заработай монеты в бою. Только в бою — иначе скучно.\n\n"
            "<i>Заработай 220 золота в боях.</i>"
        ),
        quest_title="Сделка с насмешником",
        quest_desc="Заработай 220 золота в боях.",
        quest_type="earn_gold",
        target=220,
        reward_gold=280,
        reward_xp=150,
        reward_fame=10,
        reward_rune=0,
        complete_text="— Вот видишь, можешь же. А теперь забудь, что видел меня здесь.",
        special="",
    ),
    # 16 — Сфинкс у треснувшей арки
    WanderingQuestDef(
        npc_index=16,
        npc_key="sphinx",
        npc_emoji="🗿",
        npc_name="Сфинкс у треснувшей арки",
        intro=(
            "— Я задаю вопросы, но не словами.\n"
            "Покажи силу, которую Башня признаёт: элитная победа.\n\n"
            "<i>Победи 2 элитных монстра.</i>"
        ),
        quest_title="Вопрос без ответа",
        quest_desc="Победи 2 элитных монстра.",
        quest_type="kills_elite",
        target=2,
        reward_gold=520,
        reward_xp=260,
        reward_fame=14,
        reward_rune=0,
        complete_text="— Ты ответил. Не словами. Запомни это правило для верхних ярусов.",
        special="",
    ),
    # 17 — Геката на трёх путях
    WanderingQuestDef(
        npc_index=17,
        npc_key="hecate",
        npc_emoji="🕯️",
        npc_name="Геката на трёх путях",
        intro=(
            "— Три пути ведут вверх. Все три ведут в одну тень.\n"
            "Собери победы — и вернись, пока факелы ещё горят.\n\n"
            "<i>Выиграй 6 боёв.</i>"
        ),
        quest_title="Три факела",
        quest_desc="Выиграй 6 боёв в башне.",
        quest_type="battles_win",
        target=6,
        reward_gold=420,
        reward_xp=220,
        reward_fame=16,
        reward_rune=0,
        complete_text="— Факелы не погасли. Значит, ты идёшь вовремя.",
        special="",
    ),
    # 18 — Безымянный трикстер
    WanderingQuestDef(
        npc_index=18,
        npc_key="trickster",
        npc_emoji="🎭",
        npc_name="Безымянный трикстер",
        intro=(
            "— Хочешь знать секрет? Этажи можно «переписывать».\n"
            "Но сначала заработай золото честно — в бою. Иначе я не верю.\n\n"
            "<i>Заработай 400 золота в боях.</i>"
        ),
        quest_title="Чернила и монеты",
        quest_desc="Заработай 400 золота в боях.",
        quest_type="earn_gold",
        target=400,
        reward_gold=480,
        reward_xp=240,
        reward_fame=12,
        reward_rune=0,
        complete_text="— Чернила свежие. А теперь запомни: иногда карта врёт не тебе — а себе.",
        special="",
    ),
    # 19 — Сибилла из пустой ниши
    WanderingQuestDef(
        npc_index=19,
        npc_key="sibyl",
        npc_emoji="🫥",
        npc_name="Сибилла из пустой ниши",
        intro=(
            "— Дверь откроется, когда ты перестанешь считать попытки.\n"
            "Считай победы. Их должно быть много.\n\n"
            "<i>Выиграй 10 боёв.</i>"
        ),
        quest_title="Десять отметок",
        quest_desc="Выиграй 10 боёв в башне.",
        quest_type="battles_win",
        target=10,
        reward_gold=300,
        reward_xp=180,
        reward_fame=24,
        reward_rune=1,
        complete_text="— Десять отметок. Теперь ты заметен. А заметных — проверяют.",
        special="",
    ),
    # 20 — Персей со щитом-зеркалом
    WanderingQuestDef(
        npc_index=20,
        npc_key="perseus",
        npc_emoji="🛡️",
        npc_name="Персей со щитом-зеркалом",
        intro=(
            "— Не смотри чудовищу в глаза. Смотри в отражение.\n"
            "Убей босса — и я покажу, как не сломаться на вехах.\n\n"
            "<i>Победи 1 мини-босса или сильного босса.</i>"
        ),
        quest_title="Отражение",
        quest_desc="Победи 1 мини-босса или сильного босса.",
        quest_type="kills_boss",
        target=1,
        reward_gold=680,
        reward_xp=340,
        reward_fame=18,
        reward_rune=0,
        complete_text="— Видишь? Даже страх отражается. Дальше будет хуже — но ты уже знаешь приём.",
        special="",
    ),
    # 21 — Кухулин у костяных копий
    WanderingQuestDef(
        npc_index=21,
        npc_key="cuchulainn",
        npc_emoji="🗡️",
        npc_name="Кухулин у костяных копий",
        intro=(
            "— Боссов ты боишься? Отлично. Значит, ещё живой.\n"
            "Иди и докажи, что страх не управляет руками.\n\n"
            "<i>Победи 2 босса (мини/мажор).</i>"
        ),
        quest_title="Смех над страхом",
        quest_desc="Победи 2 мини-босса или сильного босса.",
        quest_type="kills_boss",
        target=2,
        reward_gold=900,
        reward_xp=420,
        reward_fame=20,
        reward_rune=1,
        complete_text="— Вот так. Теперь ты знаешь вкус настоящего этажа.",
        special="",
    ),
    # 22 — Аманита, грибная ведьма
    WanderingQuestDef(
        npc_index=22,
        npc_key="amanita",
        npc_emoji="🍄",
        npc_name="Аманита, грибная ведьма",
        intro=(
            "— Память течёт по стенам. Я собираю крошки.\n"
            "Принеси мне победы — и я подлатаю твою голову и сердце.\n\n"
            "<i>Выиграй 5 боёв.</i>"
        ),
        quest_title="Крошки памяти",
        quest_desc="Выиграй 5 боёв в башне.",
        quest_type="battles_win",
        target=5,
        reward_gold=380,
        reward_xp=200,
        reward_fame=15,
        reward_rune=0,
        complete_text="— Хорошо. Дыши. Я убрала лишние мысли… на время.",
        special="heal",
    ),
    # 23 — Смотритель трещин
    WanderingQuestDef(
        npc_index=23,
        npc_key="crack_keeper",
        npc_emoji="🧱",
        npc_name="Смотритель трещин",
        intro=(
            "— Трещины появляются перед вехами. Я слушаю, где Башня ломается.\n"
            "Принеси золото из боёв — оно звенит иначе, если добыто честно.\n\n"
            "<i>Заработай 500 золота в боях.</i>"
        ),
        quest_title="Звон трещин",
        quest_desc="Заработай 500 золота в боях.",
        quest_type="earn_gold",
        target=500,
        reward_gold=600,
        reward_xp=260,
        reward_fame=16,
        reward_rune=0,
        complete_text="— Слышишь? Трещина рядом. Не ищи её глазами — ищи событиями.",
        special="",
    ),
)

# Индекс по npc_key
_BY_KEY: dict[str, WanderingQuestDef] = {q.npc_key: q for q in WANDERING_QUESTS}
# Индекс по npc_index
_BY_IDX: dict[int, WanderingQuestDef] = {q.npc_index: q for q in WANDERING_QUESTS}


def quest_for_npc_index(npc_index: int) -> WanderingQuestDef | None:
    """Задание по индексу NPC из пула wandering_npcs._POOL."""
    return _BY_IDX.get(npc_index)


def quest_by_npc_key(npc_key: str) -> WanderingQuestDef | None:
    return _BY_KEY.get(npc_key)


def npc_index_for_floor(character_id: int, floor_number: int) -> int:
    f = int(floor_number)
    if f <= 20:
        pool_size = 16
    else:
        pool_size = 24
    return (int(character_id) + f * 31) % pool_size
