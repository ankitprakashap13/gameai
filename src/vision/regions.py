"""Screen ROIs for 1920x1080 baseline; scale for other resolutions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ROI:
    """Rectangle in pixels: left, top, width, height (absolute to full frame)."""

    left: int
    top: int
    width: int
    height: int


# Baseline 1920x1080 — approximate Dota 2 HUD (may need user tuning)
BASE_W = 1920
BASE_H = 1080

# Draft / pick screen: full-width top bar with team portraits (1080p baseline).
# height=48 captures just the portrait art; the player names sit below.
DRAFT_TOP_BAR_BASE = ROI(left=0, top=8, width=1920, height=48)

# Minimap: bottom-left
MINIMAP_BASE = ROI(left=0, top=820, width=280, height=260)

# Six inventory slots (bottom center); approximate positions
ITEM_SLOT_BASE: list[ROI] = [
    ROI(left=800 + i * 58, top=1000, width=52, height=38)
    for i in range(6)
]

# Self hero portrait area — health/mana often near portrait; use bars above center-bottom
HEALTH_BAR_BASE = ROI(left=700, top=980, width=200, height=12)
MANA_BAR_BASE = ROI(left=700, top=996, width=200, height=10)

# Ability slots Q W E D F R — six icons
ABILITY_SLOTS_BASE: list[ROI] = [
    ROI(left=900 + i * 52, top=1000, width=46, height=46)
    for i in range(6)
]


def scale_roi(roi: ROI, frame_w: int, frame_h: int) -> ROI:
    sx = frame_w / BASE_W
    sy = frame_h / BASE_H
    return ROI(
        left=int(roi.left * sx),
        top=int(roi.top * sy),
        width=max(1, int(roi.width * sx)),
        height=max(1, int(roi.height * sy)),
    )


def scale_rois(rois: list[ROI], frame_w: int, frame_h: int) -> list[ROI]:
    return [scale_roi(r, frame_w, frame_h) for r in rois]
