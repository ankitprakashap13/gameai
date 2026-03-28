"""Thread-safe SQLite store with WAL, connection pooling, and proper schema."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_SCHEMA_VERSION = 2

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matches (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    dota_match_id TEXT,
    hero_name     TEXT,
    map_name      TEXT,
    started_at    REAL NOT NULL,
    ended_at      REAL,
    outcome       TEXT,
    summary_json  TEXT
);

CREATE TABLE IF NOT EXISTS gsi_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id   INTEGER REFERENCES matches(id),
    game_time  REAL,
    gold       INTEGER,
    level      INTEGER,
    kills      INTEGER,
    deaths     INTEGER,
    assists    INTEGER,
    items_json TEXT,
    raw_json   TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS vision_snapshots (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id       INTEGER REFERENCES matches(id),
    game_time      REAL,
    health_pct     REAL,
    mana_pct       REAL,
    minimap_json   TEXT,
    items_json     TEXT,
    cooldowns_json TEXT,
    created_at     REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS coaching_tips (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id        INTEGER REFERENCES matches(id),
    game_time       REAL,
    category        TEXT,
    tip_text        TEXT NOT NULL,
    prompt_snapshot TEXT,
    latency_ms      INTEGER,
    created_at      REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gsi_match     ON gsi_events(match_id);
CREATE INDEX IF NOT EXISTS idx_vis_match     ON vision_snapshots(match_id);
CREATE INDEX IF NOT EXISTS idx_tips_match    ON coaching_tips(match_id);
CREATE INDEX IF NOT EXISTS idx_matches_start ON matches(started_at);
"""

# Keep backward-compat table for the /data viewer
_LEGACY_TABLE = """
CREATE TABLE IF NOT EXISTS gsi_data (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    payload    TEXT NOT NULL
);
"""


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


