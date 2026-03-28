"""Detect match start / end from GSI game_state transitions."""

from __future__ import annotations

import logging
from typing import Callable

from src.db.store import Database
from src.state.models import GSIParsedState

log = logging.getLogger(__name__)

# Dota 2 GSI game_state values (from map.game_state)
_IN_PROGRESS = "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS"
_PRE_GAME = "DOTA_GAMERULES_STATE_PRE_GAME"
_POST_GAME = "DOTA_GAMERULES_STATE_POST_GAME"
_HERO_SELECTION = "DOTA_GAMERULES_STATE_HERO_SELECTION"

_ACTIVE_STATES = {_IN_PROGRESS, _PRE_GAME}


class MatchLifecycle:
    """
    Tracks the current match.  Call `update(parsed)` on every GSI tick.
    Auto-creates a DB match row on first in-progress state and closes it on post-game.
    """

    def __init__(
        self,
        db: Database,
        on_match_start: Callable[[int], None] | None = None,
        on_match_end: Callable[[int, str | None], None] | None = None,
        on_draft_start: Callable[[], None] | None = None,
        on_draft_end: Callable[[], None] | None = None,
    ) -> None:
        self._db = db
        self._on_start = on_match_start
        self._on_end = on_match_end
        self._on_draft_start = on_draft_start
        self._on_draft_end = on_draft_end
        self._match_id: int | None = None
        self._prev_state: str | None = None
        self._hero_set = False

        existing = db.get_open_match()
        if existing:
            self._match_id = int(existing["id"])
            log.info("Resumed open match id=%d", self._match_id)

    @property
    def match_id(self) -> int | None:
        return self._match_id

    def update(self, parsed: GSIParsedState) -> None:
        gs = parsed.game_state
        if gs is None:
            return

        prev = self._prev_state

        # Draft phase: hero selection screen
        if gs == _HERO_SELECTION and prev != _HERO_SELECTION:
            log.info("Draft phase started (HERO_SELECTION)")
            if self._on_draft_start:
                self._on_draft_start()
        if prev == _HERO_SELECTION and gs != _HERO_SELECTION:
            log.info("Draft phase ended -> %s", gs)
            if self._on_draft_end:
                self._on_draft_end()

        # Transition into active game
        if gs in _ACTIVE_STATES and self._match_id is None:
            self._match_id = self._db.create_match(
                hero_name=parsed.hero_name,
                map_name=parsed.map_name,
            )
            self._hero_set = parsed.hero_name is not None
            log.info("Match started id=%d hero=%s", self._match_id, parsed.hero_name)
            if self._on_start:
                self._on_start(self._match_id)

        # Backfill hero name when it arrives (GSI sometimes sends hero later)
        if (
            self._match_id is not None
            and not self._hero_set
            and parsed.hero_name
        ):
            self._db.update_match_hero(self._match_id, parsed.hero_name)
            self._hero_set = True

        # Transition to post-game
        if gs == _POST_GAME and self._match_id is not None:
            outcome = self._determine_outcome(parsed)
            self._db.end_match(self._match_id, outcome=outcome)
            log.info("Match ended id=%d outcome=%s", self._match_id, outcome)
            if self._on_end:
                self._on_end(self._match_id, outcome)
            self._match_id = None
            self._hero_set = False

        self._prev_state = gs

    @staticmethod
    def _determine_outcome(parsed: GSIParsedState) -> str | None:
        wt = parsed.win_team
        pt = parsed.player_team
        if wt and pt:
            if wt.lower() == pt.lower():
                return "win"
            return "loss"
        return None
