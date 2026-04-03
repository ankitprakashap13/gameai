"""Tests for GameTimerTracker and MissingHeroTracker."""

import pytest
from src.state.timers import GameTimerTracker, MissingHeroTracker


class TestGameTimerTracker:
    def test_no_events_before_game(self):
        t = GameTimerTracker()
        assert t.check(None, []) == []
        assert t.check(-10.0, []) == []

    def test_bounty_rune_warning(self):
        t = GameTimerTracker()
        assert t.check(140.0, []) == []
        reasons = t.check(155.0, [])
        assert "rune_bounty_approaching" in reasons

    def test_bounty_rune_no_repeat(self):
        t = GameTimerTracker()
        t.check(155.0, [])
        assert t.check(160.0, []) == []

    def test_power_rune_warning(self):
        t = GameTimerTracker()
        reasons = t.check(335.0, [])
        assert "rune_power_approaching" in reasons

    def test_water_rune_warning(self):
        t = GameTimerTracker()
        reasons = t.check(95.0, [])
        assert "rune_water_approaching" in reasons

    def test_no_water_after_4min(self):
        t = GameTimerTracker()
        assert t.check(250.0, []) == []

    def test_roshan_aegis_tracking(self):
        t = GameTimerTracker()
        t.check(600.0, ["item_aegis", None, None, None, None, None])
        assert t.roshan_status(600.0) == "dead (killed 0s ago)"

        reasons = t.check(1080.0, [None] * 6)
        assert "roshan_may_respawn" in reasons

        reasons = t.check(1260.0, [None] * 6)
        assert "roshan_alive" in reasons

    def test_roshan_status_alive_after_window(self):
        t = GameTimerTracker()
        t.check(100.0, ["item_aegis", None, None, None, None, None])
        assert "alive" in t.roshan_status(800.0)

    def test_rune_note_empty_outside_window(self):
        t = GameTimerTracker()
        assert t.rune_note(50.0) == ""

    def test_rune_note_bounty(self):
        t = GameTimerTracker()
        note = t.rune_note(160.0)
        assert "Bounty" in note

    def test_item_nudge_fires_mid_game(self):
        t = GameTimerTracker()
        reasons = t.check(
            920.0, [None] * 6,
            known_enemy_items={},
            known_enemy_heroes=["npc_dota_hero_antimage"],
        )
        assert "check_enemy_items" in reasons

    def test_item_nudge_skips_early_game(self):
        t = GameTimerTracker()
        reasons = t.check(
            300.0, [None] * 6,
            known_enemy_items={},
            known_enemy_heroes=["npc_dota_hero_antimage"],
        )
        assert "check_enemy_items" not in reasons

    def test_reset_clears_state(self):
        t = GameTimerTracker()
        t.check(155.0, [])
        t.reset()
        reasons = t.check(155.0, [])
        assert "rune_bounty_approaching" in reasons


class TestMissingHeroTracker:
    def test_no_alert_if_never_seen(self):
        m = MissingHeroTracker()
        reasons = m.update(100.0, [], ["npc_dota_hero_antimage"])
        assert reasons == []

    def test_alert_when_hero_disappears(self):
        m = MissingHeroTracker()
        m.update(100.0, ["npc_dota_hero_antimage"], ["npc_dota_hero_antimage"])
        reasons = m.update(110.0, [], ["npc_dota_hero_antimage"])
        assert "hero_missing:npc_dota_hero_antimage" in reasons

    def test_no_double_alert(self):
        m = MissingHeroTracker()
        m.update(100.0, ["npc_dota_hero_antimage"], ["npc_dota_hero_antimage"])
        m.update(110.0, [], ["npc_dota_hero_antimage"])
        reasons = m.update(115.0, [], ["npc_dota_hero_antimage"])
        assert reasons == []

    def test_realert_after_reappearing(self):
        m = MissingHeroTracker()
        m.update(100.0, ["npc_dota_hero_antimage"], ["npc_dota_hero_antimage"])
        m.update(110.0, [], ["npc_dota_hero_antimage"])
        m.update(120.0, ["npc_dota_hero_antimage"], ["npc_dota_hero_antimage"])
        reasons = m.update(130.0, [], ["npc_dota_hero_antimage"])
        assert "hero_missing:npc_dota_hero_antimage" in reasons

    def test_no_alert_before_absence_threshold(self):
        m = MissingHeroTracker()
        m.update(100.0, ["npc_dota_hero_antimage"], ["npc_dota_hero_antimage"])
        reasons = m.update(105.0, [], ["npc_dota_hero_antimage"])
        assert reasons == []

    def test_no_alert_after_recency_window(self):
        m = MissingHeroTracker()
        m.update(100.0, ["npc_dota_hero_antimage"], ["npc_dota_hero_antimage"])
        reasons = m.update(135.0, [], ["npc_dota_hero_antimage"])
        assert reasons == []

    def test_missing_heroes_property(self):
        m = MissingHeroTracker()
        m.update(100.0, ["npc_dota_hero_antimage"], ["npc_dota_hero_antimage"])
        m.update(110.0, [], ["npc_dota_hero_antimage"])
        assert "npc_dota_hero_antimage" in m.missing_heroes

    def test_reset_clears_state(self):
        m = MissingHeroTracker()
        m.update(100.0, ["npc_dota_hero_antimage"], ["npc_dota_hero_antimage"])
        m.update(110.0, [], ["npc_dota_hero_antimage"])
        m.reset()
        assert m.missing_heroes == []

    def test_ignores_negative_clock(self):
        m = MissingHeroTracker()
        assert m.update(-5.0, [], ["npc_dota_hero_antimage"]) == []

    def test_multiple_heroes(self):
        heroes = ["npc_dota_hero_antimage", "npc_dota_hero_invoker"]
        m = MissingHeroTracker()
        m.update(100.0, heroes, heroes)
        reasons = m.update(110.0, [], heroes)
        assert len(reasons) == 2
        ids = {r.split(":", 1)[1] for r in reasons}
        assert ids == set(heroes)
