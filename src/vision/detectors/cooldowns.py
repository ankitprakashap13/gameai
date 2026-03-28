"""Ability cooldown via dark overlay fraction on ability icons."""

from __future__ import annotations

import cv2
import numpy as np

from src.state.models import AbilityCooldownDetection
from src.vision.regions import ABILITY_SLOTS_BASE, scale_rois


class CooldownDetector:
    def __init__(self, dark_threshold: int = 90, cooldown_dark_ratio: float = 0.35) -> None:
        self.dark_threshold = dark_threshold
        self.cooldown_dark_ratio = cooldown_dark_ratio

    def detect(self, frame_bgr: np.ndarray, frame_w: int, frame_h: int) -> list[AbilityCooldownDetection]:
        rois = scale_rois(list(ABILITY_SLOTS_BASE), frame_w, frame_h)
        out: list[AbilityCooldownDetection] = []
        for idx, roi in enumerate(rois):
            patch = frame_bgr[roi.top : roi.top + roi.height, roi.left : roi.left + roi.width]
            if patch.size == 0:
                out.append(AbilityCooldownDetection(ability_index=idx, on_cooldown=False, cooldown_pct=0.0))
                continue
            gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
            dark = (gray < self.dark_threshold).astype(np.float32)
            ratio = float(dark.mean())
            on_cd = ratio >= self.cooldown_dark_ratio
            out.append(
                AbilityCooldownDetection(
                    ability_index=idx,
                    on_cooldown=on_cd,
                    cooldown_pct=min(1.0, ratio / max(self.cooldown_dark_ratio, 0.01)),
                )
            )
        return out
