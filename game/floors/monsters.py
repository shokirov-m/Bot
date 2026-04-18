"""
Шаблоны монстров по зонам и выбор врагов для этажа (UI + задел под бой).
"""

from __future__ import annotations

from dataclasses import dataclass

from game.floors import floor_data


@dataclass(frozen=True, slots=True)
class MonsterTemplate:
    """Описание монстра для отображения и будущего боя."""

    key: str
    name: str
    emoji: str
    element: str  # fire, ice, lightning, dark, light, earth
    blurb: str


def _short_monster_name(name: str, max_len: int = 15) -> str:
    """Короткая подпись для кнопок этажа и телефонов."""
    n = (name or "").strip()
    if len(n) <= max_len:
        return n
    return n[: max_len - 1] + "…"


@dataclass(frozen=True, slots=True)
class FloorMonsterSpawn:
    """Вариант на экране этажа."""

    slot_code: str  # 0-4 обычные, e — элита, m — мини-босс, b — сильный босс
    template: MonsterTemplate
    is_elite: bool
    is_mini_boss: bool
    is_major_boss: bool

    @property
    def display_name(self) -> str:
        short = _short_monster_name(self.template.name)
        if self.is_major_boss:
            return f"👑 {short}"
        if self.is_mini_boss:
            return f"⚔️ {short}"
        if self.is_elite:
            return f"⭐ {short}"
        return f"{self.template.emoji} {short}"


def zone_monster_templates(zone_key: str) -> tuple[MonsterTemplate, ...]:
    """Все шаблоны монстров зоны (для квестов NPC и т.п.)."""
    return _pool(zone_key)


