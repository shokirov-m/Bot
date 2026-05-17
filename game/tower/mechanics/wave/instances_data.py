"""Данные wave по этажам."""

from __future__ import annotations

from game.enemies.floors.spawns import MonsterTemplate
from game.tower.mechanics.wave.engine import WaveBanner, WaveConfig

CONFIG_10 = WaveConfig(
    floor_number=10,
    meta_key="wave_floor_v1",
    wave_slots=("wv_w1", "wv_w2", "wv_w3"),
    slot_boss="wv_boss",
    wave_templates=(
        MonsterTemplate(
            "wv_vanguard",
            "Авангард орды",
            "⚔️",
            "dark",
            "Первая волна — стремительные разведчики тёмной орды.",
        ),
        MonsterTemplate(
            "wv_berserker",
            "Берсерки орды",
            "🗡️",
            "dark",
            "Вторая волна — яростные воины в закопчённых доспехах.",
        ),
        MonsterTemplate(
            "wv_warlock",
            "Чернокнижник орды",
            "💀",
            "dark",
            "Третья волна — колдун, усилившийся кровью павших.",
        ),
    ),
    boss_template=MonsterTemplate(
        "boss_ancient_treant_wv",
        "Древний Трент",
        "🌲",
        "earth",
        "Три волны орды разбудили вековое дерево — оно жаждет мести.",
    ),
    banner=WaveBanner(
        boss_done="🌊 <b>Орда отбита!</b> Древний Трент повержен — путь на 11-й этаж открыт.",
        all_waves_done=(
            "🌊 <b>Все волны отбиты!</b> Пробудился <b>Древний Трент</b>.\n"
            "<i>Победи его, чтобы открыть путь наверх.</i>"
        ),
        title_fmt="🌊 <b>Волна вторжения</b> [{bar}] {cleared}/{total}\n{hint}",
        next_hint="<i>Следующая волна уже рвётся вперёд!</i>",
    ),
    all_slots_attr="WAVE_FLOOR_ALL_SLOTS",
    all_spawns_attr="all_wave_floor_spawns",
    format_banner_attr="format_wave_floor_banner_html",
)

CONFIG_27 = WaveConfig(
    floor_number=27,
    meta_key="wave_floor_27_v1",
    wave_slots=("wv27_w1", "wv27_w2", "wv27_w3"),
    slot_boss="wv27_boss",
    wave_templates=(
        MonsterTemplate(
            "wv27_shadow_scouts",
            "Теневые разведчики",
            "🌑",
            "dark",
            "Первая волна — быстрые призраки, выскальзывающие из стен.",
        ),
        MonsterTemplate(
            "wv27_dark_hunters",
            "Охотники тьмы",
            "🦇",
            "dark",
            "Вторая волна — стая тёмных охотников, ведомых инстинктом крови.",
        ),
        MonsterTemplate(
            "wv27_void_wraith",
            "Тёмная Жрица",
            "🕸️",
            "dark",
            "Третья волна — нити тьмы сшивают воздух в кокон.",
        ),
    ),
    boss_template=MonsterTemplate(
        "boss_night_stalker_27",
        "Ночной Охотник",
        "🌑",
        "dark",
        "Повелитель теней выходит из глубин. Три волны — лишь его свита. "
        "Он сам — воплощение пещерного мрака.",
    ),
    banner=WaveBanner(
        boss_done="🌑 <b>Волны теней отбиты!</b> Ночной Охотник повержен — путь на 28-й этаж открыт.",
        all_waves_done=(
            "🌑 <b>Все волны отбиты!</b> Из глубин появился <b>Ночной Охотник</b>.\n"
            "<i>Победи его, чтобы открыть путь наверх.</i>"
        ),
        title_fmt="🌑 <b>Волна теней</b> [{bar}] {cleared}/{total}\n{hint}",
        next_hint="<i>Следующая волна выходит из темноты!</i>",
        filled_tile="🟣",
    ),
    all_slots_attr="WAVE_FLOOR_27_ALL_SLOTS",
    all_spawns_attr="all_wave_floor_27_spawns",
    format_banner_attr="format_wave_floor_27_banner_html",
)
