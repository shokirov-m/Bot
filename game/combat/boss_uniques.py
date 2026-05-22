"""
Уникальные хардкор-механики сильных и мини-боссов.
Каждый template_key — свой набор: уклонения, метеориты по отряду, тяжёлые дебаффы.
"""

from __future__ import annotations

import html
import random
from typing import Any

from game.combat import effects

# ── Каталог механик (id → параметры) ─────────────────────────────────────────

_MECH: dict[str, dict[str, Any]] = {
    # Мини-боссы
    "mini_alpha_wolf": {
        "label": "🐺 Стая: кровавая пасть",
        "bleed": (0.55, 7, 4),
        "fear_miss": 0.12,
    },
    "mini_bog_queen": {
        "label": "👑 Токсичное болото",
        "poison": (0.65, 8, 5),
        "vuln": (0.40, 1.30, 3),
    },
    "mini_shadow_weaver": {
        "label": "🕸️ Плетение теней",
        "curse": (0.50, 0.65, 4),
        "pierce_bonus": 0.35,
    },
    "mini_frost_troll": {
        "label": "❄️ Ледяной колосс",
        "freeze_fast": True,
        "stun": (0.35, 1),
        "regen_once": (0.35, 18),
    },
    "mini_sand_titan": {
        "label": "🏜️ Разрыв панциря",
        "vuln": (0.45, 1.35, 4),
        "bleed": (0.40, 6, 3),
    },
    "mini_magma_lord": {
        "label": "🌋 Жар магмы",
        "burn": (0.55, 8, 4),
        "meteor_every": 4,
        "meteor_mult": 0.55,
    },
    "mini_blood_barons": {
        "label": "🩸 Кровавый суд",
        "bleed": (0.50, 8, 4),
        "curse": (0.40, 0.60, 3),
        "drain": 0.18,
    },
    "mini_chaos_knight": {
        "label": "🌀 Рыцарь хаоса",
        "chaos_debuff": True,
        "vuln": (0.35, 1.28, 3),
    },
    "mini_time_judge": {
        "label": "⏳ Приговор времени",
        "stun": (0.38, 1),
        "silence": (0.30, 2),
        "pierce_bonus": 0.25,
    },
    "mini_necro_servant": {
        "label": "💀 Некрослуга",
        "poison": (0.50, 7, 4),
        "drain": 0.15,
    },
    "mini_fang_hunter": {
        "label": "🦇 Охотник клыков",
        "bleed": (0.48, 7, 4),
        "vuln": (0.38, 1.25, 3),
    },
    "tower_warden": {
        "label": "🗼 Страж башни",
        "shield_every": 3,
        "stun": (0.28, 1),
    },
    # Сильные боссы
    "boss_ancient_treant": {
        "label": "🌳 Корни мирового древа",
        "root_every": 4,
        "poison": (0.50, 7, 4),
        "vuln": (0.35, 1.32, 3),
    },
    "boss_slime_king": {
        "label": "🦠 Король слизи: кислотный прилив",
        "poison": (0.70, 9, 5),
        "meteor_every": 3,
        "meteor_mult": 0.65,
        "vuln": (0.40, 1.35, 4),
    },
    "boss_night_stalker": {
        "label": "🌑 Ночной Сталкер: шаг в тень",
        "dodge_every": 3,
        "curse": (0.55, 0.55, 4),
        "blind_miss": 0.18,
    },
    "boss_glacier_king": {
        "label": "❄️ Ледяной Король: метель",
        "freeze_fast": True,
        "blizzard_every": 4,
        "meteor_mult": 0.70,
        "stun": (0.32, 1),
    },
    "boss_time_scarab": {
        "label": "🪲 Скарабей: разлом времени",
        "time_skip_every": 5,
        "meteor_every": 4,
        "meteor_mult": 0.75,
        "silence": (0.35, 2),
    },
    "boss_ember_dragon": {
        "label": "🐉 Пепельный метеор",
        "meteor_every": 3,
        "meteor_mult": 0.90,
        "burn": (0.60, 10, 5),
        "vuln": (0.45, 1.40, 4),
    },
    "boss_blood_prince": {
        "label": "🦇 Князь: кровавый приговор",
        "bleed": (0.65, 10, 5),
        "curse": (0.50, 0.50, 4),
        "drain": 0.25,
        "vuln": (0.50, 1.45, 4),
    },
    "boss_chaos_avatar": {
        "label": "👁️ Аватар: нова хаоса",
        "chaos_nova_every": 3,
        "meteor_mult": 0.80,
        "vuln": (0.45, 1.38, 4),
    },
    "boss_eternity_judge": {
        "label": "⚖️ Судья: безмолвие вечности",
        "silence": (0.45, 3),
        "judgment_every": 4,
        "pierce_bonus": 0.55,
        "curse": (0.50, 0.52, 4),
    },
    "boss_spire_warden": {
        "label": "🦇 Страж шпиля",
        "bleed": (0.55, 9, 4),
        "meteor_every": 4,
        "meteor_mult": 0.70,
    },
    "boss_tower_core": {
        "label": "💠 Ядро башни",
        "shield_every": 2,
        "meteor_every": 5,
        "meteor_mult": 0.85,
        "stun": (0.30, 1),
    },
    "boss_sky_tyrant": {
        "label": "☁️ Тиран небес",
        "meteor_every": 3,
        "meteor_mult": 0.80,
        "stun": (0.35, 1),
    },
    "mini_storm_herald": {
        "label": "⛈️ Вестник бури",
        "stun": (0.40, 1),
        "meteor_every": 4,
        "meteor_mult": 0.60,
    },
}


