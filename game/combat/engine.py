"""
Ядро пошагового боя: атака, скиллы, ход монстра, проверка исхода.
Всё состояние — JSON-словарь (FSM).
"""

from __future__ import annotations

import random
from typing import Any, Literal

from game.characters.skills import SkillDef, passive_combat_modifiers, skills_for_class
from game.combat import effects, formulas, monster_ai
from game.items.runes import ELEMENTS, RuneData

Outcome = Literal["continue", "win", "lose"]

COMBO_BONUS_MULT = 1.15


def _log_weapon_rune_elemental_once(state: dict[str, Any], elem_bonus: int, logs: list[str]) -> None:
    """
    Строка в лог боя: как руны на оружии пересекаются со стихией врага (бонус уже в формуле).
    Показываем при каждом ударе/скилле, где учитывается weapon_rune_bonus_pct.
    """
    pct = int(elem_bonus)
    payloads = list(state.get("weapon_rune_payloads") or [])
    mon = state.get("monster") or {}
    mon_el = str(mon.get("element") or "earth")
    mon_meta = ELEMENTS.get(mon_el, ELEMENTS["earth"])
    mon_lbl = f"{mon_meta.get('emoji', '')} {mon_meta.get('name', mon_el)}".strip()
    if not payloads and pct <= 0:
        return
    if not payloads:
        head = "🎯 <b>Слабое звено стихии!</b>" if pct >= 30 else "✨ <b>Стихийный резонанс</b>"
        logs.append(f"{head} против <i>{mon_lbl}</i>: <b>+{pct}%</b> к урону.")
        return
    bits: list[str] = []
    for raw in payloads:
        rd = raw if isinstance(raw, dict) else {}
        try:
            r = RuneData.from_dict(rd)
        except (ValueError, TypeError, KeyError):
            continue
        em = ELEMENTS.get(r.element, {}).get("emoji", "·")
        rom = ("", "I", "II", "III", "IV", "V")[r.rank] if 1 <= r.rank <= 5 else str(r.rank)
        bits.append(f"{em}{rom}")
    rune_lbl = " ".join(bits) if bits else "руны"
    if pct <= 0:
        if bits and not state.get("rune_neutral_logged"):
            state["rune_neutral_logged"] = True
            logs.append(f"⚪ Руны ({rune_lbl}) без преимущества против <i>{mon_lbl}</i>.")
        return
    head = "🎯 <b>Слабое звено стихии!</b>" if pct >= 30 else "✨ <b>Удар по стихии</b>"
    logs.append(f"{head} — {rune_lbl} vs <i>{mon_lbl}</i>: <b>+{pct}%</b> к урону.")


COMBO_STREAK_TO_TRIGGER = 3


def combo_break_on_player_hurt(state: dict[str, Any]) -> None:
    """Сброс серии комбо при любом потере HP игроком (не считая добровольные эффекты)."""
    state["combo_streak"] = 0
    state["combo_next_mult"] = 1.0


def combo_apply_outgoing_damage(state: dict[str, Any], dmg: int, logs: list[str]) -> int:
    """
    Три удара подряд по врагу без получения урона → сообщение «КОМБО x3» и +15% к следующему удару.
    Вызывать после расчёта урона, до списания HP монстра.
    """
    if state.get("is_tutorial"):
        return dmg
    if dmg <= 0:
        return dmg
    pending = float(state.get("combo_next_mult") or 1.0)
    if pending > 1.001:
        new_dmg = max(1, round(dmg * pending))
        if new_dmg > dmg:
            logs.append("🔥 <b>Комбо-удар!</b> +15% к этому удару.")
        dmg = new_dmg
        state["combo_next_mult"] = 1.0
    st = int(state.get("combo_streak", 0)) + 1
    if st >= COMBO_STREAK_TO_TRIGGER:
        logs.append("⚡ <b>КОМБО x3!</b> Следующий удар по врагу <b>+15%</b>.")
        st = 0
        state["combo_next_mult"] = COMBO_BONUS_MULT
    state["combo_streak"] = st
    return dmg


