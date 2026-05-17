from __future__ import annotations

"""
Уникальные способности монстров — применяются автоматически в engine.monster_turn
на основе template_key монстра.

Способности:
  venom_chance      — яд при ударе (шанс)
  bleed_chance      — кровотечение при ударе
  burn_chance       — ожог при ударе
  drain_pct         — жизнепоглощение: монстр восстанавливает % от нанесённого урона
  pierce_pct        — пробивает % брони игрока
  stun_chance       — оглушение: следующее действие игрока пропущено
  regen_threshold   — регенерация при HP < порога (один раз за бой)
  regen_pct         — сколько % макс. HP восстанавливается
  shield_period     — каждые N ходов монстра поднимает щит (блокирует один удар игрока)
  chaos_strike      — случайный статус при каждой атаке
  double_turn_chance— шанс атаковать дважды подряд
  rune_absorb_pct   — поглощает % входящего урона от игрока (rune_golem)
  undying           — один раз за бой выживает при смертельном ударе
  undying_regen_pct — % HP при воскрешении
  breath_period     — каждые N ходов удваивает свой урон (огненное дыхание)
  curse_chance      — проклятие: снижает урон игрока на 20% на N ходов
  curse_turns
  freeze_stack      — атаки накладывают «Озноб». 3 стака = оглушение на 1 ход
  shatter_death     — при смерти наносит урон игроку (базируется на броне монстра)
"""

# Глобальный множитель шанса оглушения от монстров.
MONSTER_STUN_CHANCE_MULT = 0.48

import random
from typing import Any

from game.combat import effects

# ── Таблица способностей ──────────────────────────────────────────────────────

