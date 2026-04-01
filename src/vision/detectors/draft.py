"""Draft screen: contour-based slot detection + diff-based change tracking.

Portrait slots are found dynamically using OpenCV contours on the top bar
of the frame.  A binary threshold separates the bright hero art from the
dark slanted borders.  The bounding rectangles of the resulting contours
give resolution- and aspect-ratio-independent slot positions — no
hardcoded coordinates needed.

If contour detection cannot locate exactly ~10 portrait tiles (e.g. on
a synthetic test frame), the detector falls back to pre-calibrated ratio
profiles for common aspect ratios (16:9, 4:3).

On every frame during HERO_SELECTION:
  1. On the FIRST frame, detect slot positions via contours (or fallback).
  2. Template-match all 10 slots.
  3. On subsequent frames, diff each slot against its previous crop.
  4. Only re-match slots whose pixels changed significantly.
  5. Build up a running hero list incrementally.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from src.state.models import DraftHeroPick, DraftState

log = logging.getLogger(__name__)

_DEFAULT_MATCH_THRESHOLD = 0.35
_DIFF_THRESHOLD = 12.0
_SLOTS_PER_TEAM = 5

# Height fraction of the frame to crop as the portrait top-bar region.
_TOP_BAR_FRAC = 0.08

# Threshold sweep range for contour detection.
_THRESH_LO = 40
_THRESH_HI = 70

# Inset fraction applied to each contour bounding rect to get the
# inscribed rectangle (avoids residual slant-border pixels).
_INSET_FRAC = 0.05

# ---------------------------------------------------------------------------
# Fallback ratio profiles for when contour detection fails.
# Pixel coords at a reference resolution, divided to get decimal ratios.
# ---------------------------------------------------------------------------

_FALLBACK_PROFILES: dict[str, dict] = {
    "16:9": {
        "aspect": 16 / 9,
        "ref": (1920, 1080),
        "radiant": [
            (360, 0, 65, 75), (460, 0, 65, 75), (560, 0, 65, 75),
            (660, 0, 65, 75), (760, 0, 65, 75),
        ],
        "dire": [
            (1095, 0, 65, 75), (1195, 0, 65, 75), (1295, 0, 65, 75),
            (1395, 0, 65, 75), (1495, 0, 65, 75),
        ],
    },
    "4:3": {
        "aspect": 4 / 3,
        "ref": (1024, 767),
        "radiant": [
            (63, 6, 54, 36), (127, 6, 54, 36), (191, 6, 54, 36),
            (255, 6, 54, 36), (319, 6, 54, 36),
        ],
        "dire": [
            (646, 6, 54, 36), (710, 6, 54, 36), (774, 6, 54, 36),
            (837, 6, 54, 36), (901, 6, 54, 36),
        ],
    },
}


def _fallback_slots(
    frame_w: int, frame_h: int,
) -> tuple[list[tuple[int, int, int, int]], list[tuple[int, int, int, int]]]:
    """Scale the closest fallback ratio profile to the frame resolution."""
    aspect = frame_w / frame_h
    profile = min(
        _FALLBACK_PROFILES.values(), key=lambda p: abs(p["aspect"] - aspect),
    )
    rw, rh = profile["ref"]
    sx, sy = frame_w / rw, frame_h / rh

    def scale(slots: list) -> list[tuple[int, int, int, int]]:
        return [
            (int(x * sx), int(y * sy), max(1, int(w * sx)), max(1, int(h * sy)))
            for x, y, w, h in slots
        ]

    return scale(profile["radiant"]), scale(profile["dire"])


# ---------------------------------------------------------------------------
# Contour-based slot detection
# ---------------------------------------------------------------------------

def _detect_slots_by_contour(
    frame_bgr: np.ndarray,
    frame_w: int,
    frame_h: int,
) -> tuple[list[tuple[int, int, int, int]], list[tuple[int, int, int, int]]] | None:
    """Find portrait slots via binary threshold + contour bounding rects.

    Sweeps thresholds to find the value yielding ~10 consistently-sized
    portrait rectangles.  Returns (radiant_slots, dire_slots) or None.
    """
    bar_h = max(10, int(frame_h * _TOP_BAR_FRAC))
    top_bar = frame_bgr[0:bar_h, :]
    gray = cv2.cvtColor(top_bar, cv2.COLOR_BGR2GRAY)
    th, tw = gray.shape[:2]

    min_w = tw * 0.03
    min_h = th * 0.35
    max_w = tw * 0.15

    best_score = float("inf")
    best_rects: list[tuple[int, int, int, int]] = []

    for t in range(_THRESH_LO, _THRESH_HI + 1):
        _, binary = cv2.threshold(gray, t, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
        )
        rects: list[tuple[int, int, int, int]] = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w >= min_w and h >= min_h and w < max_w:
                rects.append((x, y, w, h))

        n = len(rects)
        if n < 8 or n > 12:
            continue

        widths = [r[2] for r in rects]
        std_w = float(np.std(widths))
        score = abs(n - 10) * 100 + std_w
        if score < best_score:
            best_score = score
            best_rects = sorted(rects, key=lambda r: r[0])

    if len(best_rects) < 8:
        return None

    # Normalize to a consistent y and height across all slots.
    # Some heroes have darker art that produces shorter contours;
    # use the median y / height so every tile is the same size.
    # Then trim ~12% off the bottom to drop the grey player-name bar.
    all_ys = [r[1] for r in best_rects]
    all_hs = [r[3] for r in best_rects]
    norm_y = int(np.median(all_ys))
    norm_h = int(np.median(all_hs) * 0.88)
    best_rects = [(x, norm_y, w, norm_h) for x, _, w, _ in best_rects]

    mid_x = frame_w // 2
    left = [r for r in best_rects if r[0] + r[2] / 2 < mid_x]
    right = [r for r in best_rects if r[0] + r[2] / 2 >= mid_x]

    if len(left) < 3 or len(right) < 3:
        return None

    def inset(rects: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
        out: list[tuple[int, int, int, int]] = []
        for x, y, w, h in rects:
            ix = int(x + w * _INSET_FRAC)
            iy = int(y + h * _INSET_FRAC)
            iw = max(1, int(w * (1 - 2 * _INSET_FRAC)))
            ih = max(1, int(h * (1 - 2 * _INSET_FRAC)))
            out.append((ix, iy, iw, ih))
        return out

    return inset(left[:_SLOTS_PER_TEAM]), inset(right[:_SLOTS_PER_TEAM])


class DraftPortraitDetector:
    def __init__(
        self,
        portraits_dir: Path | str,
        fallback_heroes_dir: Path | str | None = None,
        match_threshold: float = _DEFAULT_MATCH_THRESHOLD,
        diff_threshold: float = _DIFF_THRESHOLD,
        debug_dir: Path | str | None = None,
    ) -> None:
        self.portraits_dir = Path(portraits_dir)
        self.fallback_heroes_dir = (
            Path(fallback_heroes_dir) if fallback_heroes_dir else None
        )
        self.match_threshold = match_threshold
        self.diff_threshold = diff_threshold
        self._debug_dir: Path | None = Path(debug_dir) if debug_dir else None
        self._frame_counter = 0
        self._templates: list[tuple[str, np.ndarray]] = []
        self._load_templates()

        self._prev_frame: np.ndarray | None = None
        self._r_slots: list[tuple[int, int, int, int]] = []
        self._d_slots: list[tuple[int, int, int, int]] = []
        self._radiant_picks: list[DraftHeroPick] = []
        self._dire_picks: list[DraftHeroPick] = []

    # -- public API --

    def reset(self) -> None:
        """Clear all cached state.  Call when a draft starts or ends."""
        self._prev_frame = None
        self._r_slots = []
        self._d_slots = []
        self._radiant_picks = []
        self._dire_picks = []
        self._frame_counter = 0
        if self._debug_dir:
            self._debug_dir.mkdir(parents=True, exist_ok=True)

    def detect(
        self,
        frame_bgr: np.ndarray,
        frame_w: int,
        frame_h: int,
        player_team: str | None = None,
    ) -> DraftState | None:
        if not self._templates:
            return None

        if not self._r_slots:
            result = _detect_slots_by_contour(frame_bgr, frame_w, frame_h)
            if result is not None:
                self._r_slots, self._d_slots = result
                log.info("Slot detection via contours: R=%s D=%s",
                         self._r_slots, self._d_slots)
            else:
                self._r_slots, self._d_slots = _fallback_slots(frame_w, frame_h)
                log.info("Contour detection failed; using fallback ratios: R=%s D=%s",
                         self._r_slots, self._d_slots)

        if self._prev_frame is None:
            return self._full_detect(frame_bgr, player_team)
        return self._diff_detect(frame_bgr, player_team)

    # -- template loading --

    def _load_templates(self) -> None:
        self._templates.clear()
        paths: list[Path] = []
        if self.portraits_dir.is_dir():
            paths.extend(sorted(self.portraits_dir.glob("*.png")))
        if (
            not paths
            and self.fallback_heroes_dir
            and self.fallback_heroes_dir.is_dir()
        ):
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

    # -- cropping --

    @staticmethod
    def _crop_slot(
        frame: np.ndarray,
        slot: tuple[int, int, int, int],
    ) -> np.ndarray:
        """Crop a single portrait slot from the full frame."""
        x, y, w, h = slot
        fh, fw = frame.shape[:2]
        x1 = max(0, min(x, fw - 1))
        y1 = max(0, min(y, fh - 1))
        x2 = max(x1 + 1, min(x + w, fw))
        y2 = max(y1 + 1, min(y + h, fh))
        return frame[y1:y2, x1:x2]

    # -- detection pipeline --

    def _full_detect(
        self,
        frame: np.ndarray,
        player_team: str | None,
    ) -> DraftState:
        """First-frame: template-match all 10 slots."""
        log.info(
            "Draft full detect (frame %d): radiant=%s, dire=%s",
            self._frame_counter, self._r_slots, self._d_slots,
        )

        self._radiant_picks = self._match_slots(frame, "radiant", self._r_slots)
        self._dire_picks = self._match_slots(frame, "dire", self._d_slots)

        self._prev_frame = frame.copy()
        self._frame_counter += 1
        self._save_debug(frame)
        return self._build_state(player_team)

    def _diff_detect(
        self,
        frame: np.ndarray,
        player_team: str | None,
    ) -> DraftState:
        """Diff each slot against its previous crop; only re-match changed."""
        assert self._prev_frame is not None

        for slots, picks, team in [
            (self._r_slots, self._radiant_picks, "radiant"),
            (self._d_slots, self._dire_picks, "dire"),
        ]:
            for idx, slot in enumerate(slots):
                if idx >= len(picks):
                    continue
                curr = self._crop_slot(frame, slot)
                prev = self._crop_slot(self._prev_frame, slot)
                if curr.shape != prev.shape:
                    prev = cv2.resize(prev, (curr.shape[1], curr.shape[0]))

                diff = cv2.absdiff(curr, prev)
                gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                mean_change = float(np.mean(gray_diff))
                if mean_change < self.diff_threshold:
                    continue

                best_id, best_score = self._best_template_match(curr)
                hero = best_id if best_score >= self.match_threshold else None
                old_hero = picks[idx].hero_id
                picks[idx] = DraftHeroPick(
                    slot_index=idx,
                    hero_id=hero,
                    confidence=float(best_score),
                    team=team,
                )
                if hero != old_hero:
                    log.info(
                        "Slot %s-%d changed: %s -> %s (diff=%.1f, conf=%.3f)",
                        team, idx, old_hero, hero, mean_change, best_score,
                    )
                    self._save_debug_slot(
                        frame, team, idx, slot, hero, best_score,
                    )

        self._prev_frame = frame.copy()
        self._frame_counter += 1
        return self._build_state(player_team)

    def _build_state(self, player_team: str | None) -> DraftState:
        pt = (player_team or "radiant").lower()
        if pt == "dire":
            return DraftState(
                ally_picks=list(self._dire_picks),
                enemy_picks=list(self._radiant_picks),
            )
        return DraftState(
            ally_picks=list(self._radiant_picks),
            enemy_picks=list(self._dire_picks),
        )

    def _match_slots(
        self,
        frame: np.ndarray,
        team: str,
        slots: list[tuple[int, int, int, int]],
    ) -> list[DraftHeroPick]:
        picks: list[DraftHeroPick] = []
        for idx, slot in enumerate(slots):
            patch = self._crop_slot(frame, slot)
            if patch.size == 0:
                picks.append(
                    DraftHeroPick(
                        slot_index=idx,
                        hero_id=None,
                        confidence=0.0,
                        team=team,
                    )
                )
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
        while len(picks) < _SLOTS_PER_TEAM:
            picks.append(
                DraftHeroPick(
                    slot_index=len(picks),
                    hero_id=None,
                    confidence=0.0,
                    team=team,
                )
            )
        return picks[:_SLOTS_PER_TEAM]

    def _best_template_match(
        self,
        patch_bgr: np.ndarray,
    ) -> tuple[str | None, float]:
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

    # -- debug image saving --

    def _save_debug(self, frame: np.ndarray) -> None:
        if not self._debug_dir:
            return
        try:
            f = self._frame_counter
            fh = frame.shape[0]
            all_slots = self._r_slots + self._d_slots
            if not all_slots:
                return
            max_y = max(y + h for _, y, _, h in all_slots)
            strip = frame[0 : min(max_y + 20, fh), :]
            ann = strip.copy()

            for slots, picks, color, team in [
                (self._r_slots, self._radiant_picks, (0, 255, 0), "radiant"),
                (self._d_slots, self._dire_picks, (0, 0, 255), "dire"),
            ]:
                for idx, (x, y, w, h) in enumerate(slots):
                    cv2.rectangle(ann, (x, y), (x + w, y + h), color, 2)
                    hero = picks[idx].hero_id if idx < len(picks) else None
                    conf = picks[idx].confidence if idx < len(picks) else 0.0
                    label = hero or "empty"
                    tile = self._crop_slot(frame, (x, y, w, h))
                    if tile.size > 0:
                        cv2.imwrite(
                            str(
                                self._debug_dir
                                / f"frame{f:04d}_{team}{idx}_{label}_{conf:.2f}.png"
                            ),
                            tile,
                        )

            cv2.imwrite(
                str(self._debug_dir / f"frame{f:04d}_topbar.png"), strip,
            )
            cv2.imwrite(
                str(self._debug_dir / f"frame{f:04d}_annotated.png"), ann,
            )
        except Exception:
            log.debug("Failed to save debug images", exc_info=True)

    def _save_debug_slot(
        self,
        frame: np.ndarray,
        team: str,
        idx: int,
        slot: tuple[int, int, int, int],
        hero: str | None,
        conf: float,
    ) -> None:
        if not self._debug_dir:
            return
        try:
            f = self._frame_counter
            label = hero or "empty"
            tile = self._crop_slot(frame, slot)
            if tile.size > 0:
                cv2.imwrite(
                    str(
                        self._debug_dir
                        / f"frame{f:04d}_{team}{idx}_{label}_{conf:.2f}.png"
                    ),
                    tile,
                )
        except Exception:
            log.debug("Failed to save debug slot image", exc_info=True)
