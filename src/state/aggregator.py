"""Merge GSI and vision into GameState; persist structured events to DB."""

from __future__ import annotations

import json
import logging
import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from src.db.store import Database
from src.gsi.parser import parse_gsi_payload
from src.state.match_lifecycle import MatchLifecycle
from src.state.models import DraftState, GameState, GSIParsedState, VisionState

if TYPE_CHECKING:
    from src.vision.pipeline import VisionPipeline

log = logging.getLogger(__name__)


class StateAggregator:
    def __init__(
        self,
        db: Database,
        history_seconds: float = 30.0,
    ) -> None:
        self._db = db
        self._lock = threading.Lock()
        self._history_seconds = max(5.0, history_seconds)
        self._gsi: GSIParsedState = GSIParsedState()
        self._vision: VisionState | None = None
        self._draft: DraftState | None = None
        self._history: deque[GameState] = deque()
        self._vision_pipeline: VisionPipeline | None = None
        self._lifecycle = MatchLifecycle(
            db,
            on_draft_start=self._handle_draft_start,
            on_draft_end=self._handle_draft_end,
        )

    def attach_vision_pipeline(self, pipeline: VisionPipeline) -> None:
        self._vision_pipeline = pipeline

    def _handle_draft_start(self) -> None:
        if self._vision_pipeline:
            self._vision_pipeline.set_mode("draft")
        with self._lock:
            self._draft = None
            self._push_snapshot_unlocked()

    def _handle_draft_end(self) -> None:
        if self._vision_pipeline:
            self._vision_pipeline.set_mode("in_game")
        with self._lock:
            self._draft = None
            self._push_snapshot_unlocked()

    @property
    def match_id(self) -> int | None:
        return self._lifecycle.match_id

    def on_gsi_payload(self, payload: dict[str, Any]) -> None:
        parsed = parse_gsi_payload(payload)
        self._lifecycle.update(parsed)

        if self._vision_pipeline is not None:
            self._vision_pipeline.set_player_team(parsed.player_team)

        mid = self._lifecycle.match_id
        self._db.save_gsi_event(
            match_id=mid,
            game_time=parsed.game_time_s,
            gold=parsed.player_gold,
            level=parsed.player_level,
            kills=parsed.player_kills,
            deaths=parsed.player_deaths,
            assists=parsed.player_assists,
            items=parsed.player_items,
            raw=parsed.raw,
        )
        self._db.save_legacy_payload(payload)

        with self._lock:
            self._gsi = parsed
            self._push_snapshot_unlocked()

    def on_vision_state(self, vision: VisionState) -> None:
        mid = self._lifecycle.match_id
        minimap_json = json.dumps(
            [{"hero": h.hero_id, "x": h.x_norm, "y": h.y_norm, "c": h.confidence}
             for h in vision.minimap_heroes],
            ensure_ascii=False,
        ) if vision.minimap_heroes else None
        items_json = json.dumps(
            [{"slot": s.slot_index, "item": s.item_id, "c": s.confidence}
             for s in vision.item_slots if s.item_id],
            ensure_ascii=False,
        ) if vision.item_slots else None
        cooldowns_json = json.dumps(
            [{"idx": a.ability_index, "cd": a.on_cooldown, "pct": a.cooldown_pct}
             for a in vision.ability_cooldowns],
            ensure_ascii=False,
        ) if vision.ability_cooldowns else None

        game_time: float | None = None
        with self._lock:
            game_time = self._gsi.game_time_s

        self._db.save_vision_snapshot(
            match_id=mid,
            game_time=game_time,
            health_pct=vision.health_pct,
            mana_pct=vision.mana_pct,
            minimap_json=minimap_json,
            items_json=items_json,
            cooldowns_json=cooldowns_json,
        )

        with self._lock:
            self._vision = vision
            self._push_snapshot_unlocked()

    def on_draft_state(self, draft: DraftState) -> None:
        with self._lock:
            self._draft = draft
            self._push_snapshot_unlocked()

    def _push_snapshot_unlocked(self) -> None:
        snap = GameState(gsi=self._gsi, vision=self._vision, draft=self._draft)
        self._history.append(snap)
        now = snap.merged_at
        cutoff = now - timedelta(seconds=self._history_seconds)
        while self._history and self._history[0].merged_at < cutoff:
            self._history.popleft()

    def current(self) -> GameState:
        with self._lock:
            return GameState(
                gsi=self._gsi,
                vision=self._vision,
                draft=self._draft,
                merged_at=datetime.now(timezone.utc),
            )

    def recent_history(self) -> list[GameState]:
        with self._lock:
            return list(self._history)