def _spec_for(state: dict[str, Any]) -> dict[str, Any] | None:
    bu = state.get("boss_unique")
    if not isinstance(bu, dict):
        return None
    key = str(bu.get("key") or "")
    return _MECH.get(key)


def init_boss_unique_state(state: dict[str, Any]) -> None:
    m = state.get("monster") or {}
    if not (m.get("is_mini_boss") or m.get("is_major_boss")):
        return
    tk = str(m.get("template_key") or "")
    if tk.startswith("elite_"):
        tk = tk[6:]
    spec = _MECH.get(tk)
    if not spec:
        return
    state["boss_unique"] = {
        "key": tk,
        "turn": 0,
        "regen_used": False,
        "label": str(spec.get("label") or "👑 Уникальная механика босса"),
    }
    pen = float(spec.get("pierce_bonus") or 0)
    if pen > 0:
        cur = float(m.get("armor_penetration") or 0)
        m["armor_penetration"] = min(0.95, cur + pen)


def opening_mechanic_line(state: dict[str, Any]) -> str:
    bu = state.get("boss_unique")
    if not isinstance(bu, dict):
        return ""
    return f"☠️ <b>Хардкор:</b> {html.escape(str(bu.get('label') or ''))}"


def _bump_turn(state: dict[str, Any]) -> int:
    bu = state.get("boss_unique")
    if not isinstance(bu, dict):
        return 0
    t = int(bu.get("turn") or 0) + 1
    bu["turn"] = t
    return t


def monster_evades_player_attack(state: dict[str, Any], logs: list[str]) -> bool:
    if int(state.get("boss_unique_evade_turns") or 0) > 0:
        state["boss_unique_evade_turns"] = int(state["boss_unique_evade_turns"]) - 1
        m = state.get("monster") or {}
        logs.append(
            f"🌫️ <b>{html.escape(str(m.get('name') or 'Босс'))}</b> растворяется в тени — "
            f"<b>промах!</b>",
        )
        return True
    return False


def _apply_poison(state: dict[str, Any], chance: float, pot: int, turns: int, logs: list[str]) -> None:
    if random.random() < chance:
        effects.add_effect("player", state, "Яд босса", "poison", turns, {"potency_percent": pot})
        logs.append(f"☠️ <b>Яд босса!</b> −{pot}% HP/ход × {turns} х.")


def _apply_bleed(state: dict[str, Any], chance: float, pot: int, turns: int, logs: list[str]) -> None:
    if random.random() < chance:
        effects.add_effect("player", state, "Кровотечение босса", "bleed", turns, {"potency_percent": pot})
        logs.append(f"🩸 <b>Кровавая рана!</b> −{pot}% HP/ход × {turns} х.")


def _apply_burn(state: dict[str, Any], chance: float, pot: int, turns: int, logs: list[str]) -> None:
    if random.random() < chance:
        effects.add_effect("player", state, "Ожог босса", "burn", turns, {"potency_percent": pot})
        logs.append(f"🔥 <b>Ожог босса!</b> −{pot}% HP/ход × {turns} х.")


def _apply_curse(state: dict[str, Any], chance: float, mult: float, turns: int, logs: list[str]) -> None:
    if random.random() < chance:
        state["player_damage_mult"] = min(float(state.get("player_damage_mult", 1.0)), mult)
        state["player_curse_turns"] = max(int(state.get("player_curse_turns", 0)), turns)
        pct = int((1.0 - mult) * 100)
        logs.append(f"🌑 <b>Проклятие босса!</b> Твой урон −{pct}% на {turns} х.")