def _m(state: dict[str, Any]) -> dict[str, Any]:
    return state["monster"]


def record_player_last_damage_to_monster(state: dict[str, Any], amount: int) -> None:
    """Последний урон по HP монстра (удар, скилл, DoT по врагу за тик, контрудар блока) — для UI, не сумма за бой."""
    if amount <= 0:
        return
    state["player_last_damage_to_monster"] = int(amount)


def record_monster_last_damage_to_player(state: dict[str, Any], amount: int) -> None:
    """Последний урон по HP игрока от удара монстра в его ход (после щита) — для UI."""
    if amount <= 0:
        return
    state["monster_last_damage_to_player"] = int(amount)


def _stats(state: dict[str, Any]) -> dict[str, int]:
    return state["stats"]


def _mods(state: dict[str, Any]) -> dict[str, Any]:
    return state["passive_mods"]


def apply_dot_damage_player(state: dict[str, Any]) -> list[str]:
    logs: list[str] = []
    pre_hp = int(state["player_hp"])
    mx = int(state["player_hp_max"])
    hp = int(state["player_hp"])
    new_eff: list[dict[str, Any]] = []
    for e in list(state.get("player_effects", [])):
        if e.get("key") == "burn":
            dmg = max(1, int(mx * int(e.get("potency_percent", 5)) / 100))
            hp -= dmg
            logs.append(f"🔥 Поджог: −{dmg} HP")
        elif e.get("key") == "poison":
            dmg = max(1, int(mx * int(e.get("potency_percent", 3)) / 100))
            hp -= dmg
            logs.append(f"💀 Яд: −{dmg} HP")
        elif e.get("key") == "bleed":
            dmg = max(1, int(mx * int(e.get("potency_percent", 2)) / 100))
            hp -= dmg
            logs.append(f"🩸 Кровотечение: −{dmg} HP")
        elif e.get("key") == "hot":
            heal = max(1, int(mx * int(e.get("potency_percent", 5)) / 100))
            hp = min(mx, hp + heal)
            logs.append(f"🌿 Исцеление со временем: +{heal} HP")
        turns = int(e.get("turns", 0)) - 1
        if turns > 0:
            e["turns"] = turns
            new_eff.append(e)
    state["player_hp"] = max(0, hp)
    state["player_effects"] = new_eff
    if int(state["player_hp"]) < pre_hp:
        combo_break_on_player_hurt(state)
    return logs


def apply_dot_damage_monster(state: dict[str, Any]) -> list[str]:
    logs: list[str] = []
    m = _m(state)
    hp = int(m["hp"])
    pre_hp = hp
    mx = int(m["max_hp"])
    new_eff: list[dict[str, Any]] = []
    for e in list(state.get("monster_effects", [])):
        if e.get("key") == "burn":
            dmg = max(1, int(mx * int(e.get("potency_percent", 3)) / 100))
            hp -= dmg
            logs.append(f"🔥 Враг горит: −{dmg} HP")
        elif e.get("key") == "bleed":
            dmg = max(1, int(mx * int(e.get("potency_percent", 4)) / 100))
            hp -= dmg
            logs.append(f"🩸 Враг истекает кровью: −{dmg} HP")
        elif e.get("key") == "poison":
            dmg = max(1, int(mx * int(e.get("potency_percent", 3)) / 100))
            hp -= dmg
            logs.append(f"☠️ Яд: −{dmg} HP")
        turns = int(e.get("turns", 0)) - 1
        if turns > 0:
            e["turns"] = turns
            new_eff.append(e)
    m["hp"] = max(0, hp)
    state["monster_effects"] = new_eff
    dealt = pre_hp - int(m["hp"])
    if dealt > 0:
        record_player_last_damage_to_monster(state, dealt)
    return logs