def _pool(zone_key: str) -> tuple[MonsterTemplate, ...]:
    pools: dict[str, tuple[MonsterTemplate, ...]] = {
        "forest_beginnings": (
            MonsterTemplate("wolf", "Серый волк", "🐺", "earth", "Стая уверена в своей силе."),
            MonsterTemplate("spider", "Паук-ткач", "🕷️", "earth", "Ловит в нити слепых."),
            MonsterTemplate("goblin", "Гоблин", "👺", "earth", "Бросается камнями из кустов."),
            MonsterTemplate("boar", "Кабан", "🐗", "earth", "Рывок и клыки."),
            MonsterTemplate("sprite", "Лесной спрайт", "✨", "light", "Слепит вспышками."),
            MonsterTemplate("bandit", "Лесной разбойник", "🗡️", "earth", "Знает тропы и слабые места."),
            MonsterTemplate("thorn_lurker", "Терн. прыгун", "🌵", "earth", "Выскакивает из зарослей."),
        ),
        "rotten_swamps": (
            MonsterTemplate("zombie", "Болотный зомби", "🧟", "dark", "Тянет к холодной воде."),
            MonsterTemplate("slime", "Кислотный слизень", "🫧", "earth", "Разъедает броню."),
            MonsterTemplate("wyvern", "Виверна", "🐉", "fire", "Бьётся крыльями и ядом."),
            MonsterTemplate("witch", "Топи-ведьма", "🧙‍♀️", "dark", "Проклятия из тумана."),
            MonsterTemplate("leech", "Пиявка-гигант", "🪱", "earth", "Высасывает силы."),
            MonsterTemplate("gas_frog", "Газовая жаба", "🐸", "dark", "Выдыхает едкий туман."),
            MonsterTemplate("bog_mosquito", "Рой комаров", "🦟", "earth", "Жужжит и высасывает кровь."),
        ),
        "shadow_caves": (
            MonsterTemplate("bat_swarm", "Рой летучих", "🦇", "dark", "Заслоняет свет."),
            MonsterTemplate("shade", "Теневой дух", "🌑", "dark", "Проходит сквозь сталь."),
            MonsterTemplate("crawler", "Пещерный ползун", "🪨", "earth", "Цепляется к потолку."),
            MonsterTemplate("wisp", "Огонёк-обман", "🔥", "fire", "Ведёт к ловушке."),
            MonsterTemplate("echo", "Эхо-призрак", "👻", "dark", "Повторяет твои шаги."),
            MonsterTemplate("stalactite", "Живой сталактит", "🪨", "earth", "Обрушивается сверху."),
            MonsterTemplate("gloom_weaver", "Ткач мрака", "🕸️", "dark", "Плетёт нити из тени."),
        ),
        "icy_peaks": (
            MonsterTemplate("yeti", "Снежный йети", "🧌", "ice", "Оглушает ревом."),
            MonsterTemplate("golem_ice", "Ледяной голем", "🧊", "ice", "Броня из вековых льдов."),
            MonsterTemplate("frost_wisp", "Морозная искра", "❄️", "ice", "Замедляет конечности."),
            MonsterTemplate("harpy", "Ледяная гарпия", "🪶", "ice", "Когти и ветер."),
            MonsterTemplate("frost_spider", "Инейный паук", "🕸️", "ice", "Сеть хрустит от холода."),
            MonsterTemplate("ice_wolf", "Ледяной волк", "🐺", "ice", "Синеет от мороза."),
            MonsterTemplate("avalanche", "Дух лавины", "⛰️", "ice", "Срывает снежную массу."),
        ),
        "desert_oblivion": (
            MonsterTemplate("scorpion", "Ядовитый скорпион", "🦂", "earth", "Удар хвоста — яд."),
            MonsterTemplate("sand_wraith", "Песочный призрак", "🌪️", "dark", "Режет зерном времени."),
            MonsterTemplate("cobra", "Песчаная кобра", "🐍", "earth", "Плюётся жаром."),
            MonsterTemplate("golem_sand", "Песчаный страж", "🏺", "earth", "Рассыпается и собирается."),
            MonsterTemplate("mirage", "Мираж-искуситель", "🪞", "light", "Ломает ориентиры."),
            MonsterTemplate("dune_roc", "Пустынная птица", "🦅", "earth", "Клюв как кинжал."),
            MonsterTemplate("salt_lich", "Соляной лич", "🧂", "dark", "Высушивает плоть."),
        ),
        "volcanic_ruins": (
            MonsterTemplate("salamander", "Огненная саламандра", "🦎", "fire", "Оставляет след из пепла."),
            MonsterTemplate("ember_spirit", "Угольный дух", "🔥", "fire", "Вспыхивает при ударе."),
            MonsterTemplate("drake", "Лавовый дракончик", "🐲", "fire", "Крошечный, но жгучий."),
            MonsterTemplate("ash_shade", "Тень пепла", "💨", "dark", "Ослепляет сажей."),
            MonsterTemplate("magma_slug", "Магмовый слизень", "🌋", "fire", "Капает раскалённым металлом."),
            MonsterTemplate("cinder_imp", "Пепельный бес", "😈", "fire", "Швыряет угли."),
            MonsterTemplate("obsidian_hound", "Обсидиановая гончая", "🐕", "fire", "Зубы как стекло."),
        ),
        "sky_citadel": (
            MonsterTemplate("griffon", "Бешеный грифон", "🦅", "earth", "Бьётся когтями сверху."),
            MonsterTemplate("fallen", "Ангел хаоса", "😇", "light", "Крылья режут воздух."),
            MonsterTemplate("storm_elem", "Эл. бури", "⛈️", "lightning", "Бьёт цепями."),
            MonsterTemplate("sky_serpent", "Небесный змей", "🐍", "lightning", "Прячется в облаке."),
            MonsterTemplate("valkyrie", "Падшая валькирия", "⚔️", "light", "Бросает копья молний."),
            MonsterTemplate("cloud_stalker", "Охотник в облаках", "☁️", "light", "Бьёт из невидимости."),
            MonsterTemplate("thunder_wisp", "Громовая искра", "⚡", "lightning", "Скачет по металлу."),
        ),
        "chaos_abyss": (
            MonsterTemplate("demon_imp", "Бес бездны", "😈", "dark", "Насмехается и режет."),
            MonsterTemplate("chaos_spawn", "Порожд. хаоса", "🌀", "dark", "Меняет форму."),
            MonsterTemplate("void_ling", "Дух пустоты", "🕳️", "dark", "Пожирает звук."),
            MonsterTemplate("corruptor", "Искажатель", "🧬", "dark", "Ломает баланс стихий."),
            MonsterTemplate("mad_cultist", "Безумный культист", "🧿", "dark", "Призывает углы реальности."),
            MonsterTemplate("fractal_hound", "Фрактальная гончая", "🔷", "dark", "Дублируется в углах."),
            MonsterTemplate("entropy_mite", "Клещ энтропии", "🪲", "dark", "Грызёт порядок."),
        ),
        "eternity_hall": (
            MonsterTemplate("archdemon", "Архидемон", "👹", "dark", "Говорит заклинаниями боли."),
            MonsterTemplate("eternity_warden", "Страж вечности", "⚡", "light", "Щит из остановленного времени."),
            MonsterTemplate("time_phantom", "Фантом часов", "⏳", "lightning", "Ускоряет и замедляет."),
            MonsterTemplate("seraph_dark", "Серафим тьмы", "🪽", "dark", "Перья как клинки."),
            MonsterTemplate("rune_golem", "Рунный колосс", "🗿", "earth", "Каждый шаг — удар."),
            MonsterTemplate("chrono_wraith", "Призрак хроноса", "⌛", "light", "Рвет шкалу времени."),
            MonsterTemplate("seal_breaker", "Разруш. печатей", "📜", "dark", "Гасит защитные руны."),
        ),
        floor_data.ZONE_FINAL_KEY: (
            MonsterTemplate(
                "tower_warden",
                "Око башни",
                "👁️",
                "dark",
                "Три фазы. Требует легендарное оружие и три ключа.",
            ),
        ),
    }
    return pools.get(zone_key, pools["forest_beginnings"])


