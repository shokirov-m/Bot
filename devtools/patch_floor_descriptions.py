"""One-off: playful zone descriptions in game/data/floors.py."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "game" / "data" / "floors.py"
text = p.read_text(encoding="utf-8")

ZONES: dict[str, str] = {
    "forest_beginnings": (
        "🌿 Тихий лес у подножия башни. Здесь учатся драться — враги слабее, но коварны. "
        "Элита опаснее обычных."
    ),
    "rotten_swamps": (
        "🐸 Туман −5 HP перед боем, пиявки после боя. Ищи лагерь и не спеши с элитой."
    ),
    "shadow_caves": (
        "🕳️ Тьма живёт своей жизнью: тени бьют из засады, эхо путает шаги."
    ),
    "icy_peaks": "❄️ Мороз и йети давят массой. Лёд слабит уклонение — зато награды сочнее.",
    "desert_oblivion": "🏜️ Жар и миражи: враги бьют резко, песок крадёт выносливость.",
    "volcanic_ruins": "🌋 Пепел в лёгких, лава под ногами. Огненные твари горят ярче с каждым этажом.",
    "blood_spire": (
        "🩸 Вампирская сага: охота, ритуалы, оборона. Смерть сбрасывает фазу — играй осторожно."
    ),
    "chaos_abyss": "🌀 Реальность ломается: демоны, зеркала, крики. Здесь нет «обычных» боёв.",
    "eternity_hall": (
        "✨ Зал вечного света — вершина карты. Стражи проверяют всё, чему ты научился."
    ),
}

for key, desc in ZONES.items():
    marker = f'"key": "{key}"'
    idx = text.find(marker)
    if idx < 0:
        raise SystemExit(f"missing key {key}")
    didx = text.find('"description":', idx)
    if didx < 0 or didx > idx + 600:
        raise SystemExit(f"no description for {key}")
    start = didx + len('"description":')
    rest = text[start:].lstrip()
    if rest.startswith("("):
        depth = 0
        end_rel = 0
        for i, ch in enumerate(rest):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end_rel = i + 1
                    break
        end = start + end_rel
    elif rest.startswith('"'):
        end = start + rest.find('",') + 2
    else:
        raise SystemExit(f"unknown description format for {key}")
    text = text[:didx] + f'"description": "{desc}"' + text[end:]

p.write_text(text, encoding="utf-8")
print("OK:", p)
