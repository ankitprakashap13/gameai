"""Parse raw Dota 2 GSI JSON into typed structures."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.state.models import GSIParsedState


def _get_nested(d: dict[str, Any], *keys: str) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _int_safe(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _float_safe(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _hero_name(hero_block: Any) -> str | None:
    if not isinstance(hero_block, dict):
        return None
    name = hero_block.get("name")
    return str(name) if name else None


def _player_items(player_block: Any) -> list[str | None]:
    if not isinstance(player_block, dict):
        return []
    items: list[str | None] = []
    for i in range(6):
        key = f"slot{i}"
        slot = player_block.get(key)
        if isinstance(slot, dict) and slot.get("name"):
            items.append(str(slot["name"]))
        else:
            items.append(None)
    return items


def parse_gsi_payload(payload: dict[str, Any]) -> GSIParsedState:
    """Extract coaching-relevant fields from arbitrary GSI JSON."""
    hero = _get_nested(payload, "hero")
    player = _get_nested(payload, "player")
    map_block = _get_nested(payload, "map")

    game_time = _float_safe(_get_nested(map_block, "game_time") if map_block else None)
    clock_time = _float_safe(_get_nested(map_block, "clock_time") if map_block else None)
    map_name = None
    if isinstance(map_block, dict) and map_block.get("name"):
        map_name = str(map_block["name"])
    game_state_str = None
    if isinstance(map_block, dict) and map_block.get("game_state"):
        game_state_str = str(map_block["game_state"])
    win_team = None
    if isinstance(map_block, dict) and map_block.get("win_team"):
        win_team = str(map_block["win_team"])

    radiant = _int_safe(_get_nested(map_block, "radiant_score") if map_block else None)
    dire = _int_safe(_get_nested(map_block, "dire_score") if map_block else None)

    gold = _int_safe(_get_nested(player, "gold") if player else None)
    level = _int_safe(_get_nested(player, "level") if player else None)
    kills = _int_safe(_get_nested(player, "kills") if player else None)
    deaths = _int_safe(_get_nested(player, "deaths") if player else None)
    assists = _int_safe(_get_nested(player, "assists") if player else None)
    player_team = None
    if isinstance(player, dict) and player.get("team_name"):
        player_team = str(player["team_name"])

    return GSIParsedState(
        raw=payload,
        hero_name=_hero_name(hero),
        game_time_s=game_time,
        clock_time_s=clock_time,
        game_state=game_state_str,
        player_gold=gold,
        player_level=level,
        player_kills=kills,
        player_deaths=deaths,
        player_assists=assists,
        player_items=_player_items(player) if player else [],
        map_name=map_name,
        radiant_score=radiant,
        dire_score=dire,
        player_team=player_team,
        win_team=win_team,
        updated_at=datetime.now(timezone.utc),
    )
