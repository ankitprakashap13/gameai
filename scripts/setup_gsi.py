#!/usr/bin/env python3
"""
Auto-detect Dota 2 install path via Steam's libraryfolders.vdf and install
the GSI config file.  Falls back to manual path entry if auto-detect fails.

Usage:
    python scripts/setup_gsi.py
"""

from __future__ import annotations

import platform
import re
import shutil
import sys
from pathlib import Path

GSI_FILENAME = "gamestate_integration_coach.cfg"


def _steam_default_roots() -> list[Path]:
    """Common Steam install directories per OS."""
    system = platform.system()
    if system == "Windows":
        return [
            Path("C:/Program Files (x86)/Steam"),
            Path("C:/Program Files/Steam"),
            Path("D:/Steam"),
            Path("D:/SteamLibrary"),
        ]
    if system == "Darwin":
        return [Path.home() / "Library/Application Support/Steam"]
    # Linux
    return [
        Path.home() / ".steam/steam",
        Path.home() / ".local/share/Steam",
    ]


def _parse_libraryfolders(vdf_path: Path) -> list[Path]:
    """Extract library paths from Steam's libraryfolders.vdf (Valve KV format)."""
    paths: list[Path] = []
    if not vdf_path.is_file():
        return paths
    text = vdf_path.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r'"path"\s+"([^"]+)"', text, re.IGNORECASE):
        p = Path(m.group(1).replace("\\\\", "/"))
        if p.is_dir():
            paths.append(p)
    return paths


def _find_dota_cfg() -> Path | None:
    """Walk Steam libraries looking for dota 2 beta/game/dota/cfg."""
    library_roots: list[Path] = []
    for steam_root in _steam_default_roots():
        vdf = steam_root / "steamapps" / "libraryfolders.vdf"
        if vdf.is_file():
            library_roots.extend(_parse_libraryfolders(vdf))
        if steam_root.is_dir() and steam_root not in library_roots:
            library_roots.append(steam_root)

    for lib in library_roots:
        candidate = lib / "steamapps" / "common" / "dota 2 beta" / "game" / "dota" / "cfg"
        if candidate.is_dir():
            return candidate
    return None


def _install_gsi(cfg_dir: Path, source: Path) -> Path:
    gsi_dir = cfg_dir / "gamestate_integration"
    gsi_dir.mkdir(parents=True, exist_ok=True)
    dest = gsi_dir / GSI_FILENAME
    shutil.copy2(source, dest)
    return dest


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    source_cfg = project_root / "assets" / "config" / GSI_FILENAME
    if not source_cfg.is_file():
        print(f"ERROR: source config not found at {source_cfg}", file=sys.stderr)
        return 1

    print("=== Dota 2 AI Coach — GSI Setup ===\n")
    print("Looking for Dota 2 installation...")

    cfg_dir = _find_dota_cfg()

    if cfg_dir:
        print(f"\n  Found Dota 2 cfg directory:\n  {cfg_dir}\n")
    else:
        print("\n  Could not auto-detect Dota 2 install.\n")
        print("  Typical paths:")
        print("    Windows: C:\\Program Files (x86)\\Steam\\steamapps\\common\\dota 2 beta\\game\\dota\\cfg")
        print("    Mac:     ~/Library/Application Support/Steam/steamapps/common/dota 2 beta/game/dota/cfg")
        print("    Linux:   ~/.steam/steam/steamapps/common/dota 2 beta/game/dota/cfg")
        print()
        raw = input("  Paste the full path to your Dota 2 'cfg' folder (or press Enter to cancel): ").strip()
        if not raw:
            print("Cancelled.")
            return 1
        raw = raw.strip('"').strip("'")
        cfg_dir = Path(raw)
        if not cfg_dir.is_dir():
            print(f"ERROR: directory does not exist: {cfg_dir}", file=sys.stderr)
            return 1

    dest = _install_gsi(cfg_dir, source_cfg)
    print(f"  Installed GSI config to:\n  {dest}\n")
    print("  Dota 2 will send game state to http://127.0.0.1:3000/ when you play.")
    print("  If Dota is already running, restart it to pick up the new config.\n")
    print("Done!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
