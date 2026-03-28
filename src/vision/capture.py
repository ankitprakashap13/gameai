"""Background screen capture at limited FPS with a small frame queue."""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Any

import mss
import numpy as np

log = logging.getLogger(__name__)


class ScreenCaptureService:
    """
    Captures monitor to BGR numpy arrays (OpenCV format).
    Drops old frames if queue is full (maxsize=2).
    """

    def __init__(
        self,
        fps: float = 2.0,
        monitor_index: int = 0,
        queue_maxsize: int = 2,
    ) -> None:
        self._fps = max(0.5, float(fps))
        self._monitor_index = monitor_index
        self._queue: queue.Queue[tuple[np.ndarray, int, int]] = queue.Queue(maxsize=queue_maxsize)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="ScreenCapture", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def get_queue(self) -> queue.Queue[tuple[np.ndarray, int, int]]:
        """Queue items: (bgr_image, width, height)."""
        return self._queue

    def _pick_monitor(self, sct: mss.mss) -> dict[str, Any]:
        # mss: monitors[0] is all-in-one; [1] is first physical display
        mons = sct.monitors
        if self._monitor_index <= 0 and len(mons) > 1:
            return mons[1]
        idx = min(max(self._monitor_index, 0), len(mons) - 1)
        return mons[idx]

    def _loop(self) -> None:
        interval = 1.0 / self._fps
        with mss.mss() as sct:
            while not self._stop.is_set():
                t0 = time.perf_counter()
                try:
                    mon = self._pick_monitor(sct)
                    raw = sct.grab(mon)
                    # BGRA -> BGR
                    img = np.asarray(raw, dtype=np.uint8)[:, :, :3]
                    img = img[:, :, ::-1].copy()
                    h, w = img.shape[:2]
                    try:
                        self._queue.put_nowait((img, w, h))
                    except queue.Full:
                        try:
                            self._queue.get_nowait()
                        except queue.Empty:
                            pass
                        try:
                            self._queue.put_nowait((img, w, h))
                        except queue.Full:
                            pass
                except Exception:
                    log.exception("Screen capture frame error")
                elapsed = time.perf_counter() - t0
                sleep_for = interval - elapsed
                if sleep_for > 0:
                    time.sleep(sleep_for)
