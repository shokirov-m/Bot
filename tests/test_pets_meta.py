"""Нормализация meta_progress для питомцев."""

from __future__ import annotations

import json
from types import SimpleNamespace

from game.characters import pets as pets_mod


def test_owned_keys_from_json_string_nested() -> None:
    inner = {"owned": '["pet_moss_sprite"]', "active": "pet_moss_sprite"}
    ch = SimpleNamespace(meta_progress={"pets_v1": json.dumps(inner)})
    assert pets_mod.owned_keys(ch) == ["pet_moss_sprite"]
    assert pets_mod.repair_pet_meta_if_needed(ch) is True
    assert isinstance(ch.meta_progress["pets_v1"], dict)
    assert ch.meta_progress["pets_v1"]["owned"] == ["pet_moss_sprite"]


def test_repair_active_not_in_owned() -> None:
    ch = SimpleNamespace(
        meta_progress={
            "pets_v1": {"owned": ["pet_cinder_fox"], "active": "pet_moss_sprite"},
        },
    )
    assert pets_mod.repair_pet_meta_if_needed(ch) is True
    assert ch.meta_progress["pets_v1"]["active"] == "pet_cinder_fox"
