"""Tests for screen_style and spawn labels."""
from __future__ import annotations
from game.archetypes.data import SKILLS, skill_emoji_for_v2
from game.enemies.floors.spawns import FloorMonsterSpawn, MonsterTemplate
from utils.telegram.screen_style import floor_header_html, quote_line, render_screen, truncate_button_label

def test_render_screen_joins_blocks() -> None:
    out = render_screen("test", "line2")
    assert "line2" in out

def test_all_skills_have_emoji() -> None:
    for key, sk in SKILLS.items():
        assert skill_emoji_for_v2(sk), key

def test_spawn_display_name_full() -> None:
    tpl = MonsterTemplate("wolf", "Лесной волк альфа", "🐺", "earth", "")
    sp = FloorMonsterSpawn("0", tpl, False, False, False)
    assert "Лесной волк альфа" in sp.display_name
