"""Tests for GSI parsing."""

from src.gsi.parser import parse_gsi_payload


def test_parse_minimal_payload():
    payload = {
        "hero": {"name": "npc_dota_hero_axe"},
        "map": {
            "game_time": 123.5,
            "clock_time": -45.0,
            "name": "start",
            "game_state": "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS",
            "radiant_score": 5,
            "dire_score": 3,
        },
        "player": {
            "gold": 420,
            "level": 10,
            "kills": 2,
            "deaths": 1,
            "assists": 7,
            "team_name": "radiant",
            "slot0": {"name": "item_blink"},
        },
    }
    g = parse_gsi_payload(payload)
    assert g.hero_name == "npc_dota_hero_axe"
    assert g.game_time_s == 123.5
    assert g.game_state == "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS"
    assert g.player_gold == 420
    assert g.player_level == 10
    assert g.player_team == "radiant"
    assert g.player_items and g.player_items[0] == "item_blink"


def test_parse_empty():
    g = parse_gsi_payload({})
    assert g.hero_name is None
    assert g.game_state is None
    assert g.player_items == []