def _pick_indices(floor_number: int, count: int, pool_len: int) -> list[int]:
    """Детерминированный выбор индексов без random (стабильный UI)."""
    if pool_len <= 0:
        return []
    seed = floor_number * 1103515245 + 12345
    indices: list[int] = []
    used: set[int] = set()
    x = seed % (2**31)
    while len(indices) < min(count, pool_len):
        x = (x * 1664525 + 1013904223) % (2**32)
        idx = x % pool_len
        if idx not in used:
            used.add(idx)
            indices.append(idx)
    return indices


def mini_boss_for_zone(zone: floor_data.ZoneInfo, floor_number: int) -> MonsterTemplate:
    """Уникальный мини-босс по зоне."""
    table: dict[str, MonsterTemplate] = {
        "forest_beginnings": MonsterTemplate(
            "mini_alpha_wolf",
            "Алфа",
            "🐺",
            "earth",
            "Дважды крупнее обычного волка.",
        ),
        "rotten_swamps": MonsterTemplate(
            "mini_bog_queen",
            "Болотная королева",
            "👑",
            "dark",
            "Плетёт сеть из гнили.",
        ),
        "shadow_caves": MonsterTemplate(
            "mini_shadow_weaver",
            "Ткач теней",
            "🕸️",
            "dark",
            "Режет свет.",
        ),
        "icy_peaks": MonsterTemplate(
            "mini_frost_troll",
            "Морозный тролль",
            "🧌",
            "ice",
            "Восстанавливается от холода.",
        ),
        "desert_oblivion": MonsterTemplate(
            "mini_sand_titan",
            "Песчаный титан",
            "🏜️",
            "earth",
            "Удары вызывают бури.",
        ),
        "volcanic_ruins": MonsterTemplate(
            "mini_magma_lord",
            "Повелитель магмы",
            "🌋",
            "fire",
            "Расплавляет камень под ногами.",
        ),
        "sky_citadel": MonsterTemplate(
            "mini_storm_herald",
            "Глашатай гроз",
            "⛈️",
            "lightning",
            "Призывает цепные удары.",
        ),
        "chaos_abyss": MonsterTemplate(
            "mini_chaos_knight",
            "Рыцарь бездны",
            "🗡️",
            "dark",
            "Броня из сломанных миров.",
        ),
        "eternity_hall": MonsterTemplate(
            "mini_time_judge",
            "Судья времён",
            "⏳",
            "light",
            "Останавливает твой следующий ход.",
        ),
        floor_data.ZONE_FINAL_KEY: MonsterTemplate(
            "final_warden",
            "Страж Башни",
            "👁️",
            "dark",
            "Финальное испытание.",
        ),
    }
    return table.get(zone.key, table["forest_beginnings"])


