"""Hero and ward template matching on minimap ROI."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from src.state.models import HeroMinimapDetection, WardDetection
from src.vision.regions import MINIMAP_BASE, ROI, scale_roi


class MinimapHeroDetector:
    def __init__(
        self,
        heroes_dir: Path | str,
        wards_dir: Path | str | None = None,
        match_threshold: float = 0.65,
        scale_match: float = 0.5,
    ) -> None:
        self.heroes_dir = Path(heroes_dir)
        self.wards_dir = Path(wards_dir) if wards_dir else None
        self.match_threshold = match_threshold
        self.scale_match = scale_match
        self._hero_templates: list[tuple[str, np.ndarray]] = []
        self._ward_templates: list[tuple[str, np.ndarray]] = []
        self._load_templates()

    def _load_gray(self, path: Path) -> np.ndarray | None:
        return cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)

    def _load_templates(self) -> None:
        self._hero_templates.clear()
        if self.heroes_dir.is_dir():
            for p in sorted(self.heroes_dir.glob("*.png")):
                g = self._load_gray(p)
                if g is not None and g.size > 0:
                    self._hero_templates.append((p.stem, g))
        self._ward_templates.clear()
        if self.wards_dir and self.wards_dir.is_dir():
            for p in sorted(self.wards_dir.glob("*.png")):
                g = self._load_gray(p)
                if g is not None and g.size > 0:
                    self._ward_templates.append((p.stem, g))

    def detect(
        self,
        frame_bgr: np.ndarray,
        frame_w: int,
        frame_h: int,
    ) -> tuple[list[HeroMinimapDetection], list[WardDetection]]:
        roi = scale_roi(MINIMAP_BASE, frame_w, frame_h)
        patch = frame_bgr[roi.top : roi.top + roi.height, roi.left : roi.left + roi.width]
        if patch.size == 0:
            return [], []

        gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
        sm = self.scale_match
        gray_small = cv2.resize(gray, None, fx=sm, fy=sm, interpolation=cv2.INTER_AREA) if sm != 1.0 else gray

        heroes = self._match_heroes(gray_small, roi, frame_w, frame_h, sm)
        wards = self._match_wards(gray_small, roi, frame_w, frame_h, sm)
        return heroes, wards

    def _to_norm(self, roi: ROI, x_small: float, y_small: float, frame_w: int, frame_h: int, sm: float) -> tuple[float, float]:
        """Convert template top-left in scaled minimap to normalized frame coords."""
        x_patch = x_small / sm
        y_patch = y_small / sm
        abs_x = roi.left + x_patch
        abs_y = roi.top + y_patch
        return abs_x / max(frame_w, 1), abs_y / max(frame_h, 1)

    def _match_heroes(
        self,
        gray_small: np.ndarray,
        roi: ROI,
        frame_w: int,
        frame_h: int,
        sm: float,
    ) -> list[HeroMinimapDetection]:
        out: list[HeroMinimapDetection] = []
        h_m, w_m = gray_small.shape[:2]
        used: list[tuple[int, int, int, int]] = []

        for stem, tmpl in self._hero_templates:
            t_small = (
                cv2.resize(tmpl, None, fx=sm, fy=sm, interpolation=cv2.INTER_AREA) if sm != 1.0 else tmpl
            )
            ths, tws = t_small.shape[:2]
            if ths >= h_m or tws >= w_m:
                continue
            res = cv2.matchTemplate(gray_small, t_small, cv2.TM_CCOEFF_NORMED)
            _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(res)
            if max_val < self.match_threshold:
                continue
            x, y = max_loc
            box = (x, y, tws, ths)
            if any(self._iou(box, b) > 0.3 for b in used):
                continue
            used.append(box)
            cx = x + tws / 2
            cy = y + ths / 2
            x_norm, y_norm = self._to_norm(roi, cx, cy, frame_w, frame_h, sm)
            out.append(
                HeroMinimapDetection(
                    hero_id=stem,
                    x_norm=float(max(0.0, min(1.0, x_norm))),
                    y_norm=float(max(0.0, min(1.0, y_norm))),
                    confidence=float(max_val),
                )
            )
        return out

    def _match_wards(
        self,
        gray_small: np.ndarray,
        roi: ROI,
        frame_w: int,
        frame_h: int,
        sm: float,
    ) -> list[WardDetection]:
        out: list[WardDetection] = []
        h_m, w_m = gray_small.shape[:2]
        for stem, tmpl in self._ward_templates:
            t_small = (
                cv2.resize(tmpl, None, fx=sm, fy=sm, interpolation=cv2.INTER_AREA) if sm != 1.0 else tmpl
            )
            ths, tws = t_small.shape[:2]
            if ths >= h_m or tws >= w_m:
                continue
            res = cv2.matchTemplate(gray_small, t_small, cv2.TM_CCOEFF_NORMED)
            _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(res)
            if max_val < self.match_threshold:
                continue
            x, y = max_loc
            cx = x + tws / 2
            cy = y + ths / 2
            x_norm, y_norm = self._to_norm(roi, cx, cy, frame_w, frame_h, sm)
            kind = (
                "observer"
                if "observer" in stem.lower()
                else "sentry"
                if "sentry" in stem.lower()
                else stem
            )
            out.append(
                WardDetection(
                    kind=kind,
                    x_norm=float(max(0.0, min(1.0, x_norm))),
                    y_norm=float(max(0.0, min(1.0, y_norm))),
                    confidence=float(max_val),
                )
            )
        return out

    @staticmethod
    def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        x1 = max(ax, bx)
        y1 = max(ay, by)
        x2 = min(ax + aw, bx + bw)
        y2 = min(ay + ah, by + bh)
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        union = aw * ah + bw * bh - inter
        return inter / union if union else 0.0
