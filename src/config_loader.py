"""Load .env then YAML config with optional config.local.yaml overlay."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def load_dotenv(project_root: Path | None = None) -> None:
    """Load .env file into os.environ if python-dotenv is available."""
    root = project_root or Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv as _load
        _load(env_path, override=False)
    except ImportError:
        pass


def load_config(project_root: Path | None = None) -> dict[str, Any]:
    root = project_root or Path(__file__).resolve().parent.parent
    load_dotenv(root)

    main_path = root / "config.yaml"
    local_path = root / "config.local.yaml"

    if not main_path.is_file():
        raise FileNotFoundError(f"Missing {main_path}")

    with main_path.open(encoding="utf-8") as f:
        cfg: dict[str, Any] = yaml.safe_load(f) or {}

    if local_path.is_file():
        with local_path.open(encoding="utf-8") as f:
            local = yaml.safe_load(f) or {}
        if isinstance(local, dict):
            cfg = _deep_merge(cfg, local)

    return cfg
