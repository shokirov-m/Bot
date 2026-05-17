"""Временная печать 18+ взаимодействий с наёмницами в покоях."""

from __future__ import annotations

# Снять печать: MERC_ADULT_CONTENT_SEAL_ENABLED = False
MERC_ADULT_CONTENT_SEAL_ENABLED = True


def merc_adult_content_sealed() -> bool:
    return bool(MERC_ADULT_CONTENT_SEAL_ENABLED)


def merc_adult_seal_alert_text() -> str:
    return (
        "🔒 18+ взаимодействия с наёмницами временно закрыты. "
        "Раздел скоро откроется."
    )
