"""
Генерация цветных PNG-заглушек для assets/items (только stdlib).
Собирает имена файлов из вызовов item_gear_png("...") в game/ и из списка каталога.

Запуск из каталога tower_bot:
  python -m scripts.generate_item_placeholder_pngs
"""

from __future__ import annotations

import hashlib
import re
import struct
import zlib
from pathlib import Path

W = 128
H = 128


def _png_rgb(w: int, h: int, rows: list[bytes]) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + row for row in rows)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def _color_for_stem(stem: str) -> tuple[int, int, int]:
    h = hashlib.sha256(stem.encode("utf-8")).digest()
    return int(h[0]), int(h[1]), int(h[2])


def write_placeholder(path: Path, stem: str) -> None:
    r0, g0, b0 = _color_for_stem(stem)
    r1, g1, b1 = max(0, r0 - 55), max(0, g0 - 55), max(0, b0 - 55)
    rows: list[bytes] = []
    for y in range(H):
        t = y / max(H - 1, 1)
        r = int(r0 + (r1 - r0) * t)
        g = int(g0 + (g1 - g0) * t)
        b = int(b0 + (b1 - b0) * t)
        rows.append(bytes([r, g, b]) * W)
    path.write_bytes(_png_rgb(W, H, rows))


def all_stems() -> list[str]:
    s: list[str] = []
    for prefix in (
        "catalog_armor",
        "catalog_pants",
        "catalog_helmet",
        "catalog_gloves",
        "catalog_ring",
        "catalog_amulet",
        "catalog_shield",
        "catalog_grimoire",
        "catalog_wpn_main",
        "catalog_wpn_off",
        "catalog_wpn_2h",
    ):
        s.extend(f"{prefix}_{i:02d}" for i in range(1, 9))
    s.extend(
        [
            "placeholder_item",
            "loot_elixir_flat",
            "loot_mp_flat",
            "loot_pct_hp",
            "loot_gloves",
            "loot_ring",
            "loot_trophy",
            "loot_weapon_blade",
            "loot_weapon_staff",
            "loot_moss_armor",
            "loot_cap",
            "loot_charm_amulet",
            "loot_rare_edge",
            "elite_weapon",
            "elite_armor",
            "elite_helm",
            "elite_elixir",
            "elite_ether",
            "mini_weapon",
            "mini_armor",
            "mini_helm",
            "mini_gloves",
            "mini_bundle",
            "major_weapon",
            "major_armor",
            "major_amulet",
            "major_ring",
            "major_chest",
            "shop_vita",
            "shop_ether",
            "shop_ration",
            "shop_antidote",
            "shop_f3_ring",
            "shop_f3_gloves",
            "shop_f3_amulet",
            "starter_bread",
            "starter_pants",
            "starter_offhand_dagger",
            "starter_wpn_wanderer",
            "starter_wpn_star_touched",
            "starter_wpn_tower_reaper",
            "starter_wpn_warrior",
            "starter_wpn_mage",
            "starter_wpn_archer",
            "starter_wpn_priest",
            "starter_wpn_assassin",
            "starter_wpn_berserker",
            "starter_wpn_necromancer",
            "starter_wpn_warden",
            "starter_wpn_shaman",
            "starter_wpn_hunter",
            "starter_wpn_default",
            "promo_armor_gift",
            "promo_amulet_first",
            "referral_gloves",
            "referral_ring",
            "referral_epic_necklace",
            "secret_armor_chain",
            "secret_helm_wanderer",
            "secret_gloves_leather",
            "secret_pants_wanderer",
            "secret_amulet_shard",
            "secret_ring_tower",
            "secret_ring_messenger",
            "secret_amulet_messenger",
            "secret_ring_green",
            "secret_gloves_runic",
            "secret_helm_slayer",
            "secret_amulet_darkness",
            "secret_helm_crown_low",
        ]
    )
    for k in ("armor", "pants", "helmet", "gloves", "ring", "amulet"):
        s.append(f"proc_secret_{k}")
    return s


def stems_from_sources(game_dir: Path) -> set[str]:
    pat = re.compile(r'item_gear_png\(\s*"([^"]+)"\s*\)')
    found: set[str] = set()
    for py in game_dir.rglob("*.py"):
        try:
            text = py.read_text(encoding="utf-8")
        except OSError:
            continue
        found.update(pat.findall(text))
    return found


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    stems = sorted(set(all_stems()) | stems_from_sources(root / "game"))
    out_dir = root / "assets" / "items"
    out_dir.mkdir(parents=True, exist_ok=True)
    for stem in stems:
        p = out_dir / f"{stem}.png"
        write_placeholder(p, stem)
        print(p.name)
    img_dir = root / "assets" / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    menu_p = img_dir / "menu_hub.png"
    write_placeholder(menu_p, "menu_hub")
    print(menu_p.name)


if __name__ == "__main__":
    main()
