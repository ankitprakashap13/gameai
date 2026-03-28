"""Run all vision detectors on frames from the capture queue."""

from __future__ import annotations

import logging
import queue
import threading
import time
from pathlib import Path
from typing import Callable

import numpy as np

log = logging.getLogger(__name__)

from src.state.models import VisionState
from src.vision.detectors.cooldowns import CooldownDetector
from src.vision.detectors.health import HealthManaDetector
from src.vision.detectors.items import ItemSlotDetector
from src.vision.detectors.minimap import MinimapHeroDetector


class VisionPipeline:
    def __init__(
        self,
        frame_queue: queue.Queue[tuple[np.ndarray, int, int]],
        heroes_dir: Path | str,
        items_dir: Path | str,
        wards_dir: Path | str | None = None,
        on_vision_state: Callable[[VisionState], None] | None = None,
    ) -> None:
        self._frame_queue = frame_queue
        self._on_vision = on_vision_state
        self._minimap = MinimapHeroDetector(heroes_dir, wards_dir=wards_dir)
        self._items = ItemSlotDetector(items_dir)
        self._health = HealthManaDetector()
        self._cooldowns = CooldownDetector()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="VisionPipeline", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

    def process_one(self, frame_bgr: np.ndarray, w: int, h: int) -> VisionState:
        heroes, wards = self._minimap.detect(frame_bgr, w, h)
        slots = self._items.detect(frame_bgr, w, h)
        hp, mp = self._health.detect(frame_bgr, w, h)
        cds = self._cooldowns.detect(frame_bgr, w, h)
        return VisionState(
            minimap_heroes=heroes,
            minimap_wards=wards,
            item_slots=slots,
            health_pct=hp,
            mana_pct=mp,
            ability_cooldowns=cds,
            frame_width=w,
            frame_height=h,
        )

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                frame_bgr, w, h = self._frame_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                vs = self.process_one(frame_bgr, w, h)
                if self._on_vision:
                    self._on_vision(vs)
            except Exception:
                log.exception("Vision pipeline frame error")
                time.sleep(0.05)
