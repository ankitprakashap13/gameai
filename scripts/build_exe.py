#!/usr/bin/env python3
"""
Build a standalone executable for the Dota 2 AI Coach using PyInstaller.

Usage (from project root, with venv activated):
    python scripts/build_exe.py

Output: dist/DotaCoach/DotaCoach.exe  (Windows)
        dist/DotaCoach/DotaCoach      (Mac/Linux)

The output is a one-folder bundle (not a single file) to keep startup fast.
Users unzip the dist/DotaCoach folder and run the executable inside.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    main_py = root / "main.py"
    assets = root / "assets"
    config_yaml = root / "config.yaml"
    env_example = root / ".env.example"
    scripts_dir = root / "scripts"

    if not main_py.is_file():
        print("ERROR: main.py not found in project root", file=sys.stderr)
        return 1

    name = "DotaCoach"
    sep = ";" if platform.system() == "Windows" else ":"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", name,
        "--noconfirm",
        "--clean",
        # Bundle data files
        "--add-data", f"{config_yaml}{sep}.",
        "--add-data", f"{env_example}{sep}.",
        "--add-data", f"{assets}{sep}assets",
        "--add-data", f"{scripts_dir / 'setup_gsi.py'}{sep}scripts",
        "--add-data", f"{scripts_dir / 'download_assets.py'}{sep}scripts",
        # Hidden imports that PyInstaller may miss
        "--hidden-import", "src",
        "--hidden-import", "src.config_loader",
        "--hidden-import", "src.preflight",
        "--hidden-import", "src.db.store",
        "--hidden-import", "src.gsi.server",
        "--hidden-import", "src.gsi.parser",
        "--hidden-import", "src.state.models",
        "--hidden-import", "src.state.aggregator",
        "--hidden-import", "src.state.match_lifecycle",
        "--hidden-import", "src.vision.capture",
        "--hidden-import", "src.vision.pipeline",
        "--hidden-import", "src.vision.regions",
        "--hidden-import", "src.vision.detectors.minimap",
        "--hidden-import", "src.vision.detectors.items",
        "--hidden-import", "src.vision.detectors.health",
        "--hidden-import", "src.vision.detectors.cooldowns",
        "--hidden-import", "src.vision.detectors.draft",
        "--hidden-import", "src.llm.base",
        "--hidden-import", "src.llm.factory",
        "--hidden-import", "src.llm.coach",
        "--hidden-import", "src.llm.openai_provider",
        "--hidden-import", "src.llm.anthropic_provider",
        "--hidden-import", "src.llm.ollama_provider",
        "--hidden-import", "src.overlay.window",
        "--hidden-import", "src.overlay.widgets",
        "--hidden-import", "engineio.async_drivers.threading",
        # Console window so users see preflight messages
        "--console",
        str(main_py),
    ]

    print(f"Building {name}...")
    print(f"  Command: {' '.join(cmd[:6])} ...")
    result = subprocess.run(cmd, cwd=str(root))
    if result.returncode != 0:
        print("Build failed.", file=sys.stderr)
        return result.returncode

    dist_dir = root / "dist" / name
    print(f"\nBuild complete: {dist_dir}")
    print(f"  Executable: {dist_dir / (name + ('.exe' if platform.system() == 'Windows' else ''))}")
    print("\nTo distribute:")
    print(f"  1. Copy .env.example into {dist_dir} as .env and fill in keys")
    print(f"  2. Run scripts/download_assets.py to populate assets/templates/ before building,")
    print(f"     or have users run DotaCoach once (it will tell them what's missing)")
    print(f"  3. Zip the {dist_dir} folder and share it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
