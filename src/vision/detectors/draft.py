"""Draft screen: segment top-bar portrait slots and template-match hero portraits."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np
from scipy.signal import find_peaks

from src.state.models import DraftHeroPick, DraftState
from src.vision.regions import DRAFT_TOP_BAR_BASE, scale_roi

log = logging.getLogger(__name__)

# Baseline (1080p) — minimum slot width in pixels before scaling
_MIN_SLOT_WIDTH_BASE = 28
# Plan default: empty slot if best match below this
_DEFAULT_MATCH_THRESHOLD = 0.35
# find_peaks on inverted column brightness (dark dividers between portraits)
_PEAK_DISTANCE_BASE = 40
_PEAK_PROMINENCE_BASE = 5.0


class DraftPortraitDetector:
    """
    Crop the draft top bar, find vertical slot boundaries via brightness valleys,
    split radiant (left) / dire (right), then match each slot against portrait templates.
    """

    def __init__(
        self,
        portraits_dir: Path | str,
        fallback_heroes_dir: Path | str | None = None,
        match_threshold: float = _DEFAULT_MATCH_THRESHOLD,
    ) -> None:
        self.portraits_dir = Path(portraits_dir)
        self.fallback_heroes_dir = Path(fallback_heroes_dir) if fallback_heroes_dir else None
        self.match_threshold = match_threshold
        self._templates: list[tuple[str, np.ndarray]] = []
        self._load_templates()

    def _load_templates(self) -> None:
        self._templates.clear()
        paths: list[Path] = []
        if self.portraits_dir.is_dir():
            paths.extend(sorted(self.portraits_dir.glob("*.png")))
        if not paths and self.fallback_heroes_dir and self.fallback_heroes_dir.is_dir():
            paths = sorted(self.fallback_heroes_dir.glob("*.png"))

        for p in paths:
            img = cv2.imread(str(p), cv2.IMREAD_COLOR)
            if img is None or img.size == 0:
                g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
                if g is None or g.size == 0:
                    continue
                img = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
            self._templates.append((p.stem, img))

        if not self._templates:
            log.warning(
                "DraftPortraitDetector: no PNG templates in %s or fallback %s",
                self.portraits_dir,
                self.fallback_heroes_dir,
            )

    def detect(
        self,
        frame_bgr: np.ndarray,
        frame_w: int,
        frame_h: int,
        player_team: str | None = None,
    ) -> DraftState | None:
        if not self._templates:
            return None

        roi = scale_roi(DRAFT_TOP_BAR_BASE, frame_w, frame_h)
        x1 = max(0, roi.left)
        y1 = max(0, roi.top)
        x2 = min(frame_w, roi.left + roi.width)
        y2 = min(frame_h, roi.top + roi.height)
        if x2 <= x1 or y2 <= y1:
            return None

        strip = frame_bgr[y1:y2, x1:x2]
        gray = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
        h_s, w_s = gray.shape[:2]
        if w_s < 100 or h_s < 10:
            return None

        sx = frame_w / 1920.0
        min_slot_w = max(8, int(_MIN_SLOT_WIDTH_BASE * sx))
        peak_distance = max(12, int(_PEAK_DISTANCE_BASE * sx))
        peak_prominence = max(1.0, float(_PEAK_PROMINENCE_BASE * sx))

        col_profile = np.mean(gray.astype(np.float32), axis=0)
        peaks, _ = find_peaks(-col_profile, distance=peak_distance, prominence=peak_prominence)

        boundaries = [0] + sorted(int(p) for p in peaks) + [w_s]
        segments: list[tuple[int, int]] = []
        for i in range(len(boundaries) - 1):
            a, b = boundaries[i], boundaries[i + 1]
            if b - a >= min_slot_w:
                segments.append((a, b))

        if not segments:
            segments = self._uniform_slots(w_s, 10, min_slot_w)

        mid = w_s / 2.0
        left_segs = [s for s in segments if (s[0] + s[1]) / 2.0 < mid]
        right_segs = [s for s in segments if (s[0] + s[1]) / 2.0 >= mid]
        left_segs.sort(key=lambda t: t[0])
        right_segs.sort(key=lambda t: t[0])

        left_pick = self._pick_side_slots(left_segs, 5)
        right_pick = self._pick_side_slots(right_segs, 5)

        radiant_picks = self._match_slots(strip, "radiant", left_pick)
        dire_picks = self._match_slots(strip, "dire", right_pick)

        pt = (player_team or "radiant").lower()
        if pt == "dire":
            ally_picks, enemy_picks = dire_picks, radiant_picks
        else:
            ally_picks, enemy_picks = radiant_picks, dire_picks

        return DraftState(ally_picks=ally_picks, enemy_picks=enemy_picks)

    def _uniform_slots(self, width: int, n: int, min_w: int) -> list[tuple[int, int]]:
        step = width / n
        out: list[tuple[int, int]] = []
        for i in range(n):
            a = int(round(i * step))
            b = int(round((i + 1) * step))
            if b - a >= min_w:
                out.append((a, b))
        return out

    def _pick_side_slots(self, segments: list[tuple[int, int]], want: int) -> list[tuple[int, int]]:
        if len(segments) <= want:
            return segments
        by_width = sorted(segments, key=lambda t: t[1] - t[0], reverse=True)
        chosen = by_width[:want]
        chosen.sort(key=lambda t: t[0])
        return chosen

    def _match_slots(
        self,
        strip_bgr: np.ndarray,
        team: str,
        slot_bounds: list[tuple[int, int]],
    ) -> list[DraftHeroPick]:
        picks: list[DraftHeroPick] = []
        for idx, (xa, xb) in enumerate(slot_bounds):
            patch = strip_bgr[:, xa:xb]
            if patch.size == 0:
                picks.append(DraftHeroPick(slot_index=idx, hero_id=None, confidence=0.0, team=team))
                continue
            best_id, best_score = self._best_template_match(patch)
            hero = best_id if best_score >= self.match_threshold else None
            picks.append(
                DraftHeroPick(
                    slot_index=idx,
                    hero_id=hero,
                    confidence=float(best_score),
                    team=team,
                )
            )
        while len(picks) < 5:
            picks.append(DraftHeroPick(slot_index=len(picks), hero_id=None, confidence=0.0, team=team))
        return picks[:5]

    def _best_template_match(self, patch_bgr: np.ndarray) -> tuple[str | None, float]:
        ph, pw = patch_bgr.shape[:2]
        if ph < 4 or pw < 4:
            return None, 0.0
        best_name: str | None = None
        best_val = -1.0
        for name, tmpl in self._templates:
            th, tw = tmpl.shape[:2]
            if th < 1 or tw < 1:
                continue
            resized = cv2.resize(tmpl, (pw, ph), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(patch_bgr, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val > best_val:
                best_val = float(max_val)
                best_name = name
        return best_name, best_val
