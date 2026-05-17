"""Данные room-clear по этажам (автоген: devtools/gen_room_clear_instances.py)."""

from __future__ import annotations

from game.enemies.floors.spawns import MonsterTemplate
from game.tower.mechanics.room_clear.engine import RoomClearBanner, RoomClearConfig

CONFIG_5 = RoomClearConfig(
    floor_number=5,
    meta_key='room_clear_v1',
    slot_boss='rc_boss',
    button_prefix='rc_r',
    room_groups=(('rc_r0_m0', 'rc_r0_m1'), ('rc_r1_m0', 'rc_r1_m1', 'rc_r1_m2'), ('rc_r2_m0', 'rc_r2_m1'), ('rc_r3_m0',), ('rc_r4_m0', 'rc_r4_m1')),
    room_templates=(
    (
        MonsterTemplate('goblin', 'Гоблин-Следопыт', '👺', 'earth', 'Шустрый мародёр: слышит шаг за версту.'),
        MonsterTemplate('spider', 'Ядовитый Споровик', '🕷️', 'earth', 'Плетёт смертоносные сети между корнями вековых дубов.'),
    ),
    (
        MonsterTemplate('timber_wolf', 'Теневой Волк', '🐺', 'dark', 'Стая держит периметр; глаза светятся из-под крон.'),
        MonsterTemplate('timber_wolf', 'Теневой Волк', '🐺', 'dark', 'Вожак стаи — крупнее и злее сородичей.'),
        MonsterTemplate('sprite', 'Дриада-Охотница', '🏹', 'earth', 'Стрела из чащи — прежде, чем ты увидишь стрелка.'),
    ),
    (
        MonsterTemplate('ent', 'Энт-Воитель', '🌵', 'earth', 'Кора — доспех; корни — стены.'),
        MonsterTemplate('bandit', 'Ветвевик', '🌿', 'earth', 'Живые ветви хлещут, как кнуты.'),
    ),
    (
        MonsterTemplate('orc', 'Лесной Огр', '👹', 'earth', 'Два огря нападают разом — вожак с дубиной и его телохранитель.'),
    ),
    (
        MonsterTemplate('ent', 'Энт-Воитель', '🛡️', 'earth', 'Последний страж рощи перед Древним Трентом.'),
        MonsterTemplate('boar', 'Дикий Вепрь', '⚔️', 'earth', 'Разъярённый зверь не отступит.'),
    ),
),
    boss_template=MonsterTemplate('boss_ancient_treant', 'Древний Трент', '🌳', 'earth', 'Вековое дерево закрыло ворота башни корнями.'),
    banner=RoomClearBanner(boss_done='🌳 <b>Сценарий завершён!</b> Древний Трент пал — ворота открыты.', title_fmt='🗺️ <b>Зачистка комнат</b> [{room_bar}] {cleared}/{total} комнат{hint}\n{monster_line}', hint_boss=' → <b>открылся Трент!</b>'),
    duo_room_index=3,
    all_slots_attr='ROOM_CLEAR_ALL_SLOTS',
)

