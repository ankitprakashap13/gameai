"""Health / mana bar fill via HSV color segmentation."""

from __future__ import annotations

import cv2
import numpy as np

from src.vision.regions import HEALTH_BAR_BASE, MANA_BAR_BASE, scale_roi


class HealthManaDetector:
    def __init__(self) -> None:
        pass

    def detect(self, frame_bgr: np.ndarray, frame_w: int, frame_h: int) -> tuple[float | None, float | None]:
        h_roi = scale_roi(HEALTH_BAR_BASE, frame_w, frame_h)
        m_roi = scale_roi(MANA_BAR_BASE, frame_w, frame_h)
        health = self._bar_fill_ratio(frame_bgr, h_roi, mode="health")
        mana = self._bar_fill_ratio(frame_bgr, m_roi, mode="mana")
        return health, mana

    def _bar_fill_ratio(self, frame_bgr: np.ndarray, roi, mode: str) -> float | None:
        patch = frame_bgr[roi.top : roi.top + roi.height, roi.left : roi.left + roi.width]
        if patch.size == 0:
            return None
        hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
        if mode == "health":
            # Green health bar in Dota HUD
            lower = np.array([35, 40, 40])
            upper = np.array([90, 255, 255])
        else:
            # Blue mana
            lower = np.array([90, 40, 40])
            upper = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)
        # Assume fill grows left-to-right: project column density
        col_sum = mask.sum(axis=0)
        total = col_sum.sum()
        if total <= 0:
            return 0.0
        # Last column with significant color ~ right edge of fill
        threshold = max(1.0, 0.15 * mask.shape[0] * 255)
        filled = int((col_sum >= threshold).sum())
        return min(1.0, filled / max(mask.shape[1], 1))
