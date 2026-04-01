"""Smoke tests for draft portrait detector."""

from pathlib import Path

import cv2
import numpy as np

from src.vision.detectors.draft import DraftPortraitDetector


def test_draft_detector_runs_with_fallback_templates(tmp_path: Path) -> None:
    heroes = tmp_path / "heroes"
    heroes.mkdir(parents=True)
    img = np.zeros((16, 16, 3), dtype=np.uint8)
    img[:, :] = (40, 80, 120)
    cv2.imwrite(str(heroes / "npc_dota_hero_axe.png"), img)

    det = DraftPortraitDetector(tmp_path / "portraits", fallback_heroes_dir=heroes)
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    frame[8:56, :] = 60

    out = det.detect(frame, 1920, 1080, player_team="radiant")
    assert out is not None
    assert len(out.ally_picks) == 5
    assert len(out.enemy_picks) == 5
    assert all(p.team == "radiant" for p in out.ally_picks)
    assert all(p.team == "dire" for p in out.enemy_picks)


def test_draft_detector_swaps_ally_for_dire_player(tmp_path: Path) -> None:
    heroes = tmp_path / "heroes"
    heroes.mkdir(parents=True)
    cv2.imwrite(str(heroes / "npc_dota_hero_axe.png"), np.full((8, 8, 3), 99, dtype=np.uint8))

    det = DraftPortraitDetector(tmp_path / "portraits", fallback_heroes_dir=heroes)
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    out_r = det.detect(frame, 1920, 1080, player_team="radiant")
    out_d = det.detect(frame, 1920, 1080, player_team="dire")
    assert out_r is not None and out_d is not None
    # Ally picks should be tagged with the player's team in each DraftHeroPick
    assert all(p.team == "radiant" for p in out_r.ally_picks)
    assert all(p.team == "dire" for p in out_d.ally_picks)
