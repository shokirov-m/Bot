"""Загрузка бойцов колизея из coliseum_fighters.json."""

from __future__ import annotations

from typing import Any

from game.enemies.coliseum.fighters import ColiseumFighter, SpecialId
from game.data.catalogs._loader import load_catalog_json


def catalog_fighters() -> tuple[ColiseumFighter, ...] | None:
    raw = load_catalog_json("coliseum_fighters.json")
    rows = raw.get("fighters")
    if not isinstance(rows, list) or not rows:
        return None
    out: list[ColiseumFighter] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            fid = int(row["id"])
        except (KeyError, TypeError, ValueError):
            continue
        spec = str(row.get("special", "none"))
        if spec not in (
            "none",
            "blind_2",
            "fear_30",
            "sleep_first",
            "monster_evasion_30",
            "gust_20",
            "aid_barrier",
            "mulan_pet",
            "wukong_rage",
            "loki_illusion",
            "fenrir_pet",
            "kronos_skip",
            "zeus_bolt",
        ):
            spec = "none"
        try:
            acc_raw = row.get("accuracy", None)
            eva_raw = row.get("evasion", None)
            acc_v = float(acc_raw) if acc_raw is not None else None
            eva_v = float(eva_raw) if eva_raw is not None else None
        except (TypeError, ValueError):
            acc_v, eva_v = None, None
        out.append(
            ColiseumFighter(
                id=fid,
                name=str(row.get("name", f"Боец {fid}")),
                phrase=str(row.get("phrase", "")),
                victory_quote=str(row.get("victory_quote", "")),
                hp=int(row.get("hp", 100)),
                atk=int(row.get("atk", 10)),
                defense=int(row.get("defense", 0)),
                exp_reward=int(row.get("exp_reward", 10)),
                gold_reward=int(row.get("gold_reward", 10)),
                required_level=int(row.get("required_level", 1)),
                element_tz=str(row.get("element_tz", "none")),
                is_champion=bool(row.get("is_champion", fid % 10 == 0)),
                special=spec,  # type: ignore[arg-type]
                loot_id=str(row.get("loot_id", f"loot_{fid}")),
                accuracy=acc_v,
                evasion=eva_v,
            ),
        )
    return tuple(sorted(out, key=lambda f: f.id)) if out else None


def catalog_meta() -> dict[str, Any]:
    raw = load_catalog_json("coliseum_fighters.json")
    return {
        "template_key": raw.get("template_key"),
        "enemy_atk_mult": raw.get("enemy_atk_mult"),
        "element_map": raw.get("element_map"),
        "loot": raw.get("loot"),
    }