def regen_mp_passive(state: dict[str, Any]) -> list[str]:
    regen = int(_mods(state).get("mp_regen_turn", 0))
    if regen <= 0:
        return []
    cur = int(state["player_mp"])
    mx = int(state["player_mp_max"])
    new = min(mx, cur + regen)
    state["player_mp"] = new
    if new > cur:
        return [f"💙 MP +{new - cur} (пассив класса)."]
    return []


def tick_cooldowns(state: dict[str, Any]) -> None:
    for k in list(state.get("skill_cd", {}).keys()):
        v = int(state["skill_cd"][k])
        if v > 0:
            state["skill_cd"][k] = v - 1
    cd = int(state.get("monster_special_cd", 0))
    if cd > 0:
        state["monster_special_cd"] = cd - 1


def player_weapon_attack_value(state: dict[str, Any]) -> int:
    return int(state.get("weapon_attack", 3))


def player_defense_value(state: dict[str, Any]) -> int:
    vit = int(_stats(state)["vit"])
    base = vit // 2
    gear = int(state.get("player_equipment_defense", 0))
    arm_m = float(state.get("rune_armor_mult", 1.0))
    if arm_m != 1.0:
        gear = int(gear * arm_m)
    return int(
        base
        + float(_mods(state).get("def_bonus", 0))
        + int(state.get("player_fortify_bonus", 0))
        + int(state.get("player_level_def_bonus", 0))
        + gear,
    )


def monster_armor_value(state: dict[str, Any]) -> int:
    """Эффективная броня: база − разложение + временное укрепление."""
    m = _m(state)
    base = int(m["defense"])
    shred = int(state.get("monster_def_mod", 0))
    fort = int(state.get("monster_fortify_flat", 0))
    return max(0, base - shred + fort)


def elemental_bonus_percent(attacker_element: str | None, defender_element: str | None) -> int:
    """+15% если стихия атаки совпадает с «руной» игрока (здесь = элемент персонажа)."""
    if not attacker_element or not defender_element:
        return 0
    return 15 if attacker_element == defender_element else 0


def _apply_weapon_mastery_to_damage(state: dict[str, Any], dmg: int) -> int:
    mult = float(state.get("weapon_mastery_mult", 1.0))
    return max(1, int(dmg * mult))


def _mark_weapon_mastery_strike(state: dict[str, Any]) -> None:
    if state.get("player_weapon_type"):
        state["mastery_strike_pending"] = True


def _rune_status_proc_logs(state: dict[str, Any]) -> list[str]:
    """Случайные статусы на врага от вставленных рун."""
    logs: list[str] = []
    for raw in list(state.get("weapon_rune_payloads") or []):
        if not isinstance(raw, dict):
            continue
        try:
            r = RuneData.from_dict(raw)
        except (ValueError, TypeError, KeyError):
            continue
        if random.random() >= r.status_chance:
            continue
        meta = ELEMENTS.get(r.element, {})
        se = str(meta.get("status_effect", "burn"))
        if se == "burn":
            effects.add_effect(
                "monster",
                state,
                "Рунный жар",
                "burn",
                3,
                {"potency_percent": 4},
            )
            logs.append("🔥 Руна поджигает врага!")
        elif se == "freeze":
            state["monster_skip_next"] = True
            logs.append("❄️ Ледяная руна заледенила врага!")
        elif se == "paralyze":
            state["monster_skip_next"] = True
            logs.append("⚡ Паралич от руны!")
        elif se == "fear":
            state["monster_outgoing_mult"] = min(float(state.get("monster_outgoing_mult", 1.0)), 0.82)
            state["monster_debuff_turns"] = max(int(state.get("monster_debuff_turns", 0)), 2)
            logs.append("🌑 Тьма руны сеет страх!")
        elif se == "blind":
            state["monster_outgoing_mult"] = min(float(state.get("monster_outgoing_mult", 1.0)), 0.75)
            state["monster_debuff_turns"] = max(int(state.get("monster_debuff_turns", 0)), 2)
            logs.append("✨ Вспышка руны ослепляет!")
        elif se == "slow":
            state["monster_outgoing_mult"] = min(float(state.get("monster_outgoing_mult", 1.0)), 0.78)
            state["monster_debuff_turns"] = max(int(state.get("monster_debuff_turns", 0)), 2)
            logs.append("🌿 Земля руны сковывает шаги!")
    return logs