class Database:
    """Single shared SQLite connection with WAL mode, guarded by a lock."""

    def __init__(self, db_path: str | Path) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = str(path)
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None
        self._init()

    def _init(self) -> None:
        conn = self._get_conn()
        conn.executescript("PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;")
        conn.executescript(_SCHEMA_SQL)
        conn.executescript(_LEGACY_TABLE)
        cur = conn.execute(
            "SELECT value FROM schema_meta WHERE key='version'"
        ).fetchone()
        if cur is None:
            conn.execute(
                "INSERT INTO schema_meta(key,value) VALUES('version',?)",
                (str(_SCHEMA_VERSION),),
            )
        conn.commit()
        log.info("Database ready at %s (WAL mode)", self._path)

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    # ------ matches -------------------------------------------------------

    def create_match(
        self,
        hero_name: str | None = None,
        map_name: str | None = None,
        dota_match_id: str | None = None,
    ) -> int:
        with self._lock:
            c = self._get_conn()
            cur = c.execute(
                "INSERT INTO matches(dota_match_id, hero_name, map_name, started_at) "
                "VALUES(?,?,?,?)",
                (dota_match_id, hero_name, map_name, _now_ts()),
            )
            c.commit()
            return int(cur.lastrowid)

    def end_match(self, match_id: int, outcome: str | None = None) -> None:
        with self._lock:
            c = self._get_conn()
            c.execute(
                "UPDATE matches SET ended_at=?, outcome=? WHERE id=?",
                (_now_ts(), outcome, match_id),
            )
            c.commit()

    def update_match_hero(self, match_id: int, hero_name: str) -> None:
        with self._lock:
            c = self._get_conn()
            c.execute(
                "UPDATE matches SET hero_name=? WHERE id=? AND hero_name IS NULL",
                (hero_name, match_id),
            )
            c.commit()

    def save_match_summary(self, match_id: int, summary_json: str) -> None:
        with self._lock:
            c = self._get_conn()
            c.execute(
                "UPDATE matches SET summary_json=? WHERE id=?",
                (summary_json, match_id),
            )
            c.commit()

    def get_latest_matches(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            c = self._get_conn()
            rows = c.execute(
                "SELECT * FROM matches ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_open_match(self) -> dict[str, Any] | None:
        with self._lock:
            c = self._get_conn()
            row = c.execute(
                "SELECT * FROM matches WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    # ------ gsi_events ----------------------------------------------------

    def save_gsi_event(
        self,
        match_id: int | None,
        game_time: float | None,
        gold: int | None,
        level: int | None,
        kills: int | None,
        deaths: int | None,
        assists: int | None,
        items: list[str | None],
        raw: dict[str, Any],
    ) -> int:
        items_json = json.dumps(items, ensure_ascii=False)
        raw_json = json.dumps(raw, ensure_ascii=False)
        with self._lock:
            c = self._get_conn()
            cur = c.execute(
                "INSERT INTO gsi_events"
                "(match_id, game_time, gold, level, kills, deaths, assists, items_json, raw_json, created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (match_id, game_time, gold, level, kills, deaths, assists, items_json, raw_json, _now_ts()),
            )
            c.commit()
            return int(cur.lastrowid)

    # ------ vision_snapshots ----------------------------------------------

    def save_vision_snapshot(
        self,
        match_id: int | None,
        game_time: float | None,
        health_pct: float | None,
        mana_pct: float | None,
        minimap_json: str | None,
        items_json: str | None,
        cooldowns_json: str | None,
    ) -> int:
        with self._lock:
            c = self._get_conn()
            cur = c.execute(
                "INSERT INTO vision_snapshots"
                "(match_id, game_time, health_pct, mana_pct, minimap_json, items_json, cooldowns_json, created_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (match_id, game_time, health_pct, mana_pct, minimap_json, items_json, cooldowns_json, _now_ts()),
            )
            c.commit()
            return int(cur.lastrowid)

    # ------ coaching_tips -------------------------------------------------

    def save_coaching_tip(
        self,
        match_id: int | None,
        game_time: float | None,
        tip_text: str,
        category: str | None = None,
        prompt_snapshot: str | None = None,
        latency_ms: int | None = None,
    ) -> int:
        with self._lock:
            c = self._get_conn()
            cur = c.execute(
                "INSERT INTO coaching_tips"
                "(match_id, game_time, category, tip_text, prompt_snapshot, latency_ms, created_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (match_id, game_time, category, tip_text, prompt_snapshot, latency_ms, _now_ts()),
            )
            c.commit()
            return int(cur.lastrowid)

    def get_recent_tips(self, match_id: int | None, limit: int = 5) -> list[dict[str, Any]]:
        with self._lock:
            c = self._get_conn()
            if match_id is not None:
                rows = c.execute(
                    "SELECT * FROM coaching_tips WHERE match_id=? ORDER BY id DESC LIMIT ?",
                    (match_id, limit),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM coaching_tips ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    # ------ legacy (backward compat for /data viewer) ---------------------

    def save_legacy_payload(self, payload: dict[str, Any]) -> int:
        with self._lock:
            c = self._get_conn()
            now = datetime.now(timezone.utc).isoformat()
            raw = json.dumps(payload, ensure_ascii=False)
            cur = c.execute(
                "INSERT INTO gsi_data(created_at, payload) VALUES(?,?)", (now, raw)
            )
            c.commit()
            return int(cur.lastrowid)

    def fetch_latest_payloads(self, limit: int = 100) -> list[tuple[int, str, str]]:
        with self._lock:
            c = self._get_conn()
            rows = c.execute(
                "SELECT id, created_at, payload FROM gsi_data ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [(int(r["id"]), str(r["created_at"]), str(r["payload"])) for r in rows]

    # ------ analytics helpers ---------------------------------------------

    def get_match_events(self, match_id: int) -> list[dict[str, Any]]:
        with self._lock:
            c = self._get_conn()
            rows = c.execute(
                "SELECT * FROM gsi_events WHERE match_id=? ORDER BY game_time",
                (match_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_match_tips(self, match_id: int) -> list[dict[str, Any]]:
        with self._lock:
            c = self._get_conn()
            rows = c.execute(
                "SELECT * FROM coaching_tips WHERE match_id=? ORDER BY game_time",
                (match_id,),
            ).fetchall()
            return [dict(r) for r in rows]
