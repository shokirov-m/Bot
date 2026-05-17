"""
Единые пути к контенту (этап A).

Физически:
  content/assets/     — PNG, UI, game_art (бывший tower_bot/assets/)
  content/data/       — статика (balance, items, monsters_catalog.json); game/data — junction
  content/data/catalogs/ — JSON-каталоги (archetypes, coliseum, cities…)

Старый путь ``tower_bot/assets/`` — junction на ``content/assets/`` (Windows).
"""

from __future__ import annotations

from pathlib import Path

_TOWER_BOT_ROOT = Path(__file__).resolve().parents[2]
_CONTENT_ROOT = _TOWER_BOT_ROOT / "content"
_LEGACY_ASSETS = _TOWER_BOT_ROOT / "assets"
_LEGACY_DATA = _TOWER_BOT_ROOT / "game" / "data"


def tower_bot_root() -> Path:
    return _TOWER_BOT_ROOT


def content_root() -> Path:
    return _CONTENT_ROOT


def assets_root() -> Path:
    """Корень всех бинарных ассетов (PNG и т.д.)."""
    canonical = _CONTENT_ROOT / "assets"
    if canonical.is_dir():
        return canonical
    if _LEGACY_ASSETS.is_dir():
        return _LEGACY_ASSETS
    return canonical


def data_root() -> Path:
    """Статические данные (balance, items, monsters JSON). Этап B: только content/data."""
    canonical = _CONTENT_ROOT / "data"
    if canonical.is_dir():
        return canonical
    return _LEGACY_DATA


def catalogs_root() -> Path:
    """JSON-каталоги: ``content/data/catalogs/``."""
    return data_root() / "catalogs"


def images_root() -> Path:
    return assets_root() / "images"


def items_root() -> Path:
    return assets_root() / "items"


def monsters_root() -> Path:
    return assets_root() / "monsters"


def game_art_root() -> Path:
    return assets_root() / "game_art"


def ui_assets_root() -> Path:
    return assets_root() / "ui"


def rel_assets(*parts: str) -> str:
    """Относительный путь от корня tower_bot для Telegram ``image_url`` / FSInputFile."""
    p = assets_root().joinpath(*parts)
    try:
        rel = p.relative_to(_TOWER_BOT_ROOT)
    except ValueError:
        rel = Path("content") / "assets" / Path(*parts)
    return rel.as_posix()
