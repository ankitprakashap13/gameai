"""Inventory item slot template matching."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from src.state.models import ItemSlotDetection
from src.vision.regions import ITEM_SLOT_BASE, scale_rois


class ItemSlotDetector:
    def __init__(
        self,
        items_dir: Path | str,
        match_threshold: float = 0.55,
    ) -> None:
        self.items_dir = Path(items_dir)
        self.match_threshold = match_threshold
        self._templates: list[tuple[str, np.ndarray]] = []
        self._load_templates()

    def _load_templates(self) -> None:
        self._templates.clear()
        if not self.items_dir.is_dir():
            return
        for p in sorted(self.items_dir.glob("*.png")):
            g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
            if g is not None and g.size > 0:
                self._templates.append((p.stem, g))

    def detect(self, frame_bgr: np.ndarray, frame_w: int, frame_h: int) -> list[ItemSlotDetection]:
        rois = scale_rois(list(ITEM_SLOT_BASE), frame_w, frame_h)
        results: list[ItemSlotDetection] = []
        for idx, roi in enumerate(rois):
            patch = frame_bgr[roi.top : roi.top + roi.height, roi.left : roi.left + roi.width]
            if patch.size == 0:
                results.append(ItemSlotDetection(slot_index=idx, item_id=None, confidence=0.0))
                continue
            gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
            best_name: str | None = None
            best_score = 0.0
            for stem, tmpl in self._templates:
                th, tw = tmpl.shape[:2]
                if th > gray.shape[0] or tw > gray.shape[1]:
                    t = cv2.resize(tmpl, (gray.shape[1], gray.shape[0]), interpolation=cv2.INTER_AREA)
                else:
                    t = tmpl
                res = cv2.matchTemplate(gray, t, cv2.TM_CCOEFF_NORMED)
                _min_v, max_v, _min_l, _max_l = cv2.minMaxLoc(res)
                if max_v > best_score:
                    best_score = float(max_v)
                    best_name = stem
            if best_score >= self.match_threshold and best_name:
                results.append(ItemSlotDetection(slot_index=idx, item_id=best_name, confidence=best_score))
            else:
                results.append(ItemSlotDetection(slot_index=idx, item_id=None, confidence=best_score))
        return results