CONFIG_10 = RoomClearConfig(
    floor_number=10,
    meta_key='room_clear_10_v1',
    slot_boss='r10_boss',
    button_prefix='r10_r',
    room_groups=(('r10_r0_m0', 'r10_r0_m1'), ('r10_r1_m0', 'r10_r1_m1', 'r10_r1_m2'), ('r10_r2_m0', 'r10_r2_m1'), ('r10_r3_m0',), ('r10_r4_m0', 'r10_r4_m1')),
    room_templates=(
    (
        MonsterTemplate('r10_r0_zombie', 'Склепный мертвец', '🧟', 'dark', 'Поднялся из забытой могилы.'),
        MonsterTemplate('r10_r0_wraith', 'Призрак склепа', '👻', 'dark', 'Дух, прикованный к старому гробу.'),
    ),
    (
        MonsterTemplate('r10_r1_bat', 'Тёмная летучая мышь', '🦇', 'dark', 'Стремительно пикирует из тени.'),
        MonsterTemplate('r10_r1_imp', 'Бесёнок-разведчик', '😈', 'dark', 'Мелкий демон с острыми когтями.'),
        MonsterTemplate('r10_r1_shadow', 'Живая тень', '🌑', 'dark', 'Тень, отделившаяся от стены.'),
    ),
    (
        MonsterTemplate('r10_r2_golem', 'Кислотный голем', '🧪', 'dark', 'Создан из отравленной слизи.'),
        MonsterTemplate('r10_r2_lich', 'Недо-лич', '💀', 'dark', 'Некромант, не завершивший ритуал бессмертия.'),
    ),
    (
        MonsterTemplate('r10_r3_twin_demons', 'Братья-демоны', '👹', 'dark', 'Два старших демона атакуют слаженно — огонь и лёд разом.'),
    ),
    (
        MonsterTemplate('r10_r4_dark_knight', 'Рыцарь Тьмы', '🗡️', 'dark', 'Закованный в чёрные доспехи телохранитель.'),
        MonsterTemplate('r10_r4_herald', 'Глашатай Мрака', '🔱', 'dark', 'Служитель Лорда, призывающий тёмную энергию.'),
    ),
),
    boss_template=MonsterTemplate('boss_dark_lord_10', 'Лорд Тьмы', '👑', 'dark', 'Повелитель катакомб восседает на троне из теней. Его власть питается страхом живых.'),
    banner=RoomClearBanner(boss_done='👑 <b>Катакомбы зачищены!</b> Лорд Тьмы пал — путь на 11-й этаж открыт.', title_fmt='💀 <b>Тёмные Катакомбы</b> [{room_bar}] {cleared}/{total} комнат{hint}\n{monster_line}', hint_boss=' → <b>Лорд пробудился!</b>', filled_tile='🟥'),
    duo_room_index=3,
    all_slots_attr='ROOM_CLEAR_10_ALL_SLOTS',
)

CONFIG_24 = RoomClearConfig(
    floor_number=24,
    meta_key='room_clear_24_v1',
    slot_boss='r24_boss',
    button_prefix='r24_r',
    room_groups=(('r24_r0_m0', 'r24_r0_m1'), ('r24_r1_m0', 'r24_r1_m1', 'r24_r1_m2'), ('r24_r2_m0', 'r24_r2_m1'), ('r24_r3_m0',), ('r24_r4_m0', 'r24_r4_m1')),
    room_templates=(
    (
        MonsterTemplate('bat_swarm', 'Теневая Гончая', '🦇', 'dark', 'Стая теней рвёт воздух когтями из темноты.'),
        MonsterTemplate('crawler', 'Червь-Бурильщик', '🪨', 'earth', 'Пробивает камень и кость одним броском.'),
    ),
    (
        MonsterTemplate('shade', 'Теневой Ассасин', '🌑', 'dark', 'Удар из ниоткуда; клинок холоднее пещерного воздуха.'),
        MonsterTemplate('wisp', 'Мрачный Жрец', '🔥', 'fire', 'Шёпот заклинаний гасит факелы один за другим.'),
        MonsterTemplate('echo', 'Скелет-Воин', '💀', 'dark', 'Кости стучат в такт; меч помнит старые войны.'),
    ),
    (
        MonsterTemplate('stalactite', 'Каменный Горгул', '🪨', 'earth', 'Замирает на своде — и обрушивается вниз.'),
        MonsterTemplate('gloom_weaver', 'Тёмная Жрица', '🕸️', 'dark', 'Нити тьмы сшивают воздух в кокон.'),
    ),
    (
        MonsterTemplate('r24_r3_harpy_lord', 'Повелитель гарпий', '🦅', 'dark', 'Крылатый демон управляет всей стаей пещерных гарпий. Его крик разрушает камень.'),
    ),
    (
        MonsterTemplate('r24_r4_dark_acolyte', 'Тёмный жрец', '🔱', 'dark', 'Служитель культа тьмы, проводящий ритуал.'),
        MonsterTemplate('r24_r4_shadow_beast', 'Теневой зверь', '🐺', 'dark', 'Призванный из тьмы страж алтаря.'),
    ),
),
    boss_template=MonsterTemplate('boss_night_stalker', 'Король Пауков', '🕸️', 'dark', 'Повелитель глубин; яд старше памяти пещер. Его сеть на весь зал.'),
    banner=RoomClearBanner(boss_done='🌑 <b>Пещера зачищена!</b> Король Пауков повержен — путь на 25-й этаж открыт.', title_fmt='🕯️ <b>Пещеры Теней</b> [{room_bar}] {cleared}/{total} комнат{hint}\n{monster_line}', hint_boss=' → <b>Король Пауков пробудился!</b>', filled_tile='🟣'),
    duo_room_index=3,
    all_slots_attr='ROOM_CLEAR_24_ALL_SLOTS',
)