def _apply_vuln(state: dict[str, Any], chance: float, mult: float, turns: int, logs: list[str]) -> None:
    if random.random() < chance:
        cur = float(state.get("player_boss_vuln_mult", 1.0))
        state["player_boss_vuln_mult"] = max(cur, mult)
        state["player_boss_vuln_turns"] = max(int(state.get("player_boss_vuln_turns", 0)), turns)
        pct = int((mult - 1.0) * 100)
        logs.append(f"💥 <b>Уязвимость!</b> Ты получаешь на {pct}% больше урона ({turns} х.).")


def _apply_fear(state: dict[str, Any], miss_add: float, turns: int, logs: list[str]) -> None:
    state["player_aura_miss_chance"] = float(state.get("player_aura_miss_chance", 0.0)) + miss_add
    state["player_boss_fear_turns"] = max(int(state.get("player_boss_fear_turns", 0)), turns)
    logs.append(f"😱 <b>Страх!</b> Шанс промаха +{int(miss_add * 100)}% ({turns} х.).")


def _apply_silence(state: dict[str, Any], chance: float, turns: int, logs: list[str]) -> None:
    if random.random() < chance:
        state["player_skill_silence_turns"] = max(int(state.get("player_skill_silence_turns", 0)), turns)
        logs.append(f"🔇 <b>Безмолвие!</b> Навыки заблокированы {turns} х.")


def _apply_stun(state: dict[str, Any], chance: float, logs: list[str]) -> None:
    if random.random() < chance:
        state["player_skip_next_action"] = True
        logs.append("💫 <b>Оглушение босса!</b> Следующее действие пропущено.")


