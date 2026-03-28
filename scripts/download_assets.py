#!/usr/bin/env python3
"""
Download Dota 2 hero and item icons from Steam CDN (via dotaconstants paths).
Resize hero icons for minimap-style template matching (~32px).

Usage (from project root):
  python scripts/download_assets.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np

CDN = "https://cdn.cloudflare.steamstatic.com"
HEROES_JSON = "https://raw.githubusercontent.com/odota/dotaconstants/master/build/heroes.json"
ITEMS_JSON = "https://raw.githubusercontent.com/odota/dotaconstants/master/build/items.json"


def _fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _download_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def _save_gray_png(data: bytes, out_path: Path, size: tuple[int, int]) -> None:
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return
    img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), gray)


def _save_color_png(data: bytes, out_path: Path, size: tuple[int, int]) -> None:
    """Color templates for draft top-bar matching (approx in-game portrait aspect)."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return
    img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), img)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    heroes_dir = root / "assets" / "templates" / "heroes"
    portraits_dir = root / "assets" / "templates" / "portraits"
    items_dir = root / "assets" / "templates" / "items"
    wards_dir = root / "assets" / "templates" / "wards"

    print("Fetching heroes.json …")
    heroes = _fetch_json(HEROES_JSON)
    hero_count = 0
    for _hid, h in heroes.items():
        if not isinstance(h, dict):
            continue
        img_path = h.get("img") or h.get("icon")
        if not img_path or not isinstance(img_path, str):
            continue
        url = CDN + img_path
        stem = str(h.get("name") or h.get("localized_name") or _hid).replace(" ", "_")
        stem = "".join(c if c.isalnum() or c in "_-" else "_" for c in stem).lower()
        out = heroes_dir / f"{stem}.png"
        try:
            data = _download_bytes(url)
            _save_gray_png(data, out, (32, 32))
            pout = portraits_dir / f"{stem}.png"
            _save_color_png(data, pout, (62, 35))
            hero_count += 1
            print(f"  hero {hero_count}: {out.name}")
        except Exception as e:
            print(f"  skip hero {_hid}: {e}", file=sys.stderr)

    print("Fetching items.json …")
    items = _fetch_json(ITEMS_JSON)
    item_count = 0
    for _iid, it in items.items():
        if not isinstance(it, dict):
            continue
        img_path = it.get("img")
        if not img_path or not isinstance(img_path, str):
            continue
        url = CDN + img_path
        stem = str(it.get("short_name") or it.get("name") or _iid).replace(" ", "_")
        stem = "".join(c if c.isalnum() or c in "_-" else "_" for c in stem).lower()
        out = items_dir / f"{stem}.png"
        try:
            data = _download_bytes(url)
            _save_gray_png(data, out, (40, 30))
            item_count += 1
        except Exception as e:
            print(f"  skip item {_iid}: {e}", file=sys.stderr)
    print(f"Items saved: {item_count} to {items_dir}")

    wards_dir.mkdir(parents=True, exist_ok=True)
    readme = wards_dir / "README.txt"
    readme.write_text(
        "Add observer_ward.png and sentry_ward.png (grayscale PNGs cropped from screenshots) "
        "for ward matching, or leave empty to skip ward detection.\n",
        encoding="utf-8",
    )
    print(f"Hero templates: {hero_count} → {heroes_dir}")
    print(f"Draft portraits (color): {hero_count} → {portraits_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
