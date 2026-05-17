"""
Портреты героя при регистрации: 3 мужских и 3 женских PNG в assets/images/profile/.
Ключи: male_1..male_3, female_1..female_3 — подменяй файлы своими картинками.
"""

from __future__ import annotations

from pathlib import Path

from db.models.character import Character
from game.core.paths import images_root

_ROOT = images_root() / "profile"

PORTRAIT_ORDER: tuple[str, ...] = (
    "male_1",
    "male_2",
    "male_3",
    "female_1",
    "female_2",
    "female_3",
)

META_PORTRAIT_KEY = "portrait_key"
# male / female — зафиксировано при регистрации (для гардероба / стартовых трёх обликов)
META_REG_GENDER = "reg_gender"

GENDER_MALE = "male"
GENDER_FEMALE = "female"


def portrait_keys_for_gender(gender: str) -> tuple[str, str, str]:
    """Три ключа портретов для выбранного пола регистрации."""
    g = (gender or "").strip().lower()
    if g == GENDER_FEMALE:
        return ("female_1", "female_2", "female_3")
    return ("male_1", "male_2", "male_3")


def portrait_paths_for_gender_album(gender: str) -> list[Path]:
    """До трёх путей PNG по порядку 1–3 для альбома / одного фото."""
    out: list[Path] = []
    for k in portrait_keys_for_gender(gender):
        p = portrait_path_if_exists(k)
        if p is not None:
            out.append(p)
    return out


def portrait_key_from_gender_slot(gender: str, slot: int) -> str | None:
    """Кнопка 1–3 → male_N / female_N."""
    if slot < 1 or slot > 3:
        return None
    keys = portrait_keys_for_gender(gender)
    return keys[slot - 1]


def portrait_asset_path(key: str) -> Path:
    return _ROOT / f"{key}.png"


def portrait_path_if_exists(key: str) -> Path | None:
    p = portrait_asset_path(key)
    return p if p.is_file() else None


def ordered_portrait_paths_for_album() -> list[Path]:
    """Пути по порядку альбома (1–3 муж., 4–6 жен.)."""
    out: list[Path] = []
    for k in PORTRAIT_ORDER:
        p = portrait_path_if_exists(k)
        if p is not None:
            out.append(p)
    return out


def portrait_key_from_slot(slot: int) -> str | None:
    """slot 1..6 → ключ файла."""
    if slot < 1 or slot > 6:
        return None
    return PORTRAIT_ORDER[slot - 1]


# Отображаемые названия (без технических ключей и путей к файлам).
_PORTRAIT_TITLE_RU: dict[str, str] = {
    "male_1":   "🗡️ Клинок Бездны",
    "male_2":   "🔥 Воин Пламени",
    "male_3":   "🌑 Охотник Теней",
    "female_1": "🌙 Лунная Ведьма",
    "female_2": "🌸 Алый Цветок",
    "female_3": "💫 Дева Звёзд",
    "noble_1":  "👑 Владыка Башни",
    "arcane_1": "⭐ Хранитель Архива",
}

_PORTRAIT_BLURB_RU: dict[str, str] = {
    "male_1":   "Молчаливый страж, прошедший сотни этажей.",
    "male_2":   "Боец, закалённый огнём подземелий.",
    "male_3":   "Следопыт, растворяющийся во мраке башни.",
    "female_1": "Колдунья, черпающая силу из ночи.",
    "female_2": "Воительница с лепестком на клинке.",
    "female_3": "Мистик, видящий судьбы в звёздах.",
    "noble_1":  "Аристократ, покоривший вершины Башни.",
    "arcane_1": "Хранитель запретных знаний архивов.",
}


def portrait_title_ru(key: str) -> str:
    """Краткое русское имя облика для меню и превью."""
    k = str(key or "").strip()
    if not k:
        return "Облик"
    return _PORTRAIT_TITLE_RU.get(k, "✨ Особый облик")


def portrait_blurb_ru(key: str) -> str:
    """Короткое описание облика."""
    k = str(key or "").strip()
    return _PORTRAIT_BLURB_RU.get(k, "Редкий облик для профиля героя.")


def portrait_label_ru(key: str) -> str:
    """Синоним для подписей кнопок и списков гардероба."""
    return portrait_title_ru(key)


def portrait_path_for_character(character: Character) -> Path | None:
    """PNG портрета из meta_progress, если файл есть."""
    mp = character.meta_progress or {}
    pk = mp.get(META_PORTRAIT_KEY)
    if not isinstance(pk, str) or not pk.strip():
        return None
    return portrait_path_if_exists(pk.strip())
