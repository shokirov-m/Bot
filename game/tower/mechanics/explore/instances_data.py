"""Данные explore по этажам."""

from __future__ import annotations

from game.enemies.floors.spawns import MonsterTemplate
from game.tower.mechanics.explore.engine import ExploreBanner, ExploreConfig

CONFIG_4 = ExploreConfig(
    floor_number=4,
    meta_key="explore_floor_4_v1",
    slot_boss="e4_boss",
    slot_encounter="e4_encounter",
    count_key="e4_count",
    target_key="e4_target",
    boss_avail_key="e4_boss_avail",
    target_min=15,
    target_max=20,
    monster_templates=(
        MonsterTemplate("timber_wolf", "Теневой Волк", "🐺", "dark", "Стая держит периметр у Тихого Ручья."),
        MonsterTemplate("orc", "Лесной Огр", "👹", "earth", "Грубая сила и тяжёлая дубина — хозяин просеки."),
        MonsterTemplate("spider", "Ядовитый Споровик", "🕷️", "earth", "Плетёт смертоносные сети между корнями вековых дубов."),
        MonsterTemplate("goblin", "Гоблин-Следопыт", "👺", "earth", "Шустрый мародёр: слышит шаг за версту."),
        MonsterTemplate("boar", "Дикий Вепрь", "🐗", "earth", "Разъярённый зверь мчится напролом, не сворачивая."),
        MonsterTemplate("sprite", "Дриада-Охотница", "✨", "earth", "Стрела из чащи — прежде, чем ты увидишь стрелка."),
        MonsterTemplate("bandit", "Ветвевик", "🗡️", "earth", "Живые ветви хлещут, как кнуты; ловушки прячутся в листве."),
        MonsterTemplate("ent", "Энт-Воитель", "🌵", "earth", "Кора — доспех; корни — стены. Не пройти мимо стража рощи."),
    ),
    boss_template=MonsterTemplate(
        "e4_forest_warden",
        "Леший-Страж",
        "🌳",
        "earth",
        "Древний хозяин рощи пробудился — его гнев это сам лес.",
    ),
    event_types=("monster", "gold", "merchant", "mystical", "rare_item", "trap", "ancient_inscription"),
    event_weights=(0.60, 0.11, 0.07, 0.07, 0.03, 0.07, 0.05),
    elite_chance=0.15,
    banner=ExploreBanner(
        boss_done="🌳 <b>Лес исследован!</b> Леший-Страж повержен — путь на 5-й этаж открыт.",
        title_fmt="🔍 <b>Исследование леса</b> [{bar}] {pct}%{boss_hint}\nПопыток: {count}/{target}",
        boss_hint=" → <b>Леший пробудился!</b>",
        filled_tile="🟩",
    ),
    all_slots_attr="EXPLORE_4_ALL_SLOTS",
)

CONFIG_8 = ExploreConfig(
    floor_number=8,
    meta_key="explore_floor_v1",
    slot_boss="exp_boss",
    slot_encounter="exp_encounter",
    count_key="explore_count",
    target_key="explore_target",
    boss_avail_key="boss_available",
    target_min=30,
    target_max=35,
    monster_templates=(
        MonsterTemplate("bat_swarm", "Теневая Гончая", "🦇", "dark", "Стая теней рвёт воздух когтями из темноты."),
        MonsterTemplate("shade", "Теневой Ассасин", "🌑", "dark", "Удар из ниоткуда; клинок холоднее пещерного воздуха."),
        MonsterTemplate("crawler", "Червь-Бурильщик", "🪨", "earth", "Пробивает камень и кость одним броском."),
        MonsterTemplate("stalactite", "Каменный Горгул", "🪨", "earth", "Замирает на своде — и обрушивается вниз."),
        MonsterTemplate("echo", "Скелет-Воин", "💀", "dark", "Кости стучат в такт; меч помнит старые войны."),
        MonsterTemplate("gloom_weaver", "Тёмная Жрица", "🕸️", "dark", "Нити тьмы сшивают воздух в кокон."),
        MonsterTemplate("wisp", "Мрачный Жрец", "🔥", "fire", "Шёпот заклинаний гасит факелы один за другим."),
        MonsterTemplate("goblin", "Грибной Голем", "🍄", "earth", "Споры и мох слипаются в медленного стража."),
    ),
    boss_template=MonsterTemplate(
        "boss_cave_guardian",
        "Глубинный Голем",
        "🗿",
        "earth",
        "Каменный исполин запечатал выход — пока не падёт сам.",
    ),
    event_types=("monster", "gold", "merchant", "mystical", "rare_item", "trap", "ancient_inscription"),
    event_weights=(0.60, 0.11, 0.07, 0.07, 0.03, 0.07, 0.05),
    elite_chance=0.15,
    banner=ExploreBanner(
        boss_done="🗿 <b>Исследование завершено!</b> Глубинный Голем разбит — проход открыт.",
        title_fmt="🔍 <b>Исследование пещеры</b> [{bar}] {pct}%{boss_hint}\nПопыток: {count}/{target}",
        boss_hint=" → <b>Голем пробудился!</b>",
    ),
    all_slots_attr="EXPLORE_ALL_SLOTS",
)

CONFIG_22 = ExploreConfig(
    floor_number=22,
    meta_key="explore_floor_22_v1",
    slot_boss="e22_boss",
    slot_encounter="e22_encounter",
    count_key="e22_count",
    target_key="e22_target",
    boss_avail_key="e22_boss_avail",
    target_min=20,
    target_max=30,
    monster_templates=(
        MonsterTemplate("bat_swarm", "Теневая Гончая", "🦇", "dark", "Стая теней рвёт воздух когтями из глубин."),
        MonsterTemplate("shade", "Теневой Ассасин", "🌑", "dark", "Удар из ниоткуда; клинок холоднее пещерного воздуха."),
        MonsterTemplate("crawler", "Червь-Бурильщик", "🪨", "earth", "Пробивает камень и кость одним броском."),
        MonsterTemplate("wisp", "Мрачный Жрец", "🔥", "fire", "Шёпот заклинаний гасит факелы один за другим."),
        MonsterTemplate("echo", "Скелет-Воин", "👻", "dark", "Кости стучат в такт; меч помнит старые войны."),
        MonsterTemplate("stalactite", "Каменный Горгул", "🪨", "earth", "Замирает на своде — и обрушивается вниз."),
        MonsterTemplate("gloom_weaver", "Тёмная Жрица", "🕸️", "dark", "Нити тьмы сшивают воздух в кокон."),
    ),
    boss_template=MonsterTemplate(
        "boss_night_stalker",
        "Король Пауков",
        "🕸️",
        "dark",
        "Повелитель глубин; яд старше памяти пещер. Его сеть на весь зал.",
    ),
    event_types=(
        "monster",
        "gold",
        "crystal",
        "trap",
        "mystical",
        "ancient_inscription",
        "rare_item",
    ),
    event_weights=(0.58, 0.10, 0.08, 0.07, 0.06, 0.06, 0.05),
    elite_chance=0.20,
    banner=ExploreBanner(
        boss_done="🕸️ <b>Пещера исследована!</b> Король Пауков повержен — путь на 23-й этаж открыт.",
        title_fmt="🕯️ <b>Исследование пещеры</b> [{bar}] {pct}%{boss_hint}\nПопыток: {count}/{target}",
        boss_hint=" → <b>Король Пауков пробудился!</b>",
        filled_tile="🟣",
    ),
    all_slots_attr="EXPLORE_22_ALL_SLOTS",
)