CONFIG_26 = RoomClearConfig(
    floor_number=26,
    meta_key='room_clear_26_v1',
    slot_boss='r26_boss',
    button_prefix='r26_r',
    room_groups=(('r26_r0_m0', 'r26_r0_m1'), ('r26_r1_m0', 'r26_r1_m1', 'r26_r1_m2'), ('r26_r2_m0', 'r26_r2_m1'), ('r26_r3_m0',), ('r26_r4_m0', 'r26_r4_m1')),
    room_templates=(
    (
        MonsterTemplate('r26_r0_wraith', 'Шепчущий призрак', '👻', 'dark', 'Виток тьмы у входа в зал.'),
        MonsterTemplate('r26_r0_sentinel', 'Сомневающийся страж', '🗿', 'earth', 'Каменная статуя ожила, чтобы задать вопрос без слов.'),
    ),
    (
        MonsterTemplate('r26_r1_gloom', 'Порождение мрака', '🌑', 'dark', 'Сгусток нерешительности.'),
        MonsterTemplate('r26_r1_mirror', 'Двойник в зеркале', '🪞', 'dark', 'Отражение бьёт так же больно, как оригинал.'),
        MonsterTemplate('r26_r1_moth', 'Мотылёк забвения', '🦋', 'dark', 'Крылья осыпают пылью, от которой клонит ко сну.'),
    ),
    (
        MonsterTemplate('r26_r2_chain', 'Кандалы живые', '⛓️', 'earth', 'Металл тянется к лодыжкам.'),
        MonsterTemplate('r26_r2_judge', 'Судья без лица', '⚖️', 'dark', 'Вынесет приговор, пока ты думаешь.'),
    ),
    (
        MonsterTemplate('r26_r3_doubt_lord', 'Владыка сомнений', '😶\u200d🌫️', 'dark', 'Каждый его удар — вопрос: «А стоило ли идти сюда?»'),
    ),
    (
        MonsterTemplate('r26_r4_usher', 'Проводник теней', '🕯️', 'dark', 'Ведёт к проходу, откуда не возвращаются прежними.'),
        MonsterTemplate('r26_r4_broker', 'Брокер страха', '💀', 'dark', 'Торгует чужими кошмарами.'),
    ),
),
    boss_template=MonsterTemplate('boss_shadow_gatekeeper_26', 'Привратник Чёрного Рынка', '🗝️', 'dark', 'Хранитель тайного прохода. Пока он стоит — нет ни рынка, ни наёмников. Падёт — зал опустеет навсегда.'),
    banner=RoomClearBanner(boss_done='🗝️ <b>Зал сомнений пуст.</b> Привратник пал — монстры больше не вернутся. Открыт <b>Тёмный проход</b> к рынку «Тени Башни». Поднимись на <b>27</b> этаж, когда будешь готов.', title_fmt='🗝️ <b>Зал сомнений</b> [{room_bar}] {cleared}/{total} залов{hint}\n{monster_line}', hint_boss=' → <b>Привратник ждёт!</b>', monster_subhint='<i>(последовательные бои в каждом зале)</i>', filled_tile='⬛'),
    duo_room_index=3,
    all_slots_attr='ROOM_CLEAR_26_ALL_SLOTS',
)

