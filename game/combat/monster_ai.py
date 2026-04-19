"""
ИИ монстров (ТЗ 1.5–1.6): агрессия, насмешки, скиллы по условиям, фазы боссов.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Literal

# Решение ИИ на ход монстра
MonsterAction = Literal["attack", "special", "taunt_only", "fortify"]


@dataclass(frozen=True, slots=True)
class MonsterAIProfile:
    """Поведенческий профиль по ключу шаблона монстра."""

    aggression: Literal["passive", "aggressive", "berserk"]
    # До трёх уникальных скиллов (текст в лог боя)
    skills_ru: tuple[str, ...]
    has_fortify: bool  # защитный скилл при HP < 50%


# Ключ — MonsterTemplate.key из monsters.py
AI_PROFILES: dict[str, MonsterAIProfile] = {
    "wolf": MonsterAIProfile("aggressive", ("🐺 Яростный рывок", "🦷 Укус альфы"), True),
    "spider": MonsterAIProfile("aggressive", ("🕸️ Паутина", "☠️ Укус ядом"), True),
    "goblin": MonsterAIProfile("aggressive", ("🪨 Бросок камня", "👺 Внезапный выпад"), False),
    "boar": MonsterAIProfile("berserk", ("🐗 Рывок", "💥 Таран"), False),
    "sprite": MonsterAIProfile("passive", ("✨ Ослепление", "🌟 Вспышка"), True),
    "zombie": MonsterAIProfile("passive", ("🧟 Хватание", "💀 Тлен"), True),
    "slime": MonsterAIProfile("passive", ("🫧 Брызги кислоты", "🔗 Слипание"), True),
    "wyvern": MonsterAIProfile("aggressive", ("🐉 Удар крылом", "🔥 Ядовитое дыхание"), True),
    "witch": MonsterAIProfile("aggressive", ("🧙‍♀️ Проклятие", "🌫️ Туман"), True),
    "leech": MonsterAIProfile("passive", ("🪱 Высасывание", "💧 Ослабление"), True),
    "bat_swarm": MonsterAIProfile("aggressive", ("🦇 Закрутка", "🌑 Слепота"), False),
    "shade": MonsterAIProfile("aggressive", ("🌑 Удар тени", "👁️ Взгляд бездны"), True),
    "crawler": MonsterAIProfile("berserk", ("🪨 Обвал", "🕷️ Цепляние"), True),
    "wisp": MonsterAIProfile("passive", ("🔥 Обманный огонь", "✨ Ослепление"), False),
    "echo": MonsterAIProfile("passive", ("👻 Эхо-удар", "🔊 Крик"), True),
    "yeti": MonsterAIProfile("berserk", ("🧌 Удар лапой", "❄️ Ледяной рев"), True),
    "golem_ice": MonsterAIProfile("passive", ("🧊 Ледяной кулак", "❄️ Заморозка"), True),
    "frost_wisp": MonsterAIProfile("passive", ("❄️ Иней", "🌨️ Вихрь"), False),
    "harpy": MonsterAIProfile("aggressive", ("🪶 Когти", "💨 Порыв ветра"), True),
    "frost_spider": MonsterAIProfile("aggressive", ("🕸️ Ледяная сеть", "❄️ Укус"), True),
    "scorpion": MonsterAIProfile("aggressive", ("🦂 Укол", "☠️ Яд"), True),
    "sand_wraith": MonsterAIProfile("aggressive", ("🌪️ Песчаная буря", "⏳ Искажение"), True),
    "cobra": MonsterAIProfile("passive", ("🐍 Плевок", "💤 Усыпление"), False),
    "golem_sand": MonsterAIProfile("passive", ("🏺 Обвал песка", "🪨 Удар"), True),
    "mirage": MonsterAIProfile("passive", ("🪞 Обман", "✨ Иллюзия"), True),
    "salamander": MonsterAIProfile("aggressive", ("🔥 Хвост-пламя", "🦎 Укус"), True),
    "ember_spirit": MonsterAIProfile("aggressive", ("🔥 Вспышка", "💨 Пепел"), False),
    "drake": MonsterAIProfile("berserk", ("🐲 Огненное дыхание", "🐉 Когти"), True),
    "ash_shade": MonsterAIProfile("aggressive", ("💨 Пепельная завеса", "🌑 Удар"), True),
    "magma_slug": MonsterAIProfile("passive", ("🌋 Капля лавы", "🔥 Жжение"), True),
    "griffon": MonsterAIProfile("aggressive", ("🦅 Обстрел", "🦅 Когти"), True),
    "fallen": MonsterAIProfile("berserk", ("😇 Крыло-клинок", "✨ Луч"), True),
    "storm_elem": MonsterAIProfile("aggressive", ("⛈️ Молния", "🌩️ Цепь"), True),
    "sky_serpent": MonsterAIProfile("aggressive", ("🐍 Укус", "⚡ Разряд"), True),
    "valkyrie": MonsterAIProfile("aggressive", ("⚔️ Бросок копья", "🛡️ Удар щитом"), True),
    "demon_imp": MonsterAIProfile("berserk", ("😈 Когти", "🔥 Искра"), False),
    "chaos_spawn": MonsterAIProfile("berserk", ("🌀 Хаос", "💀 Укус"), True),
    "void_ling": MonsterAIProfile("passive", ("🕳️ Пустота", "🔇 Безмолвие"), True),
    "corruptor": MonsterAIProfile("aggressive", ("🧬 Искажение", "💀 Удар"), True),
    "mad_cultist": MonsterAIProfile("aggressive", ("🧿 Проклятие", "🔮 Призыв"), True),
    "archdemon": MonsterAIProfile("berserk", ("👹 Адский удар", "🔥 Шипы"), True),
    "eternity_warden": MonsterAIProfile("passive", ("⚡ Остановка", "🛡️ Барьер"), True),
    "time_phantom": MonsterAIProfile("aggressive", ("⏳ Сдвиг", "⌛ Песок"), True),
    "seraph_dark": MonsterAIProfile("berserk", ("🪽 Перо-клинок", "🌑 Тьма"), True),
    "rune_golem": MonsterAIProfile("passive", ("🗿 Рунный удар", "⚙️ Сейсм"), True),
    "tower_warden": MonsterAIProfile("berserk", ("👁️ Суд ока", "💀 Приговор"), True),
    "boss_tower_core": MonsterAIProfile("berserk", ("👁️ Фаза разрушения", "⚡ Суд вечности"), True),
    "boss_slime_king": MonsterAIProfile("berserk", ("☠️ Волна яда", "👑 Тронный удар"), True),
}

DEFAULT_PROFILE = MonsterAIProfile("aggressive", ("💥 Мощный удар", "⚠️ Особый приём"), True)


def _normalize_template_key(template_key: str) -> str:
    k = template_key.strip()
    if k.startswith("elite_"):
        return k[7:]
    return k


def profile_for_monster(template_key: str) -> MonsterAIProfile:
    return AI_PROFILES.get(_normalize_template_key(template_key), DEFAULT_PROFILE)


def taunts_for_monster(name: str, template_key: str = "") -> list[str]:
    """Фразы по имени и по ключу шаблона."""
    low = name.lower()
    key = _normalize_template_key(template_key.lower())
    pool: list[str] = []

    if "волк" in low or key == "wolf":
        pool.extend(
            [
                "Ты пахнешь страхом!",
                "Даже детёныши смеются над тобой!",
            ],
        )
    if "лед" in low or "мороз" in low or "снег" in low or "ice" in key or "frost" in key:
        pool.extend(
            [
                "Я превращу твои кости в лёд...",
                "Твоя теплота — моя пища.",
            ],
        )
    if "дракон" in low or "огн" in low or "лав" in low or "ember" in key or "magma" in key:
        pool.extend(
            [
                "Смертный... ты осмелился?",
                "Хочешь быть моим обедом?",
            ],
        )
    if "босс" in low or "страж" in low or "око" in low or "warden" in key or "boss" in key:
        pool.extend(
            [
                "Ты слабее пыли на моём троне.",
                "Башня испытывает только избранных.",
            ],
        )
    if "слиз" in low or key == "boss_slime_king":
        pool.extend(
            [
                "Болота помнят твой шаг…",
                "Ты станешь частью трона.",
            ],
        )

    if not pool:
        pool = [
            "Слабак!",
            "Башня не для таких, как ты.",
            "Ещё один шаг к твоему концу.",
        ]
    return pool


def pick_taunt(monster_name: str, template_key: str = "") -> str:
    return random.choice(taunts_for_monster(monster_name, template_key))


def pick_provocation_taunt(monster_name: str, template_key: str = "") -> str:
    """Насмешка, когда у игрока много HP (провокация)."""
    extras = [
        "Ты слишком здоров — это меня бесит!",
        "Неужели ты думаешь, что победишь?",
        "Башня сломает твою самоуверенность.",
    ]
    return random.choice(extras + taunts_for_monster(monster_name, template_key))


def pick_rage_taunt(monster_name: str, template_key: str = "") -> str:
    """Фраза при входе монстра в «ярость» (<30% HP)."""
    rage = [
        "Хватит! Я сожгу всё вокруг!",
        "Ты разозвал зверя!",
        "Теперь ты увидишь настоящую ярость!",
    ]
    return random.choice(rage + taunts_for_monster(monster_name, template_key))


def boss_entry_line(monster_name: str, *, is_major_boss: bool, phase: int) -> str:
    """Уникальные реплики босса при входе и смене фазы."""
    if phase >= 3:
        return random.choice(
            [
                "ЯРОСТЬ! Башня отдаёт мне последние силы!",
                "Хватит! Ты увидишь конец пути!",
                "Третья фаза — ни шагу назад!",
            ],
        )
    if phase >= 2:
        return random.choice(
            [
                "Вторая фаза… Ты ещё жив? Тогда страдай дальше!",
                "Моя истинная сила пробуждается!",
                "Это была только разминка!",
            ],
        )
    if is_major_boss:
        return random.choice(
            [
                f"{monster_name}: «Ты осмелился бросить вызов хранителю этажа!»",
                "Босс: «Докажи, что достоин подниматься выше!»",
                "«Сейчас я измерю твою волю клинком!»",
            ],
        )
    return pick_taunt(monster_name)


def sync_monster_rage_visual(state: dict[str, Any]) -> None:
    """Только флаг ярости для UI (без строк в лог)."""
    m = state["monster"]
    hp, mx = int(m["hp"]), int(m["max_hp"])
    state["monster_rage"] = mx > 0 and hp / mx <= 0.30


def update_monster_mode(state: dict[str, Any]) -> list[str]:
    """
    HP < 30% — берсерк (+30% урона). Возвращает строки лога при смене режима.
    """
    logs: list[str] = []
    m = state["monster"]
    hp, mx = int(m["hp"]), int(m["max_hp"])
    if mx <= 0:
        return logs
    was_rage = bool(state.get("monster_rage"))
    sync_monster_rage_visual(state)
    if state["monster_rage"] and not was_rage:
        logs.append(
            f"💢 Ярость: АКТИВНА (+30% урон) — «{pick_rage_taunt(m['name'], str(m.get('template_key', '')))}»",
        )
    return logs


def sync_boss_phase(state: dict[str, Any]) -> list[str]:
    """
    Мини-босс / сильный босс: при переходе через 50% HP — вторая фаза (смена паттерна).
    Веха ×20 (is_milestone_boss): при <25% HP — фаза 3 «Ярость» (+50% урон в множителе).
    """
    logs: list[str] = []
    m = state["monster"]
    if not (m.get("is_mini_boss") or m.get("is_major_boss")):
        return logs
    hp, mx = int(m["hp"]), int(m["max_hp"])
    if mx <= 0:
        return logs
    pct = hp / mx
    phase = int(state.get("monster_phase", 1))
    if phase == 1 and pct <= 0.50:
        state["monster_phase"] = 2
        line = boss_entry_line(m["name"], is_major_boss=bool(m.get("is_major_boss")), phase=2)
        logs.append(f"⚡ Фаза 2: {line}")
    phase = int(state.get("monster_phase", 1))
    if m.get("is_milestone_boss") and phase == 2 and pct <= 0.25:
        state["monster_phase"] = 3
        line = boss_entry_line(m["name"], is_major_boss=bool(m.get("is_major_boss")), phase=3)
        logs.append(f"💀 <b>Фаза 3 — ЯРОСТЬ:</b> {line}")
    return logs


def monster_damage_multiplier(state: dict[str, Any]) -> float:
    mult = 1.0
    if state.get("monster_rage"):
        mult *= 1.30
    profile = profile_for_monster(str(state["monster"].get("template_key", "")))
    if profile.aggression == "berserk":
        mult *= 1.08
    ph = int(state.get("monster_phase", 1))
    if ph >= 3:
        mult *= 1.50
    elif ph >= 2:
        mult *= 1.12
    return mult


_WRATH_SKILLS: tuple[str, ...] = (
    "🩸 Клятва башни",
    "⚔️ Казнь вехи",
    "🜁 Разрыв кольца",
    "🔥 Пир последнего рубежа",
)


def pick_skill_line(state: dict[str, Any], *, special: bool) -> str:
    """Имя скилла для лога (случайный из профиля)."""
    m = state["monster"]
    if (
        special
        and int(state.get("monster_phase", 1)) >= 3
        and m.get("is_milestone_boss")
    ):
        return random.choice(_WRATH_SKILLS)
    key = str(m.get("template_key", ""))
    prof = profile_for_monster(key)
    if not prof.skills_ru:
        return special_attack_name(str(m.get("element", "earth")))
    if special:
        return prof.skills_ru[-1]
    return random.choice(prof.skills_ru)


def decide_action(state: dict[str, Any]) -> MonsterAction:
    """
    Выбор действия с учётом агрессии, HP, фазы босса и кулдауна спецудара.
    """
    m = state["monster"]
    turn = int(state.get("monster_turn", 0))
    cd = int(state.get("monster_special_cd", 0))
    key = str(m.get("template_key", ""))
    prof = profile_for_monster(key)

    hp_pct = int(m["hp"]) / max(1, int(m["max_hp"]))

    if prof.aggression == "passive" and random.random() < 0.22:
        return "taunt_only"

    if (
        prof.has_fortify
        and hp_pct < 0.50
        and random.random() < 0.28
        and int(state.get("monster_fortify_turns", 0)) == 0
    ):
        return "fortify"

    if cd > 0:
        return "attack"

    is_boss = bool(m.get("is_mini_boss") or m.get("is_major_boss"))
    phase = int(state.get("monster_phase", 1))

    if is_boss and phase >= 3 and m.get("is_milestone_boss"):
        if (turn + 1) % 2 == 1:
            return "special"
        if random.random() < 0.35 and cd == 0:
            return "special"
    elif is_boss and phase >= 2:
        if (turn + 1) % 2 == 0:
            return "special"
    else:
        if (turn + 1) % 3 == 0:
            return "special"

    if prof.aggression == "berserk" and random.random() < 0.18 and cd == 0:
        return "special"

    return "attack"


def special_attack_name(element: str) -> str:
    names = {
        "fire": "🔥 Извержение",
        "ice": "🧊 Ледяное дыхание",
        "lightning": "⚡ Удар грома",
        "dark": "💀 Высасывание",
        "light": "✨ Кара света",
        "earth": "🌿 Удар земли",
    }
    return names.get(element, "💥 Сокрушительный удар")


def opening_taunt_line(state: dict[str, Any]) -> str:
    """Первая реплика в бою."""
    m = state["monster"]
    phrases = m.get("catalog_phrases") or []
    if isinstance(phrases, list) and phrases:
        line = random.choice([str(p) for p in phrases if str(p).strip()])
        if line.strip():
            return f"💬 «{line.strip()}»"
    if m.get("is_major_boss") or m.get("is_mini_boss"):
        return f"💬 {boss_entry_line(m['name'], is_major_boss=bool(m.get('is_major_boss')), phase=1)}"
    return f"💬 «{pick_taunt(m['name'], str(m.get('template_key', '')))}»"