ABILITY_MAP: dict[str, dict[str, Any]] = {

    # ── Лесная зона (1–10) ────────────────────────────────────────────────────
    "spider": {
        "venom_chance": 0.35,
        "venom_potency": 4,
        "venom_turns": 3,
    },
    "zombie": {
        "undying": True,
        "undying_regen_pct": 20,
    },
    "ent": {
        "stun_chance": 0.22,    # «Корень» — сковывает
    },
    "boar": {
        "bleed_chance": 0.28,
        "bleed_potency": 3,
        "bleed_turns": 2,
    },

    # ── Болотная зона (11–20) ─────────────────────────────────────────────────
    "leech": {
        "drain_pct": 0.22,
    },
    "gas_frog": {
        "venom_chance": 0.45,
        "venom_potency": 5,
        "venom_turns": 2,
    },
    "bog_mosquito": {
        "bleed_chance": 0.30,
        "bleed_potency": 3,
        "bleed_turns": 2,
        "drain_pct": 0.10,
    },
    "witch": {
        "curse_chance": 0.35,
        "curse_turns": 2,
    },
    "slime": {
        "venom_chance": 0.20,
        "venom_potency": 3,
        "venom_turns": 2,
    },

    # ── Тёмные пещеры (21–30) ─────────────────────────────────────────────────
    "shade": {
        "pierce_pct": 40,       # призрак — игнорирует 40% брони
    },
    "echo": {
        "pierce_pct": 35,
        "venom_chance": 0.20,
        "venom_potency": 3,
        "venom_turns": 2,
    },
    "crawler": {
        "bleed_chance": 0.40,
        "bleed_potency": 4,
        "bleed_turns": 3,
    },
    "gloom_weaver": {
        "curse_chance": 0.30,
        "curse_turns": 2,
        "pierce_pct": 20,
    },

    # ── Ледяные вершины (31–40) ───────────────────────────────────────────────
    "yeti": {
        "stun_chance": 0.30,    # мощный удар
        "bleed_chance": 0.20,
        "bleed_potency": 3,
        "bleed_turns": 2,
    },
    "ice_elemental": {
        "freeze_stack": True,   # заморозка через стаки
        "pierce_pct": 15,
    },
    "golem_ice": {
        "shatter_death": True,
        "pierce_pct": 5,
    },
    "frost_wisp": {
        "freeze_stack": True,
        "pierce_pct": 20,
    },
    "mini_frost_troll": {
        "regen_threshold": 0.30,
        "regen_pct": 15,
        "stun_chance": 0.18,
    },
    "frost_spider": {
        "venom_chance": 0.30,
        "venom_potency": 4,
        "venom_turns": 2,
        "pierce_pct": 10,
    },
    "harpy": {
        "bleed_chance": 0.35,
        "bleed_potency": 3,
        "bleed_turns": 2,
    },

    # ── Пустыня (41–50) ───────────────────────────────────────────────────────
    "cobra": {
        "venom_chance": 0.55,
        "venom_potency": 6,
        "venom_turns": 3,
    },
    "sand_wraith": {
        "pierce_pct": 50,       # призрак пустыни — игнорирует половину брони
    },
    "mirage": {
        "pierce_pct": 40,
        "stun_chance": 0.18,
    },
    "salt_lich": {
        "drain_pct": 0.18,
        "pierce_pct": 25,
        "curse_chance": 0.25,
        "curse_turns": 2,
    },
    "scorpion": {
        "venom_chance": 0.40,
        "venom_potency": 5,
        "venom_turns": 3,
    },

    # ── Вулканические руины (51–60) ───────────────────────────────────────────
    "salamander": {
        "burn_chance": 0.45,
        "burn_potency": 5,
        "burn_turns": 3,
    },
    "drake": {
        "burn_chance": 0.30,
        "burn_potency": 4,
        "burn_turns": 2,
        "breath_period": 3,     # каждые 3 хода — огненное дыхание (×2 урон)
    },
    "obsidian_hound": {
        "bleed_chance": 0.35,
        "bleed_potency": 4,
        "bleed_turns": 2,
        "stun_chance": 0.15,
    },
    "ember_spirit": {
        "burn_chance": 0.50,
        "burn_potency": 4,
        "burn_turns": 2,
        "pierce_pct": 15,
    },
    "cinder_imp": {
        "burn_chance": 0.35,
        "burn_potency": 3,
        "burn_turns": 2,
    },

    # ── Небесная цитадель (61–70) ─────────────────────────────────────────────
    "valkyrie": {
        "shield_period": 4,     # каждые 4 хода монстра — щит, блокирует удар
        "bleed_chance": 0.25,
        "bleed_potency": 3,
        "bleed_turns": 2,
    },
    "storm_elem": {
        "stun_chance": 0.28,
        "pierce_pct": 20,
    },
    "thunder_wisp": {
        "stun_chance": 0.22,
        "pierce_pct": 25,
    },
    "fallen": {
        "drain_pct": 0.15,
        "curse_chance": 0.25,
        "curse_turns": 2,
    },
    "cloud_stalker": {
        "pierce_pct": 30,
        "stun_chance": 0.20,
    },

    # ── Бездна Хаоса (71–80) ──────────────────────────────────────────────────
    "void_ling": {
        "pierce_pct": 60,       # из Бездны — почти не блокируется
    },
    "corruptor": {
        "curse_chance": 0.45,
        "curse_turns": 3,
        "drain_pct": 0.12,
    },
    "chaos_spawn": {
        "chaos_strike": True,   # случайный эффект при каждой атаке
    },
    "fractal_hound": {
        "bleed_chance": 0.45,
        "bleed_potency": 5,
        "bleed_turns": 3,
        "drain_pct": 0.12,
    },
    "mad_cultist": {
        "curse_chance": 0.38,
        "curse_turns": 2,
        "venom_chance": 0.25,
        "venom_potency": 4,
        "venom_turns": 2,
    },

    # ── Зал Вечности (81–90) ─────────────────────────────────────────────────
    "rune_golem": {
        "rune_absorb_pct": 0.28,   # поглощает 28% входящего урона от игрока
        "regen_threshold": 0.35,
        "regen_pct": 12,
    },
    "time_phantom": {
        "double_turn_chance": 0.28,  # 28% шанс атаковать дважды
        "pierce_pct": 30,
    },
    "chrono_wraith": {
        "pierce_pct": 70,
        "drain_pct": 0.15,
    },
    "seraph_dark": {
        "regen_threshold": 0.40,
        "regen_pct": 20,
        "pierce_pct": 20,
        "curse_chance": 0.25,
        "curse_turns": 2,
    },
    "archdemon": {
        "drain_pct": 0.20,
        "pierce_pct": 35,
        "burn_chance": 0.35,
        "burn_potency": 5,
        "burn_turns": 2,
    },
    "eternity_warden": {
        "rune_absorb_pct": 0.20,
        "double_turn_chance": 0.20,
        "regen_threshold": 0.25,
        "regen_pct": 10,
    },
}


def get_abilities(template_key: str) -> dict[str, Any]:
    """Способности монстра по ключу шаблона. Elite_ снимается."""
    k = str(template_key or "")
    if k.startswith("elite_"):
        k = k[6:]
    return ABILITY_MAP.get(k, {})


# ── Применение до хода ───────────────────────────────────────────────────────

