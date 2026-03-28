"""First-run checks: GSI config, LLM keys, vision templates. Prints guidance."""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import Any

# Same detection logic as setup_gsi.py but kept standalone to avoid imports
_GSI_FILENAME = "gamestate_integration_coach.cfg"


def _find_dota_cfg_dir() -> Path | None:
    import re
    system = platform.system()
    steam_roots: list[Path] = []
    if system == "Windows":
        steam_roots = [
            Path("C:/Program Files (x86)/Steam"),
            Path("C:/Program Files/Steam"),
            Path("D:/Steam"),
            Path("D:/SteamLibrary"),
        ]
    elif system == "Darwin":
        steam_roots = [Path.home() / "Library/Application Support/Steam"]
    else:
        steam_roots = [
            Path.home() / ".steam/steam",
            Path.home() / ".local/share/Steam",
        ]

    library_paths: list[Path] = []
    for sr in steam_roots:
        vdf = sr / "steamapps" / "libraryfolders.vdf"
        if vdf.is_file():
            text = vdf.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r'"path"\s+"([^"]+)"', text, re.IGNORECASE):
                p = Path(m.group(1).replace("\\\\", "/"))
                if p.is_dir():
                    library_paths.append(p)
        if sr.is_dir() and sr not in library_paths:
            library_paths.append(sr)

    for lib in library_paths:
        candidate = lib / "steamapps" / "common" / "dota 2 beta" / "game" / "dota" / "cfg"
        if candidate.is_dir():
            return candidate
    return None


def _check_gsi(project_root: Path) -> list[str]:
    """Check if GSI cfg is installed in Dota's folder."""
    issues: list[str] = []
    cfg_dir = _find_dota_cfg_dir()
    if cfg_dir is None:
        issues.append(
            "Could not find Dota 2 install. Run:\n"
            "    python scripts/setup_gsi.py\n"
            "  to auto-install the GSI config, or copy it manually.\n"
            "  (See README for the target path.)"
        )
        return issues
    gsi_dest = cfg_dir / "gamestate_integration" / _GSI_FILENAME
    if not gsi_dest.is_file():
        issues.append(
            f"GSI config not installed. Run:\n"
            f"    python scripts/setup_gsi.py\n"
            f"  Expected at: {gsi_dest}"
        )
    return issues


def _check_llm_keys(cfg: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    llm = cfg.get("llm") or {}
    provider = (os.environ.get("COACH_LLM_PROVIDER") or llm.get("provider") or "openai").lower()

    if provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        issues.append(
            "No OPENAI_API_KEY found.\n"
            "  Option A: Copy .env.example to .env and paste your key there.\n"
            "  Option B: Switch to free local LLM — set COACH_LLM_PROVIDER=ollama in .env\n"
            "            (requires Ollama installed: https://ollama.com)"
        )
    elif provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        issues.append(
            "No ANTHROPIC_API_KEY found.\n"
            "  Copy .env.example to .env and paste your Anthropic key there."
        )
    elif provider == "ollama":
        base = os.environ.get("OLLAMA_HOST") or llm.get("ollama_base_url") or "http://localhost:11434"
        try:
            import urllib.request
            urllib.request.urlopen(base, timeout=3)
        except Exception:
            issues.append(
                f"Ollama server not reachable at {base}.\n"
                "  1. Install Ollama from https://ollama.com\n"
                "  2. Run: ollama pull llama3.2\n"
                "  3. Make sure Ollama is running before starting the coach."
            )
    return issues


def _check_templates(project_root: Path, cfg: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    paths = cfg.get("paths") or {}
    heroes_dir = project_root / paths.get("templates_heroes", "assets/templates/heroes")
    pngs = list(heroes_dir.glob("*.png")) if heroes_dir.is_dir() else []
    if len(pngs) < 5:
        issues.append(
            f"Vision templates missing ({len(pngs)} hero icons found).\n"
            "  Run:  python scripts/download_assets.py\n"
            "  This downloads hero and item icons for screen detection (~2 min)."
        )
    return issues


def _check_display_mode() -> list[str]:
    issues: list[str] = []
    if platform.system() == "Windows":
        issues.append(
            "REMINDER: Dota 2 must be in Borderless Windowed mode.\n"
            "  Settings > Video > Display Mode > Borderless Window\n"
            "  (Exclusive fullscreen blocks the overlay and screen capture.)"
        )
    return issues


def run_preflight(project_root: Path, cfg: dict[str, Any]) -> bool:
    """
    Run all checks. Print issues with fix instructions.
    Returns True if safe to continue, False if there are blockers.
    """
    blockers: list[str] = []
    warnings: list[str] = []

    blockers.extend(_check_llm_keys(cfg))
    warnings.extend(_check_gsi(project_root))
    warnings.extend(_check_templates(project_root, cfg))
    warnings.extend(_check_display_mode())

    if not blockers and not warnings:
        return True

    print("\n╔══════════════════════════════════════════╗")
    print("║     Dota 2 AI Coach — Startup Checks     ║")
    print("╚══════════════════════════════════════════╝\n")

    if blockers:
        print("BLOCKERS (must fix before the app can work):\n")
        for i, b in enumerate(blockers, 1):
            print(f"  {i}. {b}\n")

    if warnings:
        header = "WARNINGS (app will start, but features may be limited):\n" if not blockers else "ALSO:\n"
        print(header)
        for i, w in enumerate(warnings, 1):
            print(f"  {i}. {w}\n")

    if blockers:
        print("Fix the blockers above, then run again: python main.py\n")
        return False

    print("Continuing startup...\n")
    return True
