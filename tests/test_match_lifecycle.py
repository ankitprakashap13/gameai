"""Tests for match lifecycle transitions."""

import tempfile
from pathlib import Path

from src.db.store import Database
from src.state.match_lifecycle import MatchLifecycle
from src.state.models import GSIParsedState


def _tmp_db() -> Database:
    d = tempfile.mkdtemp()
    return Database(Path(d) / "test.db")


def _parsed(game_state: str | None = None, hero: str | None = None, team: str | None = None, win_team: str | None = None) -> GSIParsedState:
    return GSIParsedState(
        game_state=game_state,
        hero_name=hero,
        map_name="start",
        player_team=team,
        win_team=win_team,
    )


def test_match_start_and_end():
    db = _tmp_db()
    started = []
    ended = []
    lc = MatchLifecycle(
        db,
        on_match_start=lambda mid: started.append(mid),
        on_match_end=lambda mid, o: ended.append((mid, o)),
    )

    assert lc.match_id is None

    lc.update(_parsed(game_state="DOTA_GAMERULES_STATE_GAME_IN_PROGRESS", hero="axe"))
    assert lc.match_id is not None
    mid = lc.match_id
    assert len(started) == 1

    # Second in-progress tick should NOT create a new match
    lc.update(_parsed(game_state="DOTA_GAMERULES_STATE_GAME_IN_PROGRESS", hero="axe"))
    assert lc.match_id == mid
    assert len(started) == 1

    lc.update(_parsed(game_state="DOTA_GAMERULES_STATE_POST_GAME", hero="axe", team="radiant", win_team="radiant"))
    assert lc.match_id is None
    assert len(ended) == 1
    assert ended[0] == (mid, "win")
    db.close()


def test_loss_outcome():
    db = _tmp_db()
    lc = MatchLifecycle(db)
    lc.update(_parsed(game_state="DOTA_GAMERULES_STATE_GAME_IN_PROGRESS"))
    lc.update(_parsed(game_state="DOTA_GAMERULES_STATE_POST_GAME", team="dire", win_team="radiant"))
    matches = db.get_latest_matches(1)
    assert matches[0]["outcome"] == "loss"
    db.close()


def test_hero_backfill():
    db = _tmp_db()
    lc = MatchLifecycle(db)
    lc.update(_parsed(game_state="DOTA_GAMERULES_STATE_PRE_GAME"))
    mid = lc.match_id
    assert mid is not None

    m = db.get_open_match()
    assert m is not None
    assert m["hero_name"] is None

    lc.update(_parsed(game_state="DOTA_GAMERULES_STATE_GAME_IN_PROGRESS", hero="npc_dota_hero_invoker"))
    m2 = db.get_open_match()
    assert m2 is not None
    assert m2["hero_name"] == "npc_dota_hero_invoker"
    db.close()


def test_no_state_is_noop():
    db = _tmp_db()
    lc = MatchLifecycle(db)
    lc.update(_parsed())
    assert lc.match_id is None
    db.close()