def apply_pre_turn_abilities(state: dict[str, Any], logs: list[str]) -> None:
    """
    Вызывается в НАЧАЛЕ хода монстра (до любой атаки).
    Обрабатывает: регенерацию, щит, огненное дыхание.
    """
    m = state["monster"]
    tk = str(m.get("template_key", ""))
    ab = get_abilities(tk)
    if not ab:
        return

    mhp = int(m["hp"])
    mmx = int(m["max_hp"])
    mt = int(state.get("monster_turn", 0))

    # ── Регенерация (один раз за бой при HP < порога) ────────────────────────
    regen_thr = ab.get("regen_threshold")
    if (
        regen_thr is not None
        and not state.get("monster_regen_used")
        and mmx > 0
        and mhp / mmx < float(regen_thr)
    ):
        regen_pct = int(ab.get("regen_pct", 15))
        healed = max(1, int(mmx * regen_pct / 100))
        m["hp"] = min(mmx, mhp + healed)
        state["monster_regen_used"] = True
        logs.append(
            f"🩹 {m.get('emoji', '👹')} <b>Регенерация!</b> +{healed} HP "
            f"(восстановление при низком здоровье)."
        )

    # ── Периодический щит (valkyrie, каждые N ходов) ─────────────────────────
    period = ab.get("shield_period")
    if period is not None and mt > 0 and mt % int(period) == 0:
        state["monster_damage_shield"] = True
        logs.append(
            f"🛡️ {m.get('emoji', '👹')} <b>поднимает щит</b> — следующий удар будет заблокирован!"
        )

    # ── Огненное дыхание (drake, каждые N ходов) ─────────────────────────────
    breath = ab.get("breath_period")
    if breath is not None and mt > 0 and mt % int(breath) == 0:
        state["monster_breath_active"] = True


# ── Применение после удара ───────────────────────────────────────────────────

def apply_post_hit_abilities(
    state: dict[str, Any],
    dealt_damage: int,
    logs: list[str],
) -> None:
    """
    Вызывается ПОСЛЕ нанесения урона монстром игроку.
    Применяет яд, кровотечение, ожог, жизнепоглощение, оглушение, проклятие, хаос.
    """
    if int(state.get("player_hp", 0)) <= 0:
        return

    m = state["monster"]
    tk = str(m.get("template_key", ""))
    ab = get_abilities(tk)
    if not ab:
        return

    # ── Яд ───────────────────────────────────────────────────────────────────
    if "venom_chance" in ab and random.random() < float(ab["venom_chance"]):
        pot = int(ab.get("venom_potency", 4))
        trn = int(ab.get("venom_turns", 3))
        effects.add_effect("player", state, "Яд монстра", "poison", trn, {"potency_percent": pot})
        logs.append(f"☠️ Яд! −{pot}% HP/ход × {trn} х.")

    # ── Кровотечение ─────────────────────────────────────────────────────────
    if "bleed_chance" in ab and random.random() < float(ab["bleed_chance"]):
        pot = int(ab.get("bleed_potency", 3))
        trn = int(ab.get("bleed_turns", 2))
        effects.add_effect("player", state, "Рана", "bleed", trn, {"potency_percent": pot})
        logs.append(f"🩸 Рана! −{pot}% HP/ход × {trn} х.")

    # ── Ожог ─────────────────────────────────────────────────────────────────
    if "burn_chance" in ab and random.random() < float(ab["burn_chance"]):
        pot = int(ab.get("burn_potency", 5))
        trn = int(ab.get("burn_turns", 3))
        effects.add_effect("player", state, "Ожог", "burn", trn, {"potency_percent": pot})
        logs.append(f"🔥 Ожог! −{pot}% HP/ход × {trn} х.")

    # ── Жизнепоглощение ──────────────────────────────────────────────────────
    if "drain_pct" in ab and dealt_damage > 0:
        heal = max(1, int(dealt_damage * float(ab["drain_pct"])))
        m["hp"] = min(int(m["max_hp"]), int(m["hp"]) + heal)
        logs.append(f"🩸 Враг поглощает жизнь: +{heal} HP.")

    # ── Оглушение (следующее действие игрока пропущено) ─────────────────────
    if "stun_chance" in ab and random.random() < float(ab["stun_chance"]) * MONSTER_STUN_CHANCE_MULT:
        state["player_skip_next_action"] = True
        logs.append("💫 <b>Оглушение!</b> Твоё следующее действие пропущено.")

    # ── Проклятие (снижает урон игрока) ──────────────────────────────────────
    if "curse_chance" in ab and random.random() < float(ab["curse_chance"]):
        turns = int(ab.get("curse_turns", 2))
        state["player_damage_mult"] = min(
            float(state.get("player_damage_mult", 1.0)), 0.80
        )
        state["player_curse_turns"] = max(
            int(state.get("player_curse_turns", 0)), turns
        )
        logs.append(f"🌑 <b>Проклятие!</b> Твой урон −20% на {turns} х.")

    # ── Заморозка (стаки Озноба) ──────────────────────────────────────────────
    if ab.get("freeze_stack") and dealt_damage > 0:
        stacks = int(state.get("player_freeze_stacks", 0)) + 1
        if stacks >= 3:
            state["player_freeze_stacks"] = 0
            state["player_skip_next_action"] = True
            logs.append("❄️ <b>Заморозка!</b> Тело сковал лед, ты пропускаешь ход.")
        else:
            state["player_freeze_stacks"] = stacks
            logs.append(f"🥶 <b>Озноб</b> ({stacks}/3): твои движения замедляются.")

    # ── Хаотический удар (chaos_spawn) ───────────────────────────────────────
    if ab.get("chaos_strike") and random.random() < 0.50:
        roll = random.randint(0, 2)
        if roll == 0:
            effects.add_effect(
                "player", state, "Хаотический яд", "poison", 2, {"potency_percent": 4}
            )
            logs.append("🌀 Хаос: яд!")
        elif roll == 1:
            state["player_skip_next_action"] = True
            logs.append("🌀 Хаос: оглушение!")
        else:
            effects.add_effect(
                "player", state, "Хаотический ожог", "burn", 2, {"potency_percent": 4}
            )
            logs.append("🌀 Хаос: ожог!")


