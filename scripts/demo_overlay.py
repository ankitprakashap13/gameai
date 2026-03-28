#!/usr/bin/env python3
"""
Demo the coaching overlay with fake tips. No Dota, no LLM key needed.

Usage (from project root, with venv activated):
    python scripts/demo_overlay.py

Drag the title bar to move. Use the collapse button to minimize.
Type in the chat box and press Enter to send a message.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from src.overlay.window import CoachOverlayWindow

SAMPLE_TIPS = [
    "Stack the large camp before the 1-minute mark.",
    "Enemy mid is missing -- play safe and check minimap.",
    "You have 2100 gold -- pick up your Blink Dagger now.",
    "Roshan is likely up -- ping your team to take it.",
    "BKB timing is critical this fight -- don't forget to use it.",
    "Ward the enemy jungle entrance for pick-off vision.",
    "Your power spike is now -- group with team and push.",
]

DRAFT_DEMO_TIP = (
    "Draft detected — Your team: Jakiro, Sniper, Ogre Magi, (empty), (empty). "
    "Enemy: Phantom Assassin, Zeus, Witch Doctor, (empty), (empty). "
    "Suggest: pick Axe to counter PA and add frontline for your team."
)


def main() -> int:
    app = QApplication(sys.argv)

    overlay = CoachOverlayWindow(position="top_right")
    overlay.show()

    tip_idx = [0]
    draft_shown = [False]

    def send_next_tip() -> None:
        if not draft_shown[0]:
            overlay.enqueue_tip(DRAFT_DEMO_TIP)
            draft_shown[0] = True
            return
        if tip_idx[0] < len(SAMPLE_TIPS):
            overlay.enqueue_tip(SAMPLE_TIPS[tip_idx[0]])
            tip_idx[0] += 1
        else:
            tip_idx[0] = 0

    def on_user_chat(text: str) -> None:
        QTimer.singleShot(800, lambda: overlay.enqueue_tip(
            f"(demo) Good question about '{text[:40]}' -- in a real game I'd check your state first."
        ))

    overlay.chat_submitted.connect(on_user_chat)

    QTimer.singleShot(300, send_next_tip)
    timer = QTimer()
    timer.timeout.connect(send_next_tip)
    timer.start(8000)

    print("Overlay demo running.")
    print("  First tip simulates draft coaching (hero picks + suggestion).")
    print("  Drag the title bar to move the window.")
    print("  Click the collapse button (-) to minimize.")
    print("  Type in the chat box and press Enter.")
    print("  Ctrl+C to quit.\n")

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
