"""Detect enemy items from the HUD inspection panel when the player clicks an enemy."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from src.state.models import EnemyItemSnapshot
from src.vision.regions import (
    ENEMY_INSPECT_ITEM_SLOTS_BASE,
    ENEMY_INSPECT_PANEL_BASE,
    ROI,
    scale_roi,
    scale_rois,
)

log = logging.getLogger(__name__)

_PANEL_BRIGHTNESS_THRESHOLD = 35
_ITEM_MATCH_THRESHOLD = 0.50


class EnemyInspectDetector:
    """Reads enemy items from the unit inspection panel on the HUD.

    The panel appears when the player left-clicks on an enemy hero.
    This detector first checks whether the panel region is "active"
    (non-dark, meaning something is displayed there), and only then
    runs item template matching on the 6 item slots.

    NOTE: The ROI coordinates in regions.py are approximate 1080p guesses
    and MUST be calibrated with a real in-game screenshot.
    """

    def __init__(self, items_dir: Path | str, match_threshold: float = _ITEM_MATCH_THRESHOLD) -> None:
        self._items_dir = Path(items_dir)
        self._threshold = match_threshold
        self._templates: list[tuple[str, np.ndarray]] = []
        self._load_templates()

    def _load_templates(self) -> None:
        self._templates.clear()
        if not self._items_dir.is_dir():
            return
        for p in sorted(self._items_dir.glob("*.png")):
            g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
            if g is not None and g.size > 0:
                self._templates.append((p.stem, g))

    def detect(self, frame_bgr: np.ndarray, frame_w: int, frame_h: int) -> EnemyItemSnapshot | None:
        panel = scale_roi(ENEMY_INSPECT_PANEL_BASE, frame_w, frame_h)
        panel_region = frame_bgr[panel.top : panel.top + panel.height, panel.left : panel.left + panel.width]

        if panel_region.size == 0:
            return None

        if not self._is_panel_active(panel_region):
            return None

        slot_rois = scale_rois(list(ENEMY_INSPECT_ITEM_SLOTS_BASE), frame_w, frame_h)
        items: list[str] = []
        for roi in slot_rois:
            patch = frame_bgr[roi.top : roi.top + roi.height, roi.left : roi.left + roi.width]
            if patch.size == 0:
                continue
            item_id = self._match_item(patch)
            if item_id:
                items.append(item_id)

        if not items:
            return None

        return EnemyItemSnapshot(hero_id="unknown", items=items)

    @staticmethod
    def _is_panel_active(region: np.ndarray) -> bool:
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        return float(gray.mean()) > _PANEL_BRIGHTNESS_THRESHOLD

    def _match_item(self, patch_bgr: np.ndarray) -> str | None:
        gray = cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2GRAY)
        best_name: str | None = None
        best_score = 0.0
        for stem, tmpl in self._templates:
            th, tw = tmpl.shape[:2]
            if th > gray.shape[0] or tw > gray.shape[1]:
                t = cv2.resize(tmpl, (gray.shape[1], gray.shape[0]), interpolation=cv2.INTER_AREA)
            else:
                t = tmpl
            res = cv2.matchTemplate(gray, t, cv2.TM_CCOEFF_NORMED)
            _, max_v, _, _ = cv2.minMaxLoc(res)
            if max_v > best_score:
                best_score = float(max_v)
                best_name = stem
        if best_score >= self._threshold and best_name:
            return best_name
        return None