# ── Поглощение голема (входящий урон) ────────────────────────────────────────

def apply_rune_golem_absorb(
    state: dict[str, Any],
    incoming_dmg: int,
    logs: list[str],
) -> int:
    """
    Для rune_golem / eternity_warden: поглощает часть входящего урона от игрока.
    Вызывать в player_attack / player_skill после расчёта dmg.
    Возвращает скорректированный урон.
    """
    m = state.get("monster", {})
    tk = str(m.get("template_key", ""))
    ab = get_abilities(tk)
    absorb_pct = float(ab.get("rune_absorb_pct", 0.0))
    if absorb_pct <= 0 or incoming_dmg <= 0:
        return incoming_dmg
    absorbed = max(1, int(incoming_dmg * absorb_pct))
    reduced = max(1, incoming_dmg - absorbed)
    logs.append(f"🔮 Рунный щит голема поглотил {absorbed} урона!")
    return reduced


# ── Щит монстра (valkyrie — блокирует один удар) ─────────────────────────────

def check_and_consume_monster_shield(
    state: dict[str, Any],
    logs: list[str],
) -> bool:
    """
    Проверяет, есть ли активный щит монстра.
    Если есть — поглощает удар и возвращает True (удар блокирован).
    """
    if state.get("monster_damage_shield"):
        del state["monster_damage_shield"]
        logs.append("🛡️ Щит монстра поглотил твой удар!")
        return True
    return False


# ── Двойная атака (time_phantom) ─────────────────────────────────────────────

def roll_monster_double_turn(state: dict[str, Any]) -> bool:
    """True — монстр атакует снова в этом ходе."""
    m = state.get("monster", {})
    tk = str(m.get("template_key", ""))
    ab = get_abilities(tk)
    chance = float(ab.get("double_turn_chance", 0.0))
    return chance > 0 and random.random() < chance


# ── Нежить (zombie — выживает один раз при смертельном ударе) ───────────────

def check_zombie_undying(state: dict[str, Any], logs: list[str]) -> bool:
    """
    Вызывается когда HP монстра ≤ 0.
    Если это zombie и способность не использована — воскрешает его.
    True = монстр выжил (не считать победой).
    """
    m = state.get("monster", {})
    tk = str(m.get("template_key", ""))
    ab = get_abilities(tk)
    if not ab.get("undying"):
        return False
    if state.get("monster_undying_used"):
        return False
    regen_pct = int(ab.get("undying_regen_pct", 20))
    mmx = int(m.get("max_hp", 1))
    revive_hp = max(1, int(mmx * regen_pct / 100))
    m["hp"] = revive_hp
    state["monster_undying_used"] = True
    logs.append(
        f"💀 <b>Нежить!</b> {m.get('emoji', '👹')} поднялся с {revive_hp} HP! "
        f"(воскрешение срабатывает один раз за бой)"
    )
    return True


# ── Проверка уникальных пробиваний брони ─────────────────────────────────────
def apply_shatter_death(state: dict[str, Any], logs: list[str]) -> None:
    """Вызывается при смерти монстра с shatter_death."""
    m = state.get("monster", {})
    tk = str(m.get("template_key", ""))
    ab = get_abilities(tk)
    if not ab.get("shatter_death"):
        return
    
    # Урон = 50% от базовой брони монстра
    dmg = max(5, int(int(m.get("defense", 0)) * 0.5))
    state["player_hp"] = max(0, int(state["player_hp"]) - dmg)
    logs.append(f"💥 <b>Осколки!</b> При смерти {m.get('emoji', '👹')} разлетается на куски: −{dmg} HP.")


# ── Проверка уникальных пробиваний брони ─────────────────────────────────────

def get_extra_pierce_fraction(template_key: str) -> float:
    """
    Дополнительное пробивание брони из таблицы способностей (0.0–0.95).
    Суммируется с базовым monster armor_penetration в monster_turn.
    """
    ab = get_abilities(template_key)
    pct = float(ab.get("pierce_pct", 0))
    return min(0.95, pct / 100.0)
