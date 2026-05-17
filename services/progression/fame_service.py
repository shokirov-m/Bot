"""
Система Славы (Fame/Слава).

Слава — универсальная характеристика репутации персонажа, начисляемая
за выполнение заданий от НПС, цепочек заданий в кузнице и таверне.

Хранится в meta_progress['fame'] как целое число.
В будущем используется для открытия контента, диалогов, магазинов и т.д.
"""

from __future__ import annotations

from loguru import logger
from db.models.character import Character

_FAME_KEY = "fame"

# ── Ранги славы ────────────────────────────────────────────────────────────────
_RANKS: list[tuple[int, str, str]] = [
    (0,    "🔘 Безымянный",       "Тебя ещё никто не знает."),
    (25,   "⚪ Знакомый",         "Кое-кто слышал твоё имя."),
    (75,   "🟢 Известный",        "Торговцы узнают тебя в лицо."),
    (150,  "🔵 Уважаемый",        "Стражники кивают тебе при встрече."),
    (300,  "🟣 Прославленный",    "Барды слагают песни о твоих подвигах."),
    (600,  "🟡 Легендарный",      "Имя твоё произносят с трепетом."),
    (1200, "🟠 Великий герой",    "Целые города чтят твои деяния."),
    (2500, "🔴 Непобедимый",      "Башня сама склоняется перед тобой."),
]


def get_fame(character: Character) -> int:
    """Текущее количество Славы персонажа."""
    return int((character.meta_progress or {}).get(_FAME_KEY, 0))


def add_fame(character: Character, amount: int) -> int:
    """
    Добавить amount единиц Славы. Возвращает новое значение.
    amount должен быть > 0, иначе игнорируется.
    """
    if amount <= 0:
        return get_fame(character)
    meta = dict(character.meta_progress or {})
    new_val = int(meta.get(_FAME_KEY, 0)) + amount
    meta[_FAME_KEY] = new_val
    character.meta_progress = meta
    try:
        from services.progression.fame_bonuses import grant_fame_600_rewards_if_needed

        grant_fame_600_rewards_if_needed(character)
    except Exception:
        logger.exception(f"Ошибка при выдаче наград за славу 600 для героя {character.id}")
    return new_val


def fame_rank(fame: int) -> tuple[str, str]:
    """Возвращает (название_ранга, описание) для заданного количества Славы."""
    rank_name, rank_desc = _RANKS[0][1], _RANKS[0][2]
    for threshold, name, desc in _RANKS:
        if fame >= threshold:
            rank_name, rank_desc = name, desc
        else:
            break
    return rank_name, rank_desc


def fame_progress_to_next(fame: int) -> str:
    """Прогресс-строка до следующего ранга (или 'максимум')."""
    for i, (threshold, name, _) in enumerate(_RANKS):
        if fame < threshold:
            prev = _RANKS[i - 1][0] if i > 0 else 0
            needed = threshold - fame
            total = threshold - prev
            filled = min(10, int((fame - prev) * 10 / max(1, total)))
            bar = "🟨" * filled + "⬜" * (10 - filled)
            return f"[{bar}] {fame - prev}/{total} → {name}"
    return "🏆 Максимальный ранг достигнут!"


def format_fame_html(character: Character) -> str:
    """HTML-блок для отображения Славы в профиле."""
    fame = get_fame(character)
    rank_name, rank_desc = fame_rank(fame)
    progress = fame_progress_to_next(fame)
    extra = ""
    try:
        from services.progression.fame_bonuses import title_and_frame_600_display

        row = title_and_frame_600_display(character)
        if row:
            title, frame = row
            extra = f"\n🎖 <b>Титул славы:</b> {title}\n🖼 <b>Рамка профиля:</b> {frame}"
    except Exception:
        logger.exception(f"Ошибка при выдаче наград за славу 600 для героя {character.id}")
    return (
        f"⭐ <b>Слава:</b> {fame}  {rank_name}\n"
        f"<i>{rank_desc}</i>\n"
        f"{progress}{extra}"
    )
