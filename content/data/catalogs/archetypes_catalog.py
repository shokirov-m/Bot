"""Загрузка классов, навыков и деревьев из JSON-каталогов."""

from __future__ import annotations

from game.archetypes.models import Archetype, PassiveV2, SkillTreeNode, SkillV2
from game.data.catalogs._loader import load_catalog_json, entries_map


def _skill_from_row(key: str, row: dict) -> SkillV2:
    return SkillV2(
        key,
        str(row.get("name_ru", key)),
        str(row.get("description_ru", "")),
        int(row.get("mp_cost", 0)),
        int(row.get("cooldown", 0)),
        float(row.get("power_mult", 1.0)),
        str(row.get("kind", "phys")),  # type: ignore[arg-type]
        row.get("effect_key"),
        float(row.get("effect_chance", 0.0)),
        int(row.get("required_level", 1)),
    )


def _passive_from_row(key: str, row: dict) -> PassiveV2:
    mods = row.get("modifiers")
    if not isinstance(mods, dict):
        mods = {}
    clean: dict[str, float | int] = {}
    for mk, mv in mods.items():
        try:
            clean[str(mk)] = float(mv) if isinstance(mv, float) else int(mv)
        except (TypeError, ValueError):
            continue
    return PassiveV2(
        key,
        str(row.get("name_ru", key)),
        str(row.get("description_ru", "")),
        clean,
    )


def catalog_skills() -> dict[str, SkillV2] | None:
    ent = entries_map(load_catalog_json("archetypes_skills.json"))
    if not ent:
        return None
    return {k: _skill_from_row(k, v) for k, v in ent.items()}


def catalog_passives() -> dict[str, PassiveV2] | None:
    ent = entries_map(load_catalog_json("archetypes_passives.json"))
    if not ent:
        return None
    return {k: _passive_from_row(k, v) for k, v in ent.items()}


def catalog_archetypes(passives: dict[str, PassiveV2]) -> dict[str, Archetype] | None:
    ent = entries_map(load_catalog_json("archetypes_classes.json"))
    if not ent:
        return None
    out: dict[str, Archetype] = {}
    for k, row in ent.items():
        pkeys = row.get("passives") or []
        plist = tuple(passives[pk] for pk in pkeys if pk in passives)
        bs = row.get("base_stats")
        req = row.get("requirements")
        out[k] = Archetype(
            k,
            str(row.get("name_ru", k)),
            str(row.get("emoji", "❓")),
            int(row.get("tier", 0)),
            str(row.get("description_ru", "")),
            dict(bs) if isinstance(bs, dict) else {},
            plist,
            tuple(str(s) for s in (row.get("skills") or [])),
            float(row.get("hp_multiplier", 1.0)),
            float(row.get("mp_multiplier", 1.0)),
            {str(rk): int(rv) for rk, rv in req.items()} if isinstance(req, dict) else {},
        )
    return out if out else None


def catalog_trees() -> dict[str, dict[str, SkillTreeNode]] | None:
    raw = load_catalog_json("archetypes_skill_trees.json")
    trees = raw.get("trees")
    if not isinstance(trees, dict) or not trees:
        return None
    out: dict[str, dict[str, SkillTreeNode]] = {}
    for arch, nodes in trees.items():
        if not isinstance(nodes, dict):
            continue
        arch_nodes: dict[str, SkillTreeNode] = {}
        for nk, row in nodes.items():
            if not isinstance(row, dict):
                continue
            val = row.get("value")
            if isinstance(val, dict):
                val_out: str | dict[str, float | int] = {
                    str(mk): float(mv) if isinstance(mv, float) else int(mv)
                    for mk, mv in val.items()
                }
            else:
                val_out = str(val or "")
            parents = row.get("parent_keys") or []
            arch_nodes[str(nk)] = SkillTreeNode(
                str(nk),
                str(row.get("name_ru", nk)),
                str(row.get("description_ru", "")),
                str(row.get("node_type", "stat_boost")),  # type: ignore[arg-type]
                val_out,
                int(row.get("cost_sp", 1)),
                tuple(str(p) for p in parents),
                int(row.get("required_tier", 1)),
            )
        if arch_nodes:
            out[str(arch)] = arch_nodes
    return out if out else None
