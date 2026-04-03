"""Game timer tracking: rune spawns, Roshan respawn, and missing hero detection."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# Dota 2 rune spawn schedule (seconds of game clock)
_BOUNTY_INTERVAL = 180   # every 3 min starting at 0:00
_POWER_START = 360       # first power rune at 6:00
_POWER_INTERVAL = 120    # every 2 min after 6:00
_WATER_TIMES = (120, 240)  # 2:00 and 4:00 only
_WARN_WINDOW = 30        # alert N seconds before spawn

# Roshan respawn window (seconds after kill)
_ROSH_MIN_RESPAWN = 480  # 8 min
_ROSH_MAX_RESPAWN = 660  # 11 min

# Enemy-item-check nudge
_ITEM_CHECK_INTERVAL = 300  # 5 min between nudges
_ITEM_CHECK_MIN_TIME = 900  # only after 15 min (mid game)

# Missing hero thresholds
_MIA_RECENCY = 30.0   # hero must have been seen within this window to count
_MIA_ABSENCE = 8.0    # hero must be absent this long before alert fires


def _next_spawn(now: float, start: float, interval: float) -> float:
    """Return the next spawn time > *now* for the given periodic schedule."""
    if now < start:
        return start
    elapsed = now - start
    periods = int(elapsed / interval)
    return start + (periods + 1) * interval


class GameTimerTracker:
    """Fires event reasons based on game clock: rune spawns, Roshan, item-check nudges."""

    def __init__(self) -> None:
        self._last_bounty_warned: float = -999.0
        self._last_power_warned: float = -999.0
        self._last_water_warned: float = -999.0
        self._rosh_kill_time: float | None = None
        self._rosh_may_fired = False
        self._rosh_alive_fired = False
        self._had_aegis = False
        self._last_item_nudge: float = -999.0

    def reset(self) -> None:
        self.__init__()  # type: ignore[misc]

    def check(
        self,
        clock_time: float | None,
        player_items: list[str | None],
        known_enemy_items: dict[str, list[str]] | None = None,
        known_enemy_heroes: list[str] | None = None,
    ) -> list[str]:
        """Return a list of event reason strings for any timers that fire now."""
        if clock_time is None or clock_time < 0:
            return []
        reasons: list[str] = []
        reasons.extend(self._check_runes(clock_time))
        reasons.extend(self._check_roshan(clock_time, player_items))
        reasons.extend(self._check_item_nudge(
            clock_time, known_enemy_items or {}, known_enemy_heroes or [],
        ))
        return reasons

    def rune_note(self, clock_time: float | None) -> str:
        """Human-readable rune proximity note for prompts."""
        if clock_time is None or clock_time < 0:
            return ""
        notes: list[str] = []

        delta_b = _next_spawn(clock_time, 0, _BOUNTY_INTERVAL) - clock_time
        if 0 < delta_b <= _WARN_WINDOW:
            notes.append(f"Bounty runes in {int(delta_b)}s")

        if clock_time >= _POWER_START - _WARN_WINDOW:
            delta_p = _next_spawn(clock_time, _POWER_START, _POWER_INTERVAL) - clock_time
            if 0 < delta_p <= _WARN_WINDOW:
                notes.append(f"Power rune in {int(delta_p)}s")

        for wt in _WATER_TIMES:
            delta_w = wt - clock_time
            if 0 < delta_w <= _WARN_WINDOW:
                notes.append(f"Water rune in {int(delta_w)}s")
                break

        return "; ".join(notes)

    def roshan_status(self, clock_time: float | None) -> str:
        """Human-readable Roshan status for prompts."""
        if self._rosh_kill_time is None:
            return "unknown"
        if clock_time is None:
            return "unknown"
        elapsed = clock_time - self._rosh_kill_time
        if elapsed >= _ROSH_MAX_RESPAWN:
            return "alive (respawn window passed)"
        if elapsed >= _ROSH_MIN_RESPAWN:
            return f"may be alive (killed {int(elapsed)}s ago)"
        return f"dead (killed {int(elapsed)}s ago)"

    def _check_runes(self, clock_time: float) -> list[str]:
        reasons: list[str] = []

        next_bounty = _next_spawn(clock_time, 0, _BOUNTY_INTERVAL)
        if 0 < next_bounty - clock_time <= _WARN_WINDOW and next_bounty != self._last_bounty_warned:
            self._last_bounty_warned = next_bounty
            reasons.append("rune_bounty_approaching")

        if clock_time >= _POWER_START - _WARN_WINDOW:
            next_power = _next_spawn(clock_time, _POWER_START, _POWER_INTERVAL)
            if 0 < next_power - clock_time <= _WARN_WINDOW and next_power != self._last_power_warned:
                self._last_power_warned = next_power
                reasons.append("rune_power_approaching")

        for wt in _WATER_TIMES:
            if 0 < wt - clock_time <= _WARN_WINDOW and wt != self._last_water_warned:
                self._last_water_warned = float(wt)
                reasons.append("rune_water_approaching")
                break

        return reasons

    def _check_roshan(self, clock_time: float, player_items: list[str | None]) -> list[str]:
        reasons: list[str] = []
        has_aegis = any(i == "item_aegis" for i in player_items if i)

        if has_aegis and not self._had_aegis:
            self._rosh_kill_time = clock_time
            self._rosh_may_fired = False
            self._rosh_alive_fired = False
            log.info("Aegis detected — Roshan killed at %.0fs", clock_time)

        self._had_aegis = has_aegis

        if self._rosh_kill_time is not None:
            elapsed = clock_time - self._rosh_kill_time
            if elapsed >= _ROSH_MIN_RESPAWN and not self._rosh_may_fired:
                self._rosh_may_fired = True
                reasons.append("roshan_may_respawn")
            if elapsed >= _ROSH_MAX_RESPAWN and not self._rosh_alive_fired:
                self._rosh_alive_fired = True
                reasons.append("roshan_alive")

        return reasons

    def _check_item_nudge(
        self,
        clock_time: float,
        known_enemy_items: dict[str, list[str]],
        known_enemy_heroes: list[str],
    ) -> list[str]:
        if clock_time < _ITEM_CHECK_MIN_TIME or not known_enemy_heroes:
            return []
        stale = any(
            hero not in known_enemy_items or not known_enemy_items[hero]
            for hero in known_enemy_heroes
        )
        if stale and clock_time - self._last_item_nudge >= _ITEM_CHECK_INTERVAL:
            self._last_item_nudge = clock_time
            return ["check_enemy_items"]
        return []


class MissingHeroTracker:
    """Diff minimap detections against known enemies; fire hero_missing events."""

    def __init__(
        self,
        recency_window: float = _MIA_RECENCY,
        absence_threshold: float = _MIA_ABSENCE,
    ) -> None:
        self._recency = recency_window
        self._absence = absence_threshold
        self._last_seen: dict[str, float] = {}
        self._alerted: set[str] = set()

    def reset(self) -> None:
        self._last_seen.clear()
        self._alerted.clear()

    def update(
        self,
        clock_time: float | None,
        visible_hero_ids: list[str],
        known_enemy_heroes: list[str],
    ) -> list[str]:
        """Return event reasons for enemies that just went MIA."""
        if clock_time is None or clock_time < 0:
            return []

        visible_set = set(visible_hero_ids)

        for hero_id in visible_set:
            self._last_seen[hero_id] = clock_time
            self._alerted.discard(hero_id)

        reasons: list[str] = []
        for hero_id in known_enemy_heroes:
            if hero_id in visible_set:
                continue
            last = self._last_seen.get(hero_id)
            if last is None:
                continue
            time_since = clock_time - last
            if time_since <= self._recency and time_since >= self._absence and hero_id not in self._alerted:
                self._alerted.add(hero_id)
                reasons.append(f"hero_missing:{hero_id}")
                log.info("MIA alert: %s (last seen %.0fs ago)", hero_id, time_since)

        return reasons

    @property
    def missing_heroes(self) -> list[str]:
        """Currently-alerted hero IDs (still missing)."""
        return list(self._alerted)
