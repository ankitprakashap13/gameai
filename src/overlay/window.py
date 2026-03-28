"""Always-interactive coaching sidebar: draggable, resizable, always-on-top."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QMainWindow, QWidget

from src.overlay.widgets import CoachPanel


class CoachOverlayWindow(QMainWindow):
    """
    Persistent coaching chat window.
    - Always on top of other windows
    - Draggable via the title bar
    - Resizable by dragging edges
    - Collapsible via the minimize button in the title bar
    - Settings gear for font size, opacity, width, tip frequency
    """

    chat_submitted = pyqtSignal(str)
    frequency_changed = pyqtSignal(int)

    def __init__(
        self,
        position: str = "top_right",
        tip_duration_ms: int = 8000,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._position_key = position

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(240, 120)

        self._panel = CoachPanel(self)
        self._panel.user_message.connect(self._on_user_msg)
        self._panel.frequency_changed.connect(self.frequency_changed.emit)
        self.setCentralWidget(self._panel)

        self._place_window()

    def _place_window(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        margin = 16
        w = min(400, geo.width() // 4)
        h = 260
        if self._position_key == "right_center":
            x = geo.right() - w - margin + 1
            y = geo.top() + (geo.height() - h) // 2
        else:
            x = geo.right() - w - margin + 1
            y = geo.top() + margin
        self.setGeometry(x, y, w, h)

    # -- public API --

    def enqueue_tip(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        self._panel.add_coach_message(text)

    def add_user_message(self, text: str) -> None:
        self._panel.add_user_message(text)

    def _on_user_msg(self, text: str) -> None:
        self._panel.add_user_message(text)
        self.chat_submitted.emit(text)
