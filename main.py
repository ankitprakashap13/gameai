#!/usr/bin/env python3
"""
Dota 2 AI Coach — GSI + vision + LLM + overlay.
Run from project root: python main.py
Requires Dota in borderless windowed; GSI pointed at http://127.0.0.1:3000/
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import QApplication

from src.config_loader import load_config
from src.db.store import Database
from src.gsi.server import create_gsi_app
from src.llm.coach import CoachService
from src.llm.factory import build_llm_provider
from src.overlay.window import CoachOverlayWindow
from src.preflight import run_preflight
from src.state.aggregator import StateAggregator
from src.vision.capture import ScreenCaptureService
from src.vision.pipeline import VisionPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("coach")


class TipBridge(QObject):
    """Thread-safe tip delivery onto the Qt main thread."""

    tip = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()


class AsyncLoopRunner:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_forever, name="AsyncIO", daemon=True)

    def _run_forever(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)

    def submit(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)


def main() -> int:
    root = Path(__file__).resolve().parent
    cfg = load_config(root)

    paths = cfg.get("paths") or {}
    db_path = root / paths.get("db", "dota_gsi.db")
    heroes_dir = root / paths.get("templates_heroes", "assets/templates/heroes")
    items_dir = root / paths.get("templates_items", "assets/templates/items")
    wards_dir = root / paths.get("templates_wards", "assets/templates/wards")
    portraits_dir = root / paths.get("templates_portraits", "assets/templates/portraits")

    for d in (heroes_dir, items_dir, wards_dir, portraits_dir):
        d.mkdir(parents=True, exist_ok=True)

    if not run_preflight(root, cfg):
        return 1

    db = Database(db_path)

    aggregator = StateAggregator(
        db=db,
        history_seconds=float(cfg.get("state", {}).get("history_seconds", 30.0)),
    )

    gsi_cfg = cfg.get("gsi") or {}
    host = str(gsi_cfg.get("host", "127.0.0.1"))
    port = int(gsi_cfg.get("port", 3000))

    flask_app = create_gsi_app(db, on_gsi_payload=aggregator.on_gsi_payload)

    def run_flask() -> None:
        flask_app.run(host=host, port=port, use_reloader=False, threaded=True)

    flask_thread = threading.Thread(target=run_flask, name="FlaskGSI", daemon=True)
    flask_thread.start()
    log.info("GSI server on %s:%d", host, port)

    cap_cfg = cfg.get("capture") or {}
    fps = float(cap_cfg.get("fps", 2.0))
    mon = int(cap_cfg.get("monitor", 0))

    capture = ScreenCaptureService(fps=fps, monitor_index=mon)
    frame_q = capture.get_queue()

    vision = VisionPipeline(
        frame_q,
        heroes_dir=heroes_dir,
        items_dir=items_dir,
        wards_dir=wards_dir,
        portraits_dir=portraits_dir,
        on_vision_state=aggregator.on_vision_state,
        on_draft_state=aggregator.on_draft_state,
    )
    aggregator.attach_vision_pipeline(vision)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    overlay_cfg = cfg.get("overlay") or {}
    overlay = CoachOverlayWindow(
        position=str(overlay_cfg.get("position", "top_right")),
        tip_duration_ms=int(float(overlay_cfg.get("tip_duration_seconds", 8.0)) * 1000),
    )

    bridge = TipBridge()
    bridge.tip.connect(overlay.enqueue_tip, Qt.ConnectionType.QueuedConnection)

    llm_cfg = cfg.get("llm") or {}
    provider = build_llm_provider(cfg)

    coach = CoachService(
        provider=provider,
        db=db,
        get_match_id=lambda: aggregator.match_id,
        throttle_seconds=float(llm_cfg.get("throttle_seconds", 10.0)),
        max_tokens=int(llm_cfg.get("max_tokens", 120)),
        on_tip=lambda t: bridge.tip.emit(t),
    )

    async_runner = AsyncLoopRunner()
    async_runner.start()

    def on_user_chat(question: str) -> None:
        state = aggregator.current()

        async def _ask() -> None:
            reply = await coach.answer_user_question(question, state)
            if reply:
                bridge.tip.emit(reply)

        async_runner.submit(_ask())

    overlay.chat_submitted.connect(on_user_chat, Qt.ConnectionType.QueuedConnection)

    def on_frequency_changed(seconds: int) -> None:
        coach._throttle = max(3.0, float(seconds))
        log.info("Tip frequency changed to %ds", seconds)

    overlay.frequency_changed.connect(on_frequency_changed, Qt.ConnectionType.QueuedConnection)

    def poll_coach() -> None:
        state = aggregator.current()
        async_runner.submit(coach.maybe_generate_tip(state))

    poll_ms = 2000
    timer = QTimer()
    timer.timeout.connect(poll_coach)
    timer.start(poll_ms)

    capture.start()
    vision.start()
    overlay.show()
    log.info("Coach overlay running — capture %.1f FPS, LLM throttle %.0fs", fps, float(llm_cfg.get("throttle_seconds", 10.0)))

    exit_code = app.exec()

    vision.stop()
    capture.stop()
    async_runner.stop()
    db.close()
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