def player_attack(state: dict[str, Any]) -> tuple[list[str], Outcome, int]:
    logs: list[str] = []
    st = _stats(state)
    luck = int(st["luck"])
    mods = _mods(state)

    elem_bonus = int(state.get("weapon_rune_bonus_pct", 0))
    _log_weapon_rune_elemental_once(state, elem_bonus, logs)

    dmg = formulas.physical_damage(
        int(st["str"]),
        player_weapon_attack_value(state),
        monster_armor_value(state),
        elemental_bonus_percent=elem_bonus,
    )
    crit = formulas.roll_crit(luck, crit_bonus_flat=float(mods.get("crit_bonus", 0.0)))
    if crit:
        dmg = int(dmg * formulas.crit_multiplier())
        cdm = int(state.get("rune_crit_damage_bonus_percent", 0))
        if cdm > 0:
            dmg = int(dmg * (1.0 + cdm / 100.0))
    dmg = _apply_weapon_mastery_to_damage(state, dmg)
    dmg = combo_apply_outgoing_damage(state, dmg, logs)
    if crit:
        logs.append(f"→ Ты нанёс 🗡️ {dmg} урона [КРИТ💥]")
    else:
        logs.append(f"→ Ты нанёс 🗡️ {dmg} урона")

    syn = str(state.get("rune_synergy_name") or "")
    if syn and not state.get("rune_syn_logged"):
        state["rune_syn_logged"] = True
        logs.append(f"🔗 Синергия рун: {syn}")

    logs.extend(_rune_status_proc_logs(state))

    _m(state)["hp"] = max(0, int(_m(state)["hp"]) - dmg)
    record_player_last_damage_to_monster(state, dmg)
    _mark_weapon_mastery_strike(state)
    if int(_m(state)["hp"]) <= 0:
        return logs, "win", dmg
    return logs, "continue", dmg


