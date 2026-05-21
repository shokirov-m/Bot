"""
Уникальные залы на этажах сильного босса (×10): отдельные слоты ft_br* для каждой комнаты.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from game.enemies.floors.spawns import major_boss_for_zone, mini_boss_for_zone
from game.tower.progression import floor_data


@dataclass(frozen=True, slots=True)
class BossChamber:
    slot: str
    name_ru: str
    emoji: str
    blurb_ru: str
    wins_need: int = 3
    is_elite: bool = False
    is_guardian: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "name_ru": self.name_ru,
            "emoji": self.emoji,
            "blurb_ru": self.blurb_ru,
            "wins_need": self.wins_need,
            "is_elite": self.is_elite,
            "is_guardian": self.is_guardian,
        }


@dataclass(frozen=True, slots=True)
class BossFloorTrial:
    floor: int
    title_ru: str
    blurb_ru: str
    boss_key: str
    boss_name_ru: str
    chambers: tuple[BossChamber, ...]


def _slot(i: int) -> str:
    return f"ft_br{i:02d}"


# Уникальные маршруты к каждому сильному боссу башни
_BOSS_FLOORS: dict[int, BossFloorTrial] = {
    10: BossFloorTrial(
        10,
        "Тронный зал Древнего Дуба",
        "Три священные камеры ведут к сердцу рощи. Зачисти стражей — откроется Дуб.",
        "boss_ancient_treant",
        "Древний Дуб",
        (
            BossChamber(_slot(0), "Корни-часовые", "🌳", "Плети корней сжимают проход.", 2),
            BossChamber(_slot(1), "Зал шепчущих листьев", "🍃", "Листва скрывает охотников рощи.", 3, is_elite=True),
            BossChamber(_slot(2), "Камера семян", "🌱", "Семена оживают — добей элиту хранителя.", 3, is_guardian=True),
            BossChamber(_slot(3), "Мост к сердцевине", "🌲", "Последний рубеж перед Дубом.", 2, is_elite=True),
        ),
    ),
    20: BossFloorTrial(
        20,
        "Топи Короля Слизи",
        "Болотные купола — каждый со своим стражем. Дойди до трона жижи.",
        "boss_slime_king",
        "Король Слизи",
        (
            BossChamber(_slot(0), "Купол пиявок", "🪱", "Пиявки в тёмной воде.", 3),
            BossChamber(_slot(1), "Гнилой мост", "🌿", "Мост гниёт под ногами.", 2, is_elite=True),
            BossChamber(_slot(2), "Тюрьма пузырей", "🫧", "Пленники пузырят ядом.", 3),
            BossChamber(_slot(3), "Склеп короны", "👑", "Корона плавает в тине.", 4, is_guardian=True),
        ),
    ),
    30: BossFloorTrial(
        30,
        "Суд Ночного Сталкера",
        "Пещера-суд: залы присяжных теней, затем испытание в темноте.",
        "boss_night_stalker",
        "Ночной Сталкер",
        (
            BossChamber(_slot(0), "Зал эха", "🕳️", "Эхо выдаёт твои шаги.", 2),
            BossChamber(_slot(1), "Клетки зеркал", "🪞", "Отражения атакуют сами.", 3, is_elite=True),
            BossChamber(_slot(2), "Ниша без света", "🌑", "Свет гаснет полностью.", 3),
            BossChamber(_slot(3), "Скамья присяжных", "⚖️", "Тени судят — победи стражу.", 3, is_guardian=True),
            BossChamber(_slot(4), "Порог приговора", "🗡️", "Финальный зал перед Сталкером.", 2, is_elite=True),
        ),
    ),
    40: BossFloorTrial(
        40,
        "Ледник Ледяного Короля",
        "Замёрзшие залы дворца — разбуди стражей льда по одному.",
        "boss_glacier_king",
        "Ледяной Король",
        (
            BossChamber(_slot(0), "Вестибюль вьюг", "❄️", "Вьюга режет глаза.", 3),
            BossChamber(_slot(1), "Зал колокольного льда", "🔔", "Лёд звенит как сталь.", 3, is_elite=True),
            BossChamber(_slot(2), "Тронница пленников", "⛓️", "Пленники во льду.", 4),
            BossChamber(_slot(3), "Коридор короны", "👑", "Корона ждёт в глубине.", 3, is_guardian=True),
        ),
    ),
    50: BossFloorTrial(
        50,
        "Пески Скарабея Времени",
        "Пустынные гробницы: каждая комната — эпоха, босс — в центре часов.",
        "boss_time_scarab",
        "Скарабей Времени",
        (
            BossChamber(_slot(0), "Дюна часов", "⏳", "Песок течёт вспять.", 3),
            BossChamber(_slot(1), "Оазис-призрак", "🏜️", "Вода исчезает на глазах.", 2, is_elite=True),
            BossChamber(_slot(2), "Зал песчаных часов", "⌛", "Часы без стрелок.", 3),
            BossChamber(_slot(3), "Гробница фараона", "🪲", "Скарабей шевелится в янтаре.", 4, is_guardian=True),
        ),
    ),
    60: BossFloorTrial(
        60,
        "Кузня Пепельного Дракона",
        "Вулканические залы: жар, шлак, лава — трон дракона в конце.",
        "boss_ember_dragon",
        "Пепельный Дракон",
        (
            BossChamber(_slot(0), "Галерея шлака", "🌋", "Шлак режет сапоги.", 3),
            BossChamber(_slot(1), "Зал расплавленных цепей", "⛓️", "Цепи капают огнём.", 3, is_elite=True),
            BossChamber(_slot(2), "Котельня слуг", "🔥", "Слуги дракона не спят.", 4),
            BossChamber(_slot(3), "Мост через лаву", "🌉", "Камни трескаются.", 3, is_guardian=True),
        ),
    ),
    70: BossFloorTrial(
        70,
        "Врата Князя Кровавого Зуба",
        "Десять ярусов сходятся здесь: ритуальные залы, затем трон князя.",
        "boss_blood_prince",
        "Князь Кровавый Зуб",
        (
            BossChamber(_slot(0), "Галерея клыков", "🦇", "Статуи пьют свет.", 3),
            BossChamber(_slot(1), "Зал трёх фаз", "🩸", "Кровь пульсирует в жилах стен.", 4, is_elite=True),
            BossChamber(_slot(2), "Склеп баронов", "⚰️", "Бароны восстают.", 4),
            BossChamber(_slot(3), "Тронный коридор", "👑", "Ковёр из пепла.", 3, is_guardian=True),
            BossChamber(_slot(4), "Алтарь зуба", "🦷", "Последний ритуал перед князем.", 3, is_elite=True),
        ),
    ),
    80: BossFloorTrial(
        80,
        "Аватар Хаоса",
        "Бездна ломает реальность — комнаты без названий, но босс один.",
        "boss_chaos_avatar",
        "Аватар Хаоса",
        (
            BossChamber(_slot(0), "Платформа без низа", "🌀", "Гравитация скачет.", 3),
            BossChamber(_slot(1), "Зал ломаных зеркал", "🪞", "Отражения — враги.", 4, is_elite=True),
            BossChamber(_slot(2), "Клетка криков", "😱", "Крики не твои.", 3),
            BossChamber(_slot(3), "Узел искажений", "👁️", "Пространство скручивается.", 4, is_guardian=True),
        ),
    ),
    90: BossFloorTrial(
        90,
        "Суд Вечности",
        "Зал перед вершиной: присяга, печати, звёзды — судья ждёт.",
        "boss_eternity_judge",
        "Судья Вечности",
        (
            BossChamber(_slot(0), "Арка звёзд", "⭐", "Звёзды падают вверх.", 3),
            BossChamber(_slot(1), "Зал печатей", "📜", "Печати горят холодом.", 4, is_elite=True),
            BossChamber(_slot(2), "Мост вечного света", "🌉", "Свет слепит.", 3),
            BossChamber(_slot(3), "Скамья присяги", "⚖️", "Присяга на клинке.", 4, is_guardian=True),
            BossChamber(_slot(4), "Порог приговора", "⚡", "Судья смотрит без лица.", 3, is_elite=True),
        ),
    ),
}


def is_boss_floor(floor: int) -> bool:
    return floor_data.is_major_boss_floor(int(floor))


def get_boss_floor_trial(floor: int) -> BossFloorTrial | None:
    return _BOSS_FLOORS.get(int(floor))


def chamber_for_slot(cfg: dict[str, Any], slot: str) -> dict[str, Any] | None:
    for row in cfg.get("chambers") or []:
        if isinstance(row, dict) and str(row.get("slot")) == str(slot):
            return row
    return None


def apply_boss_chamber_trial(floor: int, base: dict[str, Any] | None = None) -> dict[str, Any]:
    """Собрать конфиг испытания «залы босса» для ×10 этажа."""
    fl = int(floor)
    defn = get_boss_floor_trial(fl)
    if defn is None:
        return dict(base or {})
    zone = floor_data.get_zone_for_floor(fl)
    tier = max(1, fl // 20)
    chambers = [c.to_dict() for c in defn.chambers]
    n = len(chambers)
    wins_default = 3 if fl <= 30 else (4 if fl <= 60 else 5)
    merged = dict(base or {})
    boss_key = str(merged.get("boss_key") or defn.boss_key)
    return {
        **merged,
        "floor": fl,
        "zone_key": zone.key,
        "trial_type": "boss_chamber",
        "trial_title_ru": defn.title_ru,
        "variant_id": f"boss_floor_{fl}",
        "hub_blurb_ru": (
            f"<b>{defn.boss_name_ru}</b> — {defn.blurb_ru} "
            f"Зачисти <b>{n}</b> уникальных зала (слоты ft_br), затем босс."
        ),
        "boss_key": boss_key,
        "chambers": chambers,
        "grounds_count": n,
        "grounds_visible_initial": n,
        "wins_per_ground": wins_default,
        "checkpoint_every_grounds": 2,
        "required_progress_pct": int(merged.get("required_progress_pct") or 88),
        "death_reset": str(merged.get("death_reset") or "phase"),
        "hardcore": bool(merged.get("hardcore", fl >= 40)),
        "stamina_per_venture": int(merged.get("stamina_per_venture") or (2 if fl > 25 else 1)),
        "daily_venture_cap": int(merged.get("daily_venture_cap") or max(4, 10 - tier)),
        "boss_retry_cooldown_min_minutes": int(
            merged.get("boss_retry_cooldown_min_minutes") or (15 if fl < 50 else 16),
        ),
        "boss_retry_cooldown_max_minutes": int(
            merged.get("boss_retry_cooldown_max_minutes") or (18 if fl < 50 else 20),
        ),
        "floor_stat_mult": float(merged.get("floor_stat_mult") or (1.0 if fl < 50 else 1.08)),
        "generated": True,
        "targets": {
            "chambers": n,
            "fights": n * wins_default + fl,
            "elites": sum(1 for c in chambers if c.get("is_elite")),
            "guardians": sum(1 for c in chambers if c.get("is_guardian")),
            "mini_bosses": 1,
        },
    }
