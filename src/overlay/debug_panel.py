"""Debug panel: live GSI state, system stats, and scrollable log viewer."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
)

_FONT = "'.AppleSystemUIFont', 'Segoe UI', sans-serif"
_MONO = "'SF Mono', 'Consolas', 'Menlo', monospace"

_PANEL_CSS = """
QFrame#debugPanel {
    background: rgba(12, 12, 18, 245);
    border-top: 1px solid rgba(255, 255, 255, 10);
    border-bottom-left-radius: 14px;
    border-bottom-right-radius: 14px;
}
"""

_SECTION_HEADER_CSS = f"""
    color: rgba(100, 220, 160, 200);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
    font-family: {_FONT};
    padding: 2px 0;
"""

_KV_LABEL_CSS = f"""
    color: rgba(140, 140, 165, 180);
    font-size: 10px;
    font-family: {_FONT};
"""

_KV_VALUE_CSS = f"""
    color: rgba(200, 210, 255, 220);
    font-size: 10px;
    font-weight: 600;
    font-family: {_FONT};
"""

_LOG_CSS = f"""
QPlainTextEdit {{
    background: rgba(8, 8, 14, 200);
    color: rgba(170, 175, 190, 200);
    font-size: 9px;
    font-family: {_MONO};
    border: 1px solid rgba(255, 255, 255, 8);
    border-radius: 6px;
    padding: 4px;
    selection-background-color: rgba(80, 120, 220, 100);
}}
QScrollBar:vertical {{
    width: 4px; background: transparent;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 30); border-radius: 2px; min-height: 16px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
"""

_MAX_LOG_LINES = 200


# -- data model for updates --

@dataclass
class DebugSnapshot:
    hero: str = ""
    game_state: str = ""
    gold: str = ""
    level: str = ""
    kda: str = ""
    game_time: str = ""
    team: str = ""
    score: str = ""
    items: str = ""
    llm_calls: int = 0
    llm_chats: int = 0
    llm_avg_ms: int = 0
    llm_last_reason: str = ""
    vision_mode: str = "idle"
    capture_fps: str = ""
    gsi_event_count: int = 0


# -- Qt log handler --

class _LogSignal(QObject):
    message = pyqtSignal(str)


class QtLogHandler(logging.Handler):
    """Logging handler that emits records as Qt signals for the debug panel."""

    def __init__(self) -> None:
        super().__init__()
        self._signal = _LogSignal()
        self.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname).1s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))

    @property
    def message_signal(self) -> pyqtSignal:
        return self._signal.message

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._signal.message.emit(self.format(record))
        except RuntimeError:
            pass


# -- widget --

class DebugPanel(QFrame):
    """Live debug information panel shown below the main chat overlay."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("debugPanel")
        self.setStyleSheet(_PANEL_CSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 6, 10, 10)
        root.setSpacing(4)

        root.addWidget(self._make_header("GSI STATE"))
        gsi_grid = QVBoxLayout()
        gsi_grid.setSpacing(1)
        self._gsi_row1 = self._make_kv_row()
        self._gsi_row2 = self._make_kv_row()
        self._gsi_row3 = self._make_kv_row()
        gsi_grid.addLayout(self._gsi_row1[0])
        gsi_grid.addLayout(self._gsi_row2[0])
        gsi_grid.addLayout(self._gsi_row3[0])
        root.addLayout(gsi_grid)

        root.addWidget(self._make_header("SYSTEM"))
        stats_grid = QVBoxLayout()
        stats_grid.setSpacing(1)
        self._stats_row1 = self._make_kv_row()
        self._stats_row2 = self._make_kv_row()
        stats_grid.addLayout(self._stats_row1[0])
        stats_grid.addLayout(self._stats_row2[0])
        root.addLayout(stats_grid)

        root.addWidget(self._make_header("LOGS"))
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setStyleSheet(_LOG_CSS)
        self._log_view.setMaximumBlockCount(_MAX_LOG_LINES)
        self._log_view.setFixedHeight(120)
        root.addWidget(self._log_view)

        self._log_handler = QtLogHandler()
        self._log_handler.message_signal.connect(
            self._append_log, Qt.ConnectionType.QueuedConnection,
        )

    @property
    def log_handler(self) -> QtLogHandler:
        return self._log_handler

    def update_snapshot(self, s: DebugSnapshot) -> None:
        self._set_kv_row(self._gsi_row1, "Hero", s.hero, "State", s.game_state)
        self._set_kv_row(self._gsi_row2, "Gold", s.gold, "Lvl", s.level)
        self._set_kv_row(self._gsi_row3, "K/D/A", s.kda, "Time", s.game_time)

        total_llm = s.llm_calls + s.llm_chats
        avg = f"{s.llm_avg_ms}ms" if total_llm else "-"
        self._set_kv_row(
            self._stats_row1,
            "LLM", f"{s.llm_calls} tips + {s.llm_chats} chats",
            "Avg", avg,
        )
        self._set_kv_row(
            self._stats_row2,
            "Vision", s.vision_mode,
            "FPS", s.capture_fps,
        )

    def _append_log(self, text: str) -> None:
        self._log_view.appendPlainText(text)

    # -- layout helpers --

    @staticmethod
    def _make_header(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(_SECTION_HEADER_CSS)
        return lbl

    @staticmethod
    def _make_kv_row() -> tuple[QHBoxLayout, QLabel, QLabel, QLabel, QLabel]:
        lay = QHBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        k1 = QLabel()
        k1.setStyleSheet(_KV_LABEL_CSS)
        v1 = QLabel()
        v1.setStyleSheet(_KV_VALUE_CSS)
        k2 = QLabel()
        k2.setStyleSheet(_KV_LABEL_CSS)
        v2 = QLabel()
        v2.setStyleSheet(_KV_VALUE_CSS)
        lay.addWidget(k1)
        lay.addWidget(v1)
        lay.addStretch()
        lay.addWidget(k2)
        lay.addWidget(v2)
        return lay, k1, v1, k2, v2

    @staticmethod
    def _set_kv_row(
        row: tuple[QHBoxLayout, QLabel, QLabel, QLabel, QLabel],
        k1: str, v1: str, k2: str, v2: str,
    ) -> None:
        _, kl1, vl1, kl2, vl2 = row
        kl1.setText(k1)
        vl1.setText(v1)
        kl2.setText(k2)
        vl2.setText(v2)