def player_skill(state: dict[str, Any], index: int) -> tuple[list[str], Outcome | None, int]:
    """
    Возвращает (логи, исход, урон_по_врагу) или (логи, None, 0) если навык не применён.
    Урон — только по веткам, наносящим HP-урон монстру (после всех множителей).
    """
    logs: list[str] = []
    class_key = state["class_key"]
    skills = skills_for_class(class_key)
    if index < 0 or index > 2:
        logs.append("Нет такого навыка.")
        return logs, None, 0

    sk: SkillDef = skills[index]
    cd = int(state["skill_cd"].get(str(index), 0))
    if cd > 0:
        logs.append(f"Навык на перезарядке ({cd} х.).")
        return logs, None, 0

    mp = int(state["player_mp"])
    if mp < sk.mp_cost:
        logs.append("Недостаточно MP.")
        return logs, None, 0

    state["player_mp"] = mp - sk.mp_cost
    state["skill_cd"][str(index)] = sk.cooldown

    st = _stats(state)
    mods = _mods(state)
    luck = int(st["luck"])

    if sk.effect_key == "heal":
        heal = int(state["player_hp_max"] * 0.25)
        state["player_hp"] = min(int(state["player_hp_max"]), int(state["player_hp"]) + heal)
        logs.append(f"{sk.name}: +{heal} HP.")
        return logs, "continue", 0

    if sk.effect_key == "block_next":
        state["player_block_next"] = True
        logs.append(f"{sk.name}: готов отразить следующий удар.")
        return logs, "continue", 0

    if sk.effect_key == "dodge_buff":
        state["player_temp_dodge"] = float(state.get("player_temp_dodge", 0.0)) + 0.18
        state["player_temp_dodge_turns"] = max(int(state.get("player_temp_dodge_turns", 0)), 3)
        logs.append(f"{sk.name}: +18% к шансу уклонения на 3 хода.")
        return logs, "continue", 0

    if sk.effect_key == "shield":
        absorb = max(14, int(int(state["player_hp_max"]) * 0.18))
        state["player_shield_hp"] = int(state.get("player_shield_hp", 0)) + absorb
        logs.append(f"{sk.name}: щит поглощает до {absorb} урона (накопительно).")
        return logs, "continue", 0

    if sk.effect_key == "smoke":
        state["monster_outgoing_mult"] = min(float(state.get("monster_outgoing_mult", 1.0)), 0.62)
        state["monster_debuff_turns"] = max(int(state.get("monster_debuff_turns", 0)), 3)
        logs.append(f"{sk.name}: враг бьёт слабее (~−38% урона, 3 х.).")
        return logs, "continue", 0

    if sk.effect_key == "fortify" and sk.power == 0:
        state["player_fortify_bonus"] = int(state.get("player_fortify_bonus", 0)) + 10
        state["player_fortify_turns"] = max(int(state.get("player_fortify_turns", 0)), 3)
        logs.append(f"{sk.name}: +10 к защите на 3 хода.")
        return logs, "continue", 0

    if sk.effect_key == "hot":
        effects.add_effect("player", state, "Тотем исцеления", "hot", 4, {"potency_percent": 5})
        logs.append(f"{sk.name}: восстановление HP в начале твоих ходов (4 х.).")
        return logs, "continue", 0

    if sk.effect_key == "shred_armor":
        state["monster_def_mod"] = int(state.get("monster_def_mod", 0)) + 3
        logs.append(f"{sk.name}: броня врага ослаблена.")

    if sk.power == 0:
        return logs, "continue", 0

    mdef = monster_armor_value(state)

    if sk.kind == "mag":
        base = formulas.magical_damage(
            int(st["int"]),
            max(2, player_weapon_attack_value(state) // 2),
            mdef,
            mag_bonus_percent=int(mods.get("mag_bonus_percent", 0)),
        )
        base = int(base * formulas.int_skill_mag_extra_scale(int(st["int"])))
    else:
        rb = int(state.get("weapon_rune_bonus_pct", 0))
        _log_weapon_rune_elemental_once(state, rb, logs)
        base = formulas.physical_damage(
            int(st["str"]),
            player_weapon_attack_value(state),
            mdef,
            elemental_bonus_percent=rb,
        )
        base = int(base * formulas.int_skill_phys_tuning_multiplier(int(st["int"])))

    dmg = int(base * sk.power) if sk.power else int(base)

    mon = _m(state)
    mhp, mmx = int(mon["hp"]), int(mon["max_hp"])
    if sk.effect_key == "backstab" and mmx > 0 and mhp / mmx > 0.70:
        dmg = int(dmg * 1.28)
        logs.append("В спину! Дополнительный урон.")
    if sk.effect_key == "low_hp_bonus":
        php = int(state["player_hp"]) / max(1, int(state["player_hp_max"]))
        if php < 0.42:
            dmg = int(dmg * 1.38)
            logs.append("Кровь усиливает ярость!")

    crit = formulas.roll_crit(luck, crit_bonus_flat=float(mods.get("crit_bonus", 0.0)))
    if crit:
        dmg = int(dmg * formulas.crit_multiplier())

    dmg = _apply_weapon_mastery_to_damage(state, dmg)
    dmg = combo_apply_outgoing_damage(state, dmg, logs)

    if sk.effect_key == "burn" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        effects.add_effect(
            "monster",
            state,
            "Поджог",
            "burn",
            3,
            {"potency_percent": 5},
        )
        logs.append("Враг горит!")
    if sk.effect_key == "freeze" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        state["monster_skip_next"] = True
        logs.append("Враг заледенел и пропустит ход!")
    if sk.effect_key == "paralyze" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        state["monster_skip_next"] = True
        logs.append("Паралич! Враг может пропустить ход.")
    if sk.effect_key == "stun" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        state["monster_skip_next"] = True
        logs.append("Оглушение! Враг пропустит ход.")
    if sk.effect_key == "root" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        state["monster_skip_next"] = True
        logs.append("Капкан! Враг пропустит ход.")
    if sk.effect_key == "slow" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        state["monster_outgoing_mult"] = min(float(state.get("monster_outgoing_mult", 1.0)), 0.78)
        state["monster_debuff_turns"] = max(int(state.get("monster_debuff_turns", 0)), 2)
        logs.append("Оковы: враг бьёт слабее (~−22% урона, 2 х.).")
    if sk.effect_key == "poison" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        effects.add_effect(
            "monster",
            state,
            "Яд",
            "poison",
            3,
            {"potency_percent": 3},
        )
        logs.append("Яд разъедает врага!")
    if sk.effect_key == "bleed" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        effects.add_effect(
            "monster",
            state,
            "Кровотечение",
            "bleed",
            3,
            {"potency_percent": 4},
        )
        logs.append("Кровотечение!")

    tag = "🔮" if sk.kind == "mag" else "🗡️"
    if crit:
        logs.append(f"{tag} {sk.name}: {dmg} урона [КРИТ💥]")
    else:
        logs.append(f"{tag} {sk.name}: {dmg} урона")

    mon["hp"] = max(0, mhp - dmg)
    record_player_last_damage_to_monster(state, dmg)
    _mark_weapon_mastery_strike(state)

    if sk.effect_key == "self_bleed" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        effects.add_effect("player", state, "Кровожадность", "bleed", 2, {"potency_percent": 2})
        logs.append("Ты ранишь себя в ярости…")

    if sk.effect_key == "drain":
        ch = sk.effect_chance if sk.effect_chance > 0 else 1.0
        if effects.roll_chance(ch):
            heal = max(1, int(dmg * 0.35))
            curp = int(state["player_hp"])
            mxp = int(state["player_hp_max"])
            state["player_hp"] = min(mxp, curp + heal)
            logs.append(f"↩️ Поглощение жизни: +{heal} HP.")

    if int(mon["hp"]) <= 0:
        return logs, "win", dmg
    return logs, "continue", dmg


def monster_turn(state: dict[str, Any]) -> tuple[list[str], Outcome]:
    logs: list[str] = []
    m = _m(state)
    tk = str(m.get("template_key", ""))

    logs.extend(monster_ai.update_monster_mode(state))
    logs.extend(monster_ai.sync_boss_phase(state))

    if state.get("monster_skip_next"):
        state["monster_skip_next"] = False
        logs.append("Враг пропускает ход.")
        state["monster_turn"] = int(state.get("monster_turn", 0)) + 1
        return logs, "continue"

    php = int(state["player_hp"]) / max(1, int(state["player_hp_max"]))
    if php > 0.80 and random.random() < 0.35:
        logs.append(f"💬 «{monster_ai.pick_provocation_taunt(m['name'], tk)}»")

    dodge_flat = float(_mods(state).get("dodge_bonus", 0.0)) + float(state.get("player_temp_dodge", 0.0))
    if formulas.roll_dodge(int(_stats(state)["dex"]), dodge_bonus_flat=dodge_flat):
        logs.append("🏃 Ты увернулся от атаки!")
        state["monster_turn"] = int(state.get("monster_turn", 0)) + 1
        return logs, "continue"

    action = monster_ai.decide_action(state)

    if action == "taunt_only":
        logs.append(f"💬 «{monster_ai.pick_taunt(m['name'], tk)}»")
        state["monster_turn"] = int(state.get("monster_turn", 0)) + 1
        return logs, "continue"

    if action == "fortify":
        state["monster_fortify_flat"] = 8
        state["monster_fortify_turns"] = 3
        logs.append(f"🛡️ {m.get('emoji', '👹')} Укрепление! Броня +8 на 3 хода.")
        state["monster_turn"] = int(state.get("monster_turn", 0)) + 1
        return logs, "continue"

    mult = monster_ai.monster_damage_multiplier(state)
    atk = int(m["atk"])
    out_m = float(state.get("monster_outgoing_mult", 1.0))
    base = int(atk * random.uniform(0.9, 1.1) * mult * out_m)
    defense = player_defense_value(state)

    cd = int(state.get("monster_special_cd", 0))
    is_special = action == "special" and cd == 0
    if is_special:
        base = int(base * 1.5)
        logs.append(f"Враг применил {monster_ai.pick_skill_line(state, special=True)}!")
        state["monster_special_cd"] = 2
    else:
        logs.append(f"Враг: {monster_ai.pick_skill_line(state, special=False)}.")

    if state.get("player_block_next"):
        state["player_block_next"] = False
        counter = max(1, int(base * 0.5))
        m["hp"] = max(0, int(m["hp"]) - counter)
        record_player_last_damage_to_monster(state, counter)
        logs.append(f"🛡️ Блок! Контрудар: −{counter} HP врагу.")
        if int(m["hp"]) <= 0:
            state["monster_turn"] = int(state.get("monster_turn", 0)) + 1
            return logs, "win"

    dmg = max(1, base - defense)
    pre_php = int(state["player_hp"])
    shield = int(state.get("player_shield_hp", 0))
    if shield > 0:
        absorbed = min(shield, dmg)
        state["player_shield_hp"] = shield - absorbed
        dmg -= absorbed
        if absorbed > 0:
            logs.append(f"🛡️ Щит поглотил {absorbed} урона.")
    state["player_hp"] = max(0, int(state["player_hp"]) - dmg)
    if int(state["player_hp"]) < pre_php:
        combo_break_on_player_hurt(state)
    if dmg > 0:
        logs.append(f"→ {m.get('emoji', '👹')} Удар по тебе: −{dmg} HP")
        record_monster_last_damage_to_player(state, dmg)

    state["monster_turn"] = int(state.get("monster_turn", 0)) + 1

    if int(state["player_hp"]) <= 0:
        return logs, "lose"
    return logs, "continue"


def opening_taunt(state: dict[str, Any]) -> str:
    return monster_ai.opening_taunt_line(state)


def end_round_tick(state: dict[str, Any]) -> list[str]:
    """Конец раунда: длительности эффектов и ослабление брони."""
    logs: list[str] = []
    logs.extend(effects.tick_effect_turns("player", state))
    logs.extend(effects.tick_effect_turns("monster", state))
    if int(state.get("monster_def_mod", 0)) > 0:
        state["monster_def_mod"] = max(0, int(state["monster_def_mod"]) - 1)
    ft = int(state.get("monster_fortify_turns", 0))
    if ft > 0:
        state["monster_fortify_turns"] = ft - 1
        if int(state["monster_fortify_turns"]) <= 0:
            state["monster_fortify_flat"] = 0
            logs.append("🛡️ Укрепление врага спало.")

    td = int(state.get("player_temp_dodge_turns", 0))
    if td > 0:
        state["player_temp_dodge_turns"] = td - 1
        if int(state["player_temp_dodge_turns"]) <= 0:
            state["player_temp_dodge"] = 0.0
            logs.append("💨 Бонус к уклонению спал.")

    pft = int(state.get("player_fortify_turns", 0))
    if pft > 0:
        state["player_fortify_turns"] = pft - 1
        if int(state["player_fortify_turns"]) <= 0:
            state["player_fortify_bonus"] = 0
            logs.append("🛡️ Твоё укрепление спало.")

    md = int(state.get("monster_debuff_turns", 0))
    if md > 0:
        state["monster_debuff_turns"] = md - 1
        if int(state["monster_debuff_turns"]) <= 0:
            state["monster_outgoing_mult"] = 1.0
            logs.append("🌫️ Ослабление атаки врага спало.")

    return logs
