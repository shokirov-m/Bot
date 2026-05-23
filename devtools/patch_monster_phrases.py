"""Shorten and brighten monster phrases in monsters_catalog.json."""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "content" / "data" / "monsters_catalog.json"

OPENINGS = [
    "Слышишь? Это уже слишком близко…",
    "Ещё шаг — и пожалеешь.",
    "Здесь я хозяин. Ты — добыча.",
    "Пахнет страхом. Отлично.",
]
TAUNTS = [
    "Слабак!",
    "Ты дрожишь?",
    "Ещё разок — и конец.",
]
VICTORY = [
    "Как и ожидалось.",
    "Следующий?",
    "Пыль на ветру.",
]
DEFEAT = [
    "Невозможно…",
    "Тьма… забирает…",
    "Я… вернусь…",
]


def _short(text: str, max_len: int = 78) -> str:
    t = " ".join((text or "").split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _pick(pool: list[str], seed: str) -> str:
    rng = random.Random(seed)
    return rng.choice(pool)


def main() -> None:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    monsters = data.get("monsters") or {}
    for key, row in monsters.items():
        if not isinstance(row, dict):
            continue
        name = str(row.get("display_name") or row.get("name") or key).strip()
        row["opening_phrase"] = _short(
            row.get("opening_phrase")
            or _pick(OPENINGS, key + ":open")
            or f"{name} выходит из тени.",
        )
        row["victory_phrase"] = _short(
            row.get("victory_phrase") or _pick(VICTORY, key + ":win"),
        )
        row["defeat_phrase"] = _short(
            row.get("defeat_phrase") or _pick(DEFEAT, key + ":lose"),
        )
        phrases = list(row.get("phrases") or [])
        if len(phrases) > 3:
            phrases = phrases[:3]
        while len(phrases) < 2:
            phrases.append(_pick(TAUNTS, key + f":t{len(phrases)}"))
        row["phrases"] = [_short(p, 72) for p in phrases]
        blurb = str(row.get("blurb") or "").strip()
        if blurb:
            row["blurb"] = _short(blurb, 90)
    CATALOG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("patched", len(monsters), "monsters")


if __name__ == "__main__":
    main()
