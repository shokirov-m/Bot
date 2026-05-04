#!/usr/bin/env python3
"""Патч recipes_data. Запуск из tower_bot: python tools/patch_named_materials.py"""
from __future__ import annotations
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RECIPES_PATH = ROOT / "game" / "crafting" / "recipes_data.py"
# ... (file continues - use run to create)