def _meteor_strike(
    state: dict[str, Any],
    logs: list[str],
    *,
    mult: float,
    hit_mercs: bool = True,
    label: str = "☄️ Метеорит босса",
) -> None:
    """Урон игроку и наёмникам (% от ATK босса)."""
    m = state["monster"]
    atk = int(m.get("atk") or 1)
    raw = max(1, int(atk * mult * random.uniform(0.92, 1.12)))
    from game.combat.engine import (
        _apply_elemental_resist_to_incoming_damage,
        combo_break_on_player_hurt,
        player_defense_value,
        record_monster_last_damage_to_player,
    )
    from game.combat import companions as companions_mod
    from game.enemies.coliseum import combat_hooks as coliseum_hooks

    logs.append(f"<b>{label}</b> обрушивается на отряд!")
    defense = player_defense_value(state)
    dmg = max(1, raw - int(defense * 0.35))
    vuln = float(state.get("player_boss_vuln_mult", 1.0))
    if vuln > 1.0:
        dmg = max(1, int(dmg * vuln))
    dmg = coliseum_hooks.mulan_reduce_incoming_damage(state, dmg, logs)
    dmg = companions_mod.apply_tank_intercept_to_player_damage(state, dmg, logs)
    shield = int(state.get("player_shield_hp", 0))
    if shield > 0:
        absorbed = min(shield, dmg)
        state["player_shield_hp"] = shield - absorbed
        if int(state["player_shield_hp"]) <= 0:
            state["player_shield_hp_max"] = 0
            state["player_shield_kind"] = ""
        dmg -= absorbed
        if absorbed > 0:
            kind = str(state.get("player_shield_kind") or "shield")
            label = "Барьер" if kind == "barrier" else "Щит"
            logs.append(f"🛡️ {label} поглотил {absorbed} урона от метеорита.")
    pre = int(state["player_hp"])
    state["player_hp"] = max(0, pre - dmg)
    if dmg > 0:
        logs.append(f"→ −{dmg} HP герою")
        record_monster_last_damage_to_player(state, dmg)
        combo_break_on_player_hurt(state)

    if hit_mercs:
        for c in list(state.get("companions") or []):
            if c.get("dead") or int(c.get("hp", 0) or 0) <= 0:
                continue
            md = max(1, int(raw * 0.72) - int(c.get("def", 0) or 0) // 2)
            if vuln > 1.0:
                md = max(1, int(md * vuln))
            chp = int(c.get("hp", 0))
            c["hp"] = max(0, chp - md)
            nm = html.escape(str(c.get("name") or "Наёмник"))
            if int(c["hp"]) <= 0:
                c["dead"] = True
                logs.append(f"☄️ <b>{nm}</b> выбит метеоритом (−{md} HP).")
            else:
                logs.append(f"☄️ <b>{nm}</b>: −{md} HP от ударной волны.")


def _chaos_debuff_roll(state: dict[str, Any], logs: list[str]) -> None:
    roll = random.randint(0, 5)
    if roll == 0:
        _apply_poison(state, 1.0, 9, 4, logs)
    elif roll == 1:
        _apply_bleed(state, 1.0, 8, 4, logs)
    elif roll == 2:
        _apply_burn(state, 1.0, 9, 4, logs)
    elif roll == 3:
        _apply_curse(state, 1.0, 0.50, 4, logs)
    elif roll == 4:
        _apply_vuln(state, 1.0, 1.40, 4, logs)
    else:
        _apply_stun(state, 1.0, logs)
        _apply_silence(state, 1.0, 2, logs)


def on_monster_turn_start(state: dict[str, Any], logs: list[str]) -> bool:
    """
    Старт хода босса: периодические уклонения, метеориты, метель.
    True — обычная атака монстра в этом ходу не нужна (уже отыграли механику).
    """
    spec = _spec_for(state)
    if not spec:
        return False
    turn = _bump_turn(state)
    m = state["monster"]

    # Реген мини-босса (один раз)
    regen = spec.get("regen_once")
    if regen and not state.get("boss_unique", {}).get("regen_used"):
        thr, pct = float(regen[0]), int(regen[1])
        mmx = int(m.get("max_hp") or 1)
        mhp = int(m.get("hp") or 0)
        if mhp / mmx < thr:
            healed = max(1, int(mmx * pct / 100))
            m["hp"] = min(mmx, mhp + healed)
            state["boss_unique"]["regen_used"] = True
            logs.append(f"💚 <b>{m.get('emoji', '👹')}</b> восстанавливает <b>{healed}</b> HP!")

    dodge_n = int(spec.get("dodge_every") or 0)
    if dodge_n > 0 and turn % dodge_n == 0:
        state["boss_unique_evade_turns"] = 2
        logs.append(
            f"🌑 <b>Шаг в тень!</b> Следующие удары по боссу могут не достичь цели "
            f"(уклонение {dodge_n} х. цикла).",
        )

    shield_n = int(spec.get("shield_every") or 0)
    if shield_n > 0 and turn % shield_n == 0:
        state["monster_damage_shield"] = True
        logs.append("🛡️ <b>Босс поднимает щит</b> — блокирует следующий удар героя!")

    root_n = int(spec.get("root_every") or 0)
    if root_n > 0 and turn % root_n == 0:
        state["player_skip_next_action"] = True
        _apply_poison(state, 1.0, 7, 3, logs)
        logs.append("🌿 <b>Корни сковали тебя!</b> Пропуск хода + яд.")

    time_skip = int(spec.get("time_skip_every") or 0)
    if time_skip > 0 and turn % time_skip == 0:
        state["player_skip_next_action"] = True
        _apply_silence(state, 1.0, 1, logs)
        logs.append("⏳ <b>Разлом времени!</b> Твой ход сорван.")

    meteor_n = int(spec.get("meteor_every") or 0)
    bliz = int(spec.get("blizzard_every") or 0)
    chaos_n = int(spec.get("chaos_nova_every") or 0)
    judgment = int(spec.get("judgment_every") or 0)

    if chaos_n > 0 and turn % chaos_n == 0:
        logs.append("👁️ <b>Нова хаоса!</b>")
        _chaos_debuff_roll(state, logs)
        _meteor_strike(
            state,
            logs,
            mult=float(spec.get("meteor_mult") or 0.75),
            label="🌀 Удар хаоса",
        )
        return int(state.get("player_hp", 0)) > 0

    if judgment > 0 and turn % judgment == 0:
        _apply_curse(state, 1.0, 0.48, 4, logs)
        _apply_vuln(state, 1.0, 1.42, 3, logs)
        _meteor_strike(state, logs, mult=0.85, label="⚖️ Удар приговора")
        return int(state.get("player_hp", 0)) > 0

    trigger_meteor = (meteor_n > 0 and turn % meteor_n == 0) or (bliz > 0 and turn % bliz == 0)
    if trigger_meteor:
        lbl = "❄️ Ледяная метель" if bliz else "☄️ Метеорит босса"
        _meteor_strike(
            state,
            logs,
            mult=float(spec.get("meteor_mult") or 0.70),
            label=lbl,
        )
        return int(state.get("player_hp", 0)) > 0

    return False


def apply_post_hit_debuffs(state: dict[str, Any], dealt_damage: int, logs: list[str]) -> None:
    """После удара босса по игроку — уникальные дебаффы."""
    spec = _spec_for(state)
    if not spec or dealt_damage <= 0:
        return
    m = state["monster"]

    po = spec.get("poison")
    if po:
        _apply_poison(state, float(po[0]), int(po[1]), int(po[2]), logs)
    bl = spec.get("bleed")
    if bl:
        _apply_bleed(state, float(bl[0]), int(bl[1]), int(bl[2]), logs)
    bn = spec.get("burn")
    if bn:
        _apply_burn(state, float(bn[0]), int(bn[1]), int(bn[2]), logs)
    cr = spec.get("curse")
    if cr:
        _apply_curse(state, float(cr[0]), float(cr[1]), int(cr[2]), logs)
    vn = spec.get("vuln")
    if vn:
        _apply_vuln(state, float(vn[0]), float(vn[1]), int(vn[2]), logs)
    st = spec.get("stun")
    if st:
        _apply_stun(state, float(st[0]), logs)
    sl = spec.get("silence")
    if sl:
        _apply_silence(state, float(sl[0]), int(sl[1]), logs)
    if spec.get("fear_miss"):
        _apply_fear(state, float(spec["fear_miss"]), 2, logs)
    if spec.get("blind_miss"):
        _apply_fear(state, float(spec["blind_miss"]), 3, logs)

    drain = float(spec.get("drain") or 0)
    if drain > 0:
        heal = max(1, int(dealt_damage * drain))
        m["hp"] = min(int(m["max_hp"]), int(m["hp"]) + heal)
        logs.append(f"🩸 Босс поглощает <b>{heal}</b> HP.")

    if spec.get("freeze_fast"):
        stacks = int(state.get("player_freeze_stacks", 0)) + 1
        if stacks >= 2:
            state["player_freeze_stacks"] = 0
            state["player_skip_next_action"] = True
            logs.append("❄️ <b>Ледяной оков!</b> Пропуск хода.")
        else:
            state["player_freeze_stacks"] = stacks
            logs.append(f"🥶 <b>Озноб босса</b> ({stacks}/2 до оков).")

    if spec.get("chaos_debuff") and random.random() < 0.45:
        _chaos_debuff_roll(state, logs)


def tick_round_debuffs(state: dict[str, Any], logs: list[str]) -> None:
    ft = int(state.get("player_boss_fear_turns") or 0)
    if ft > 0:
        state["player_boss_fear_turns"] = ft - 1
        if ft <= 1:
            state["player_aura_miss_chance"] = max(
                0.0,
                float(state.get("player_aura_miss_chance", 0.0)) - 0.12,
            )
            logs.append("😌 Страх спадает.")

    vt = int(state.get("player_boss_vuln_turns") or 0)
    if vt > 0:
        state["player_boss_vuln_turns"] = vt - 1
        if vt <= 1:
            state["player_boss_vuln_mult"] = 1.0
            logs.append("💥 Уязвимость спала.")

    st = int(state.get("player_skill_silence_turns") or 0)
    if st > 0:
        state["player_skill_silence_turns"] = st - 1
        if st <= 1:
            logs.append("🔇 Безмолвие спало.")


def player_skill_silenced(state: dict[str, Any]) -> bool:
    return int(state.get("player_skill_silence_turns") or 0) > 0


def merge_ability_map_overrides() -> dict[str, dict[str, Any]]:
    """Доп. строки для monster_abilities.ABILITY_MAP (импорт при старте модуля)."""
    out: dict[str, dict[str, Any]] = {}
    for key, spec in _MECH.items():
        row: dict[str, Any] = {}
        if spec.get("pierce_bonus"):
            row["pierce_pct"] = int(float(spec["pierce_bonus"]) * 100)
        po = spec.get("poison")
        if po:
            row["venom_chance"] = min(0.85, float(po[0]))
            row["venom_potency"] = int(po[1])
            row["venom_turns"] = int(po[2])
        bl = spec.get("bleed")
        if bl:
            row["bleed_chance"] = min(0.85, float(bl[0]))
            row["bleed_potency"] = int(bl[1])
            row["bleed_turns"] = int(bl[2])
        bn = spec.get("burn")
        if bn:
            row["burn_chance"] = min(0.85, float(bn[0]))
            row["burn_potency"] = int(bn[1])
            row["burn_turns"] = int(bn[2])
        cr = spec.get("curse")
        if cr:
            row["curse_chance"] = min(0.75, float(cr[0]))
            row["curse_turns"] = int(cr[2])
        dr = spec.get("drain")
        if dr:
            row["drain_pct"] = float(dr)
        st = spec.get("stun")
        if st:
            row["stun_chance"] = min(0.55, float(st[0]))
        if spec.get("freeze_fast"):
            row["freeze_stack"] = True
        if spec.get("chaos_debuff"):
            row["chaos_strike"] = True
        if row:
            out[key] = row
    return out
