from __future__ import annotations

"""
Generate PNG placeholder assets for mercenary portraits + quarters actions.

Run locally:
  python generate_merc_placeholder_pngs.py

It creates files under:
  game/assets/home/merc_quarters/
"""

from pathlib import Path


def _require_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont  # noqa: F401

        return Image, ImageDraw, ImageFont
    except Exception as e:  # pragma: no cover
        raise SystemExit(
            "Pillow (PIL) is required. Install it with:\n"
            "  pip install pillow\n\n"
            f"Error: {e}"
        )


def _font(ImageFont):
    for name, size in (("arial.ttf", 56), ("arial.ttf", 40), ("arial.ttf", 26)):
        try:
            yield ImageFont.truetype(name, size)
        except Exception:
            yield ImageFont.load_default()


def _make_png(
    Image,
    ImageDraw,
    *,
    out: Path,
    size: tuple[int, int],
    bg: tuple[int, int, int],
    header: str,
    body: str,
    footer: str,
    font_big,
    font_mid,
    font_small,
) -> None:
    w, h = size
    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)

    d.rounded_rectangle((16, 16, w - 16, h - 16), radius=26, outline=(255, 255, 255), width=4)
    d.rounded_rectangle((34, 34, w - 34, 130), radius=18, fill=(0, 0, 0))
    d.text((52, 58), header, fill=(255, 255, 255), font=font_mid)

    d.text((52, 170), body, fill=(255, 255, 255), font=font_big)

    d.rounded_rectangle((34, h - 120, w - 34, h - 34), radius=18, fill=(0, 0, 0))
    d.text((52, h - 98), footer, fill=(255, 255, 255), font=font_small)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="PNG")


def main() -> None:
    Image, ImageDraw, ImageFont = _require_pillow()
    font_big, font_mid, font_small = tuple(_font(ImageFont))

    root = Path("game/assets/home/merc_quarters")
    portraits = root / "portraits"
    romance = root / "romance"

    mercs = {
        "elf_emerald": {"title": "Эльфика\n(изумрудные волосы)", "color": (20, 120, 90)},
        "vampiress": {"title": "Вампирша", "color": (90, 15, 25)},
        "wolfgirl": {"title": "Волкодевушка", "color": (130, 95, 35)},
    }

    # Must match `game/data/merc_quarters_romance_ru.json`
    assets = {
        "hold_hands": ["hold_hands_1.png", "hold_hands_2.png", "hold_hands_3.png", "hold_hands_4.png"],
        "kiss": ["kiss_1.png", "kiss_2.png", "kiss_3.png", "kiss_4.png"],
        "bath": ["bath_1.png", "bath_2.png", "bath_3.png", "bath_4.png"],
        "talk": ["talk_1.png", "talk_2.png", "talk_3.png", "talk_4.png"],
    }

    portraits.mkdir(parents=True, exist_ok=True)
    for mk in mercs:
        (romance / mk).mkdir(parents=True, exist_ok=True)

    for mk, meta in mercs.items():
        _make_png(
            Image,
            ImageDraw,
            out=portraits / f"{mk}.png",
            size=(768, 768),
            bg=meta["color"],
            header="Портрет наёмницы",
            body=meta["title"],
            footer=f"key: {mk}",
            font_big=font_big,
            font_mid=font_mid,
            font_small=font_small,
        )

    for mk, meta in mercs.items():
        for action, files in assets.items():
            for fn in files:
                _make_png(
                    Image,
                    ImageDraw,
                    out=romance / mk / fn,
                    size=(960, 540),
                    bg=meta["color"],
                    header="Покои · действие",
                    body=f"{meta['title']}\n{action}",
                    footer=fn,
                    font_big=font_big,
                    font_mid=font_mid,
                    font_small=font_small,
                )

    print("OK. Generated placeholder PNGs in:", root.as_posix())


if __name__ == "__main__":
    main()