def major_boss_for_zone(zone: floor_data.ZoneInfo, floor_number: int) -> MonsterTemplate:
    """Сильный босс на каждом 10-м этаже."""
    # Для этажа 100 — финальный страж
    if floor_number >= 100:
        return MonsterTemplate(
            "boss_tower_core",
            "Страж (×3)",
            "👁️",
            "dark",
            "Легендарный лут. Особое поведение ИИ.",
        )
    table: dict[str, MonsterTemplate] = {
        "forest_beginnings": MonsterTemplate(
            "boss_ancient_treant",
            "Король леса",
            "🐻",
            "earth",
            "Корни сковывают поле боя.",
        ),
        "rotten_swamps": MonsterTemplate(
            "boss_slime_king",
            "Царь слизней",
            "👑",
            "poison",
            "Трон из слизи и яда: бьёт сильно и отравляет.",
        ),
        "shadow_caves": MonsterTemplate(
            "boss_night_stalker",
            "Ночной охотник",
            "🌑",
            "dark",
            "Исчезает между ударами.",
        ),
        "icy_peaks": MonsterTemplate(
            "boss_glacier_king",
            "Король ледников",
            "🧊",
            "ice",
            "Две фазы: броня и ядро.",
        ),
        "desert_oblivion": MonsterTemplate(
            "boss_time_scarab",
            "Скарабей времени",
            "🪲",
            "lightning",
            "Перематывает твои баффы.",
        ),
        "volcanic_ruins": MonsterTemplate(
            "boss_ember_dragon",
            "Угольный дракон",
            "🐉",
            "fire",
            "Дыхание волной жара.",
        ),
        "sky_citadel": MonsterTemplate(
            "boss_sky_tyrant",
            "Небесный тиран",
            "☁️",
            "light",
            "Блокирует небо.",
        ),
        "chaos_abyss": MonsterTemplate(
            "boss_chaos_avatar",
            "Аватар хаоса",
            "🌀",
            "dark",
            "Меняет стихию каждую фазу.",
        ),
        "eternity_hall": MonsterTemplate(
            "boss_eternity_judge",
            "Судья вечности",
            "⚖️",
            "light",
            "Считает каждый твой промах.",
        ),
    }
    return table.get(zone.key, table["forest_beginnings"])


def build_spawns_for_floor(floor_number: int) -> list[FloorMonsterSpawn]:
    """
    Список целей на этаже: 6 обычных + элита (на базе первого),
    плюс мини-босс / сильный босс по правилам этажа.
    """
    # Этаж 3 — только город-хаб: боёв на карте нет (монстры, тайник, привал — убраны с экрана).
    if int(floor_number) == 3:
        return []
    if floor_number >= 100:
        zone = floor_data.ZONE_FINAL
        bb = major_boss_for_zone(zone, floor_number)
        return [
            FloorMonsterSpawn(
                slot_code="b",
                template=bb,
                is_elite=False,
                is_mini_boss=False,
                is_major_boss=True,
            ),
        ]

    zone = floor_data.get_zone_for_floor(floor_number)
    pool = _pool(zone.key)
    picks = _pick_indices(floor_number, 6, len(pool))
    spawns: list[FloorMonsterSpawn] = []

    for i, idx in enumerate(picks):
        tpl = pool[idx]
        spawns.append(
            FloorMonsterSpawn(
                slot_code=str(i),
                template=tpl,
                is_elite=False,
                is_mini_boss=False,
                is_major_boss=False,
            ),
        )

    if spawns:
        first = spawns[0].template
        spawns.append(
            FloorMonsterSpawn(
                slot_code="e",
                template=MonsterTemplate(
                    key=f"elite_{first.key}",
                    name=first.name,
                    emoji=first.emoji,
                    element=first.element,
                    blurb=first.blurb + " (элита: +50% HP и урона)",
                ),
                is_elite=True,
                is_mini_boss=False,
                is_major_boss=False,
            ),
        )

    if floor_data.is_mini_boss_floor(floor_number):
        mb = mini_boss_for_zone(zone, floor_number)
        spawns.append(
            FloorMonsterSpawn(
                slot_code="m",
                template=mb,
                is_elite=False,
                is_mini_boss=True,
                is_major_boss=False,
            ),
        )

    if floor_data.is_major_boss_floor(floor_number):
        bb = major_boss_for_zone(zone, floor_number)
        spawns.append(
            FloorMonsterSpawn(
                slot_code="b",
                template=bb,
                is_elite=False,
                is_mini_boss=False,
                is_major_boss=True,
            ),
        )

    return spawns
