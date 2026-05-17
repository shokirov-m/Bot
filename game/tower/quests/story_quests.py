"""
Сюжетные NPC и квесты Этажа 1 — «Тихий Ручей».

Три постоянных NPC, каждый с одним квестом. Прогресс хранится в
character.meta_progress["story_quest_{quest_id}"] = "pending" | "active" | "done"
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from db.models.character import Character

META_SQ_PREFIX = "story_quest_"


@dataclass
class StoryQuest:
    quest_id: str
    npc_key: str
    npc_name: str
    npc_emoji: str
    npc_role: str            # короткая роль для UI
    npc_intro: str           # первая реплика при встрече
    npc_in_progress: str     # реплика, если квест взят но не выполнен
    npc_completed: str       # реплика после сдачи
    quest_title: str
    quest_desc: str          # полное описание квеста
    # Условие: тип + порог
    condition_type: str      # "kills", "material_count", "floor_reached"
    condition_key: str       # ключ в meta_progress для отслеживания
    condition_target: int
    # Награды
    reward_xp: int = 0
    reward_gold: int = 0
    reward_lore: str = ""    # лор-текст, который игрок получит при сдаче
    reward_extra: dict[str, Any] = field(default_factory=dict)


STORY_QUESTS: list[StoryQuest] = [
    StoryQuest(
        quest_id="sq_eyris_wolves",
        npc_key="eyris",
        npc_name="Страж Эйрис",
        npc_emoji="🗡️",
        npc_role="Бывший призванный, 2-е прохождение",
        npc_intro=(
            "🗡️ <b>Страж Эйрис</b>\n\n"
            "<i>Высокая женщина в потрёпанном плаще оценивает тебя холодным взглядом.</i>\n\n"
            "— Ещё один призванный. Я уже видела таких... большинство не добираются до третьего этажа.\n"
            "Но раз уж ты здесь — докажи, что не зря занимаешь место.\n\n"
            "Лесные волки вокруг Тихого Ручья становятся агрессивнее. Убей 5 из них.\n"
            "Если выживешь — расскажу кое-что о Башне."
        ),
        npc_in_progress=(
            "🗡️ <b>Страж Эйрис</b>\n\n"
            "— Ещё не закончил? Волков нужно убить 5. "
            "Ищи их на этажах 2–3."
        ),
        npc_completed=(
            "🗡️ <b>Страж Эйрис</b>\n\n"
            "— Хм. Живой и без серьёзных ран. Возможно, из тебя что-то выйдет.\n\n"
            "<i>Она вручает тебе небольшой кошелёк и говорит тихо:</i>\n\n"
            "— Слушай. Башня существует уже тысячу лет. "
            "Те, кто её создал, знали, что демоны снаружи однажды прорвутся. "
            "Нас призывают сюда не просто так — мы будущие стражи. "
            "Если доберёшься до вершины... ты поймёшь всё сам."
        ),
        quest_title="Волчья стража",
        quest_desc=(
            "Убей 5 лесных волков на этажах 2–3.\n"
            "Это первое задание Стража Эйрис."
        ),
        condition_type="kills",
        condition_key="sq_eyris_wolf_kills",
        condition_target=5,
        reward_xp=500,
        reward_gold=0,
        reward_lore=(
            "📜 <b>Лор: О цели Башни</b>\n\n"
            "Башня возведена создателями тысячу лет назад как место подготовки сильнейших. "
            "Призванные — кандидаты на роль стражей внешних границ. "
            "Те, кто покорит вершину, первыми встанут против внешних демонов."
        ),
    ),

    StoryQuest(
        quest_id="sq_owl_materials",
        npc_key="owl",
        npc_name="Алхимик Сова",
        npc_emoji="🦉",
        npc_role="Загадочный старец (скрытый создатель)",
        npc_intro=(
            "🦉 <b>Алхимик Сова</b>\n\n"
            "<i>Старый человек в мантии стоит у котла, бормоча под нос. "
            "Он поднимает взгляд — и ты чувствуешь, что он знает о тебе больше, чем должен.</i>\n\n"
            "— О, ещё один. Хорошо. У меня как раз заканчиваются ингредиенты.\n"
            "Принеси мне три материала с этажей Башни — любых. "
            "Камень, кость, кристалл... что найдёшь. "
            "Взамен дам рецепт. Он пригодится."
        ),
        npc_in_progress=(
            "🦉 <b>Алхимик Сова</b>\n\n"
            "— Ещё не принёс три материала? Они попадаются с монстров или на ферме. "
            "Не торопись — но и не медли."
        ),
        npc_completed=(
            "🦉 <b>Алхимик Сова</b>\n\n"
            "— Хорошо, хорошо. Вот рецепт.\n\n"
            "<i>Он протягивает свиток, затем добавляет тихо:</i>\n\n"
            "— Ты когда-нибудь задумывался, зачем нужна эта Башня? "
            "Не «зачем вам», а зачем она вообще существует?\n"
            "Подсказка: те, кто её строил, не ушли. "
            "Они просто... изменили форму."
        ),
        quest_title="Ингредиенты для алхимика",
        quest_desc=(
            "Принеси Алхимику Сове 3 материала.\n"
            "Материалы падают с монстров или добываются на шахте."
        ),
        condition_type="material_count",
        condition_key="sq_owl_materials_delivered",
        condition_target=3,
        reward_xp=300,
        reward_gold=500,
        reward_lore=(
            "📜 <b>Лор: Тайна создателей</b>\n\n"
            "Создатели Башни не покинули её после постройки. "
            "По слухам, они растворились в самой структуре Башни, "
            "наблюдая за каждым призванным. "
            "Некоторые из «случайных» NPC в Башне — не совсем случайные."
        ),
        reward_extra={"recipe_key": "health_potion_basic"},
    ),

    StoryQuest(
        quest_id="sq_rand_floor5",
        npc_key="rand",
        npc_name="Торговец Рэнд",
        npc_emoji="🧳",
        npc_role="Обычный призванный, как и ты",
        npc_intro=(
            "🧳 <b>Торговец Рэнд</b>\n\n"
            "<i>Молодой мужчина суетливо перебирает товары в небольшой лавке.</i>\n\n"
            "— Эй! Ты же новенький? Слушай, у меня дело.\n"
            "Я сам дальше 3-го этажа не хожу — слишком опасно. "
            "Но мне нужно знать, что творится на 5-м этаже. Там говорят, "
            "особая торговая тропа...\n"
            "Доберись до 5-го этажа и вернись. "
            "Заплачу золотом и расскажу кое-что интересное."
        ),
        npc_in_progress=(
            "🧳 <b>Торговец Рэнд</b>\n\n"
            "— Ещё не дошёл до 5-го этажа? Давай-давай, у меня уже покупатели ждут информацию!"
        ),
        npc_completed=(
            "🧳 <b>Торговец Рэнд</b>\n\n"
            "— Вернулся! И живой! Отлично.\n\n"
            "<i>Он отсчитывает монеты и наклоняется ближе:</i>\n\n"
            "— Вот что я слышал от одного старого авантюриста: "
            "на каждом пятом этаже есть «узловая точка» — место, "
            "где Башня «решает», достоин ли ты идти дальше. "
            "Боссы — это не просто монстры. "
            "Это тест Башни. Готовься к каждому серьёзно."
        ),
        quest_title="Разведка пятого этажа",
        quest_desc=(
            "Доберись до 5-го этажа Башни.\n"
            "Просто достигни его — бой необязателен."
        ),
        condition_type="floor_reached",
        condition_key="highest_floor_reached",
        condition_target=5,
        reward_xp=0,
        reward_gold=1000,
        reward_lore=(
            "📜 <b>Лор: Узловые точки Башни</b>\n\n"
            "Каждый пятый этаж — особое испытание. "
            "Башня оценивает призванных не только по силе, но и по воле. "
            "Те, кто боится боссов, как правило, остаются на нижних этажах навсегда."
        ),
    ),
    StoryQuest(
        quest_id="sq_cassandra_elite",
        npc_key="cassandra",
        npc_name="Пифия Кассандра",
        npc_emoji="🔮",
        npc_role="Оракул у закрытой двери",
        npc_intro=(
            "🔮 <b>Пифия Кассандра</b>\n\n"
            "<i>У стены стоит девушка с потемневшими глазами. Она не смотрит на тебя — "
            "она смотрит сквозь тебя, туда, где ты ещё не был.</i>\n\n"
            "— Я слышу шаги тех, кого здесь не должно быть. Башня в этот раз… торопится.\n"
            "Принеси мне знак силы: одолей элитного врага. Тогда я скажу, что видела.\n\n"
            "<i>Победи 2 элитных монстра.</i>"
        ),
        npc_in_progress=(
            "🔮 <b>Пифия Кассандра</b>\n\n"
            "— Ещё нет. Мне нужно <b>2</b> элитных победы. "
            "Только так Башня «замечает» тебя."
        ),
        npc_completed=(
            "🔮 <b>Пифия Кассандра</b>\n\n"
            "— Теперь ты пахнешь железом и дымом. Я видела это.\n\n"
            "<i>Она шепчет:</i>\n\n"
            "— На этажах выше есть двери, которых нет на карте. "
            "И у каждой двери — свой страж. "
            "Не путай «босса» и «стража». Второй выбирает тебя в ответ."
        ),
        quest_title="Знак силы",
        quest_desc="Победи 2 элитных монстра. Элитные чаще встречаются в узловых боях и у охотников.",
        condition_type="kills",
        condition_key="sq_cassandra_elite_kills",
        condition_target=2,
        reward_xp=350,
        reward_gold=350,
        reward_lore=(
            "📜 <b>Лор: Двери вне карты</b>\n\n"
            "В Башне есть проходы, не отмеченные на схемах. "
            "Их видят только те, кого Башня считает достойными. "
            "Говорят, они ведут к «слоям», где правила боёв меняются."
        ),
    ),
    StoryQuest(
        quest_id="sq_archivist_floor10",
        npc_key="archivist",
        npc_name="Архивариус Янтарь",
        npc_emoji="📚",
        npc_role="Хранитель записей",
        npc_intro=(
            "📚 <b>Архивариус Янтарь</b>\n\n"
            "<i>Человек в перчатках листает пустую книгу. "
            "Страницы белые, но ты ощущаешь тяжесть текста.</i>\n\n"
            "— Каждый, кто поднимается, оставляет след. "
            "Я собираю следы — чтобы Башня не забыла.\n"
            "Доберись до 10-го этажа. Не ради силы — ради факта.\n"
            "Вернёшься — и я дам тебе запись, которую нельзя прочитать вслух.\n\n"
            "<i>Доберись до 10-го этажа.</i>"
        ),
        npc_in_progress=(
            "📚 <b>Архивариус Янтарь</b>\n\n"
            "— Нет, ещё нет. Мне нужна отметка: <b>этаж 10</b>. "
            "Башня любит круглые числа."
        ),
        npc_completed=(
            "📚 <b>Архивариус Янтарь</b>\n\n"
            "— Запись сделана. И теперь ты в списке.\n\n"
            "<i>Он протягивает лист, который кажется тёплым.</i>\n\n"
            "— Когда в следующий раз услышишь, как стены шепчут твоё имя — "
            "не отвечай. Это не вопрос. Это проверка."
        ),
        quest_title="Отметка в книге",
        quest_desc="Достигни 10-го этажа (достаточно открыть его).",
        condition_type="floor_reached",
        condition_key="highest_floor_reached",
        condition_target=10,
        reward_xp=0,
        reward_gold=700,
        reward_lore=(
            "📜 <b>Лор: Записи Башни</b>\n\n"
            "Башня ведёт учёт. Не только побед — но и намерений. "
            "Иногда она «переписывает» тех, кто ей не нравится. "
            "Архивариусы пытаются удержать имена от исчезновения."
        ),
    ),
]

STORY_QUESTS_BY_ID: dict[str, StoryQuest] = {q.quest_id: q for q in STORY_QUESTS}
STORY_QUESTS_BY_NPC: dict[str, StoryQuest] = {q.npc_key: q for q in STORY_QUESTS}


def get_quest_state(character: Character, quest_id: str) -> str:
    """Возвращает 'pending' | 'active' | 'done'."""
    mp = dict(character.meta_progress or {})
    return str(mp.get(f"{META_SQ_PREFIX}{quest_id}", "pending"))


def set_quest_state(character: Character, quest_id: str, state: str) -> None:
    mp = dict(character.meta_progress or {})
    mp[f"{META_SQ_PREFIX}{quest_id}"] = state
    character.meta_progress = mp


def accept_quest(character: Character, quest_id: str) -> bool:
    """Принять квест. Возвращает True если принят (был pending)."""
    if get_quest_state(character, quest_id) != "pending":
        return False
    set_quest_state(character, quest_id, "active")
    return True


def check_quest_completion(character: Character, quest: StoryQuest) -> bool:
    """
    Проверить, выполнено ли условие квеста.
    Не меняет статус — это делает claim_quest_reward.
    """
    if get_quest_state(character, quest.quest_id) != "active":
        return False
    if quest.condition_type == "floor_reached":
        val = int(getattr(character, quest.condition_key, 0) or 0)
    else:
        mp = dict(character.meta_progress or {})
        val = int(mp.get(quest.condition_key, 0) or 0)
    return val >= quest.condition_target


def claim_quest_reward(character: Character, quest: StoryQuest) -> tuple[bool, str]:
    """
    Сдать квест и получить награду.
    Возвращает (success, message_html).
    """
    if get_quest_state(character, quest.quest_id) != "active":
        return False, "Квест ещё не взят."
    if not check_quest_completion(character, quest):
        mp = dict(character.meta_progress or {})
        current = int(mp.get(quest.condition_key, 0) or 0)
        return False, (
            f"Ещё не выполнено: {current}/{quest.condition_target}."
        )

    set_quest_state(character, quest.quest_id, "done")

    lines = [quest.npc_completed, ""]
    if quest.reward_xp:
        character.experience = int(character.experience) + quest.reward_xp
        lines.append(f"✨ <b>+{quest.reward_xp} XP</b>")
    if quest.reward_gold:
        character.gold = int(character.gold) + quest.reward_gold
        lines.append(f"💰 <b>+{quest.reward_gold} золота</b>")
    if quest.reward_lore:
        lines.append("")
        lines.append(quest.reward_lore)

    return True, "\n".join(lines)


def increment_kill_counter(character: Character, quest_id: str, amount: int = 1) -> None:
    """Увеличить счётчик убийств для квеста-убийств."""
    quest = STORY_QUESTS_BY_ID.get(quest_id)
    if quest is None or quest.condition_type != "kills":
        return
    if get_quest_state(character, quest_id) != "active":
        return
    mp = dict(character.meta_progress or {})
    mp[quest.condition_key] = int(mp.get(quest.condition_key, 0) or 0) + amount
    character.meta_progress = mp


def increment_material_counter(character: Character, quest_id: str, amount: int = 1) -> None:
    """Увеличить счётчик материалов для квеста-сбора."""
    quest = STORY_QUESTS_BY_ID.get(quest_id)
    if quest is None or quest.condition_type != "material_count":
        return
    if get_quest_state(character, quest_id) != "active":
        return
    mp = dict(character.meta_progress or {})
    mp[quest.condition_key] = int(mp.get(quest.condition_key, 0) or 0) + amount
    character.meta_progress = mp
