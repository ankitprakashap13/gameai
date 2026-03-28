"""Tests for the new Database schema and operations."""

import tempfile
from pathlib import Path

from src.db.store import Database


def _tmp_db() -> Database:
    d = tempfile.mkdtemp()
    return Database(Path(d) / "test.db")


def test_create_and_end_match():
    db = _tmp_db()
    mid = db.create_match(hero_name="npc_dota_hero_axe", map_name="start")
    assert mid >= 1
    m = db.get_open_match()
    assert m is not None
    assert m["id"] == mid
    assert m["hero_name"] == "npc_dota_hero_axe"
    assert m["ended_at"] is None

    db.end_match(mid, outcome="win")
    m2 = db.get_open_match()
    assert m2 is None

    matches = db.get_latest_matches(limit=5)
    assert len(matches) == 1
    assert matches[0]["outcome"] == "win"
    db.close()


def test_gsi_events():
    db = _tmp_db()
    mid = db.create_match()
    eid = db.save_gsi_event(
        match_id=mid,
        game_time=100.0,
        gold=500,
        level=6,
        kills=1,
        deaths=0,
        assists=2,
        items=["item_blink", None, None, None, None, None],
        raw={"hero": {"name": "axe"}},
    )
    assert eid >= 1
    events = db.get_match_events(mid)
    assert len(events) == 1
    assert events[0]["gold"] == 500
    db.close()


def test_vision_snapshots():
    db = _tmp_db()
    mid = db.create_match()
    vid = db.save_vision_snapshot(
        match_id=mid,
        game_time=200.0,
        health_pct=0.75,
        mana_pct=0.5,
        minimap_json='[{"hero":"axe"}]',
        items_json=None,
        cooldowns_json=None,
    )
    assert vid >= 1
    db.close()


def test_coaching_tips_and_dedup():
    db = _tmp_db()
    mid = db.create_match()
    tid = db.save_coaching_tip(
        match_id=mid,
        game_time=300.0,
        tip_text="Buy a BKB now",
        prompt_snapshot="prompt text...",
        latency_ms=450,
    )
    assert tid >= 1
    tips = db.get_recent_tips(mid, limit=5)
    assert len(tips) == 1
    assert tips[0]["tip_text"] == "Buy a BKB now"
    assert tips[0]["latency_ms"] == 450
    db.close()


def test_legacy_compat():
    db = _tmp_db()
    lid = db.save_legacy_payload({"hero": {"name": "axe"}})
    assert lid >= 1
    rows = db.fetch_latest_payloads(limit=10)
    assert len(rows) == 1
    assert "axe" in rows[0][2]
    db.close()


def test_wal_mode():
    db = _tmp_db()
    import sqlite3
    conn = sqlite3.connect(db._path)
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()
    assert mode == "wal"
    db.close()