CONFIG_30 = RoomClearConfig(
    floor_number=30,
    meta_key='room_clear_30_v1',
    slot_boss='r30_boss',
    button_prefix='r30_r',
    room_groups=(('r30_r0_m0', 'r30_r0_m1'), ('r30_r1_m0', 'r30_r1_m1', 'r30_r1_m2'), ('r30_r2_m0', 'r30_r2_m1'), ('r30_r3_m0',), ('r30_r4_m0', 'r30_r4_m1')),
    room_templates=(
    (
        MonsterTemplate('void_ling', 'Осколок Бездны', '🕳️', 'dark', 'Края тела «съедают» свет факела.'),
        MonsterTemplate('crawler', 'Пещерный Ползун', '🪨', 'earth', 'Чует шаги и ползёт навстречу.'),
    ),
    (
        MonsterTemplate('shade', 'Теневой Ассасин', '🌑', 'dark', 'Из стены срывается плотная тьма.'),
        MonsterTemplate('wisp', 'Мрачный Фонарь', '✨', 'dark', 'Заманивает в развилку, где тише.'),
        MonsterTemplate('entropy_mite', 'Жук Пустоты', '🪲', 'dark', 'Из трещин сочится холодная тьма.'),
    ),
    (
        MonsterTemplate('gloom_weaver', 'Ткач Мрака', '🕸️', 'dark', 'Натянул нити между сталагмитами.'),
        MonsterTemplate('corruptor', 'Исказитель Плоти', '☠️', 'dark', 'Пульсирует чужой энергией.'),
    ),
    (
        MonsterTemplate('mini_shadow_weaver', 'Ткач Теней', '🌑', 'dark', 'Хранитель границы — без его падения дальше не пройти.'),
    ),
    (
        MonsterTemplate('seal_breaker', 'Разрушитель Печатей', '🔏', 'dark', 'Готовит проход к сердцу тьмы.'),
        MonsterTemplate('obsidian_hound', 'Обсидиановая Гончая', '🐕\u200d🦺', 'dark', 'Зубы из чёрного стекла.'),
    ),
),
    boss_template=MonsterTemplate('boss_night_stalker', 'Ночной Охотник', '🌑', 'dark', 'Исчезает между ударами — ударь, пока виден.'),
    banner=RoomClearBanner(boss_done='🌑 <b>Глубины зачищены!</b> Ночной охотник повержен — путь на 31-й этаж открыт.', title_fmt='🕯️ <b>Тёмный периметр (30)</b> [{room_bar}] {cleared}/{total} залов{hint}\n{monster_line}', hint_boss=' → <b>Ночной охотник ждёт!</b>', monster_line_fmt='Врагов: {mon}/{mon_total} {subhint}', filled_tile='🟣'),
    duo_room_index=3,
    all_slots_attr='ROOM_CLEAR_30_ALL_SLOTS',
)

CONFIG_40 = RoomClearConfig(
    floor_number=40,
    meta_key='room_clear_40_v1',
    slot_boss='r40_boss',
    button_prefix='r40_r',
    room_groups=(('r40_r0_m0', 'r40_r0_m1'), ('r40_r1_m0', 'r40_r1_m1', 'r40_r1_m2'), ('r40_r2_m0', 'r40_r2_m1'), ('r40_r3_m0',), ('r40_r4_m0', 'r40_r4_m1')),
    room_templates=(
    (
        MonsterTemplate('ice_wolf', 'Морозный Волк', '🐺', 'ice', 'Стая на льду; дыхание облаками пара.'),
        MonsterTemplate('frost_wisp', 'Морозный огонёк', '✨', 'ice', 'Кружит, оставляя инеистый след.'),
    ),
    (
        MonsterTemplate('frost_spider', 'Паук стужи', '🕷️', 'ice', 'Паутина звенит, как тонкое стекло.'),
        MonsterTemplate('ice_elemental', 'Элементаль льда', '🧊', 'ice', 'Глыбы сходятся в человеческий силуэт.'),
        MonsterTemplate('golem_ice', 'Снежный голем', '⛄', 'ice', 'Встаёт из сугроба, осыпаясь хлопьями.'),
    ),
    (
        MonsterTemplate('harpy', 'Гарпия перевала', '🦅', 'ice', 'Крылья бьют снегом в лицо.'),
        MonsterTemplate('yeti', 'Йети склона', '❄️', 'ice', 'Тяжёлые шаги сотрясают наст.'),
    ),
    (
        MonsterTemplate('mini_frost_troll', 'Морозный тролль', '🧌', 'ice', 'Страж ущелья — пока он стоит, ветер режет сильнее.'),
    ),
    (
        MonsterTemplate('avalanche', 'Лавина-живое', '⛰️', 'ice', 'Сходит грудой снежной пыли.'),
        MonsterTemplate('fractal_hound', 'Кристальная гончая', '💎', 'ice', 'Шкура как ломаное зеркало.'),
    ),
),
    boss_template=MonsterTemplate('boss_glacier_king', 'Король ледников', '🧊', 'ice', 'Две фазы: броня и ядро.'),
    banner=RoomClearBanner(boss_done='❄️ <b>Вершина взята!</b> Король ледников повержен — путь на 41-й этаж открыт.', title_fmt='🌨️ <b>Ледяной цитадельный пояс (40)</b> [{room_bar}] {cleared}/{total} залов{hint}\n{monster_line}', hint_boss=' → <b>Король ледников ждёт!</b>', monster_line_fmt='Врагов: {mon}/{mon_total} {subhint}', monster_subhint='<i>(в каждом зале — последовательные бои)</i>', filled_tile='🧊'),
    duo_room_index=3,
    all_slots_attr='ROOM_CLEAR_40_ALL_SLOTS',
)
