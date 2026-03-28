"""Overlay widgets: title bar, settings tray, message bubbles, chat input."""

from __future__ import annotations

from datetime import datetime, timezone

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

_FONT = "'.AppleSystemUIFont', 'Segoe UI', sans-serif"

# ---------- panel ----------

_PANEL_CSS = """
QFrame#coachPanel {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(22, 22, 30, 240),
        stop:1 rgba(16, 16, 22, 250)
    );
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 18);
}
"""

# ---------- title bar ----------

_TITLE_BAR_CSS = """
QFrame#titleBar {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(35, 35, 50, 250),
        stop:1 rgba(28, 28, 42, 250)
    );
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 10);
}
"""

_TITLE_LABEL_CSS = f"""
    color: rgba(160, 170, 255, 220);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2px;
    font-family: {_FONT};
"""

_STATUS_DOT_CSS = "color: #44dd88; font-size: 8px;"

_BTN_CSS = """
QPushButton {
    background: rgba(255, 255, 255, 8);
    color: rgba(180, 180, 200, 180);
    border: 1px solid rgba(255, 255, 255, 12);
    border-radius: 6px;
    font-size: 13px;
    padding: 0px;
}
QPushButton:hover {
    background: rgba(255, 255, 255, 20);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 30);
}
"""

# ---------- settings tray ----------

_SETTINGS_TRAY_CSS = """
QFrame#settingsTray {
    background: rgba(25, 25, 36, 245);
    border-bottom: 1px solid rgba(255, 255, 255, 8);
}
"""

_SETTING_LABEL_CSS = f"""
    color: rgba(155, 155, 175, 180);
    font-size: 10px;
    font-family: {_FONT};
"""

_SETTING_VALUE_CSS = f"""
    color: rgba(180, 190, 255, 200);
    font-size: 10px;
    font-weight: 600;
    font-family: {_FONT};
    min-width: 28px;
"""

_SLIDER_CSS = """
QSlider::groove:horizontal {
    height: 3px;
    background: rgba(255, 255, 255, 20);
    border-radius: 1px;
}
QSlider::handle:horizontal {
    width: 10px;
    height: 10px;
    margin: -4px 0;
    background: rgba(140, 160, 255, 220);
    border-radius: 5px;
}
QSlider::handle:horizontal:hover {
    background: rgba(170, 185, 255, 255);
}
QSlider::sub-page:horizontal {
    background: rgba(100, 120, 255, 100);
    border-radius: 1px;
}
"""

# ---------- messages ----------

def _msg_coach_css(font_size: int) -> str:
    return f"""
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(50, 50, 72, 200),
        stop:1 rgba(42, 42, 62, 200)
    );
    border-radius: 10px;
    border-bottom-left-radius: 3px;
    border: 1px solid rgba(255, 255, 255, 8);
    padding: 9px 11px;
    color: #dddde8;
    font-size: {font_size}px;
    line-height: 1.4;
    font-family: {_FONT};
    """

def _msg_user_css(font_size: int) -> str:
    return f"""
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(60, 110, 210, 200),
        stop:1 rgba(50, 90, 180, 200)
    );
    border-radius: 10px;
    border-bottom-right-radius: 3px;
    border: 1px solid rgba(255, 255, 255, 10);
    padding: 9px 11px;
    color: #f0f2ff;
    font-size: {font_size}px;
    line-height: 1.4;
    font-family: {_FONT};
    """

_TIME_CSS = f"""
    color: rgba(140, 140, 165, 130);
    font-size: 9px;
    font-family: {_FONT};
    padding: 1px 6px 0px 6px;
"""

# ---------- chat input ----------

def _input_css(font_size: int) -> str:
    return f"""
    QLineEdit {{
        background-color: rgba(30, 30, 42, 230);
        border: 1px solid rgba(255, 255, 255, 25);
        border-radius: 10px;
        color: #e0e0ee;
        font-size: {font_size}px;
        font-family: {_FONT};
        padding: 7px 12px;
        selection-background-color: rgba(80, 120, 220, 150);
    }}
    QLineEdit:focus {{
        border: 1px solid rgba(110, 140, 255, 140);
        background-color: rgba(34, 34, 48, 240);
    }}
    QLineEdit::placeholder {{
        color: rgba(130, 130, 155, 100);
    }}
    """

# ---------- scrollbar ----------

_SCROLL_CSS = """
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical {
    width: 4px; background: transparent; margin: 2px 0;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 35); border-radius: 2px; min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: rgba(255, 255, 255, 60); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""


# ======================================================================
#  Settings tray (slides open below title bar)
# ======================================================================

class SettingsTray(QFrame):
    """Collapsible row of sliders for font size, opacity, width, tip frequency."""

    font_size_changed = pyqtSignal(int)
    opacity_changed = pyqtSignal(int)
    width_changed = pyqtSignal(int)
    frequency_changed = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsTray")
        self.setStyleSheet(_SETTINGS_TRAY_CSS)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(6)

        self._font_slider, self._font_val = self._add_row(
            lay, "Font", 10, 20, 12, "px", self._on_font
        )
        self._opacity_slider, self._opacity_val = self._add_row(
            lay, "Opacity", 40, 100, 95, "%", self._on_opacity
        )
        self._width_slider, self._width_val = self._add_row(
            lay, "Width", 240, 500, 340, "px", self._on_width
        )
        self._freq_slider, self._freq_val = self._add_row(
            lay, "Tips every", 5, 60, 10, "s", self._on_freq
        )

    def _add_row(self, parent_lay, label_text, min_v, max_v, default, suffix, handler):
        row = QHBoxLayout()
        row.setSpacing(6)

        lbl = QLabel(label_text)
        lbl.setStyleSheet(_SETTING_LABEL_CSS)
        lbl.setFixedWidth(58)
        row.addWidget(lbl)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setStyleSheet(_SLIDER_CSS)
        slider.setRange(min_v, max_v)
        slider.setValue(default)
        slider.setFixedHeight(16)
        row.addWidget(slider, 1)

        val = QLabel(f"{default}{suffix}")
        val.setStyleSheet(_SETTING_VALUE_CSS)
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(val)

        slider.valueChanged.connect(lambda v: (val.setText(f"{v}{suffix}"), handler(v)))

        parent_lay.addLayout(row)
        return slider, val

    def _on_font(self, v: int) -> None:
        self.font_size_changed.emit(v)

    def _on_opacity(self, v: int) -> None:
        self.opacity_changed.emit(v)

    def _on_width(self, v: int) -> None:
        self.width_changed.emit(v)

    def _on_freq(self, v: int) -> None:
        self.frequency_changed.emit(v)


# ======================================================================
#  Title bar
# ======================================================================

class DraggableTitleBar(QFrame):
    collapse_toggled = pyqtSignal(bool)
    settings_toggled = pyqtSignal(bool)

    def __init__(self, title: str = "COACH", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setStyleSheet(_TITLE_BAR_CSS)
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 6, 0)
        lay.setSpacing(6)

        dot = QLabel("\u25cf")
        dot.setStyleSheet(_STATUS_DOT_CSS)
        dot.setFixedWidth(10)
        lay.addWidget(dot)

        self._label = QLabel(title)
        self._label.setStyleSheet(_TITLE_LABEL_CSS)
        lay.addWidget(self._label)
        lay.addStretch()

        self._settings_btn = QPushButton("\u2699")
        self._settings_btn.setStyleSheet(_BTN_CSS)
        self._settings_btn.setFixedSize(22, 22)
        self._settings_btn.setToolTip("Settings")
        self._settings_btn.clicked.connect(self._on_settings)
        lay.addWidget(self._settings_btn)

        self._collapse_btn = QPushButton("\u2013")
        self._collapse_btn.setStyleSheet(_BTN_CSS)
        self._collapse_btn.setFixedSize(22, 22)
        self._collapse_btn.setToolTip("Collapse / Expand")
        self._collapse_btn.clicked.connect(self._on_collapse)
        lay.addWidget(self._collapse_btn)

        self._collapsed = False
        self._settings_open = False
        self._drag_pos: QPoint | None = None

    def _on_collapse(self) -> None:
        self._collapsed = not self._collapsed
        self._collapse_btn.setText("+" if self._collapsed else "\u2013")
        self.collapse_toggled.emit(self._collapsed)

    def _on_settings(self) -> None:
        self._settings_open = not self._settings_open
        self.settings_toggled.emit(self._settings_open)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        if event and self._drag_pos is not None:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        self._drag_pos = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)


# ======================================================================
#  Message bubble
# ======================================================================

class MessageBubble(QFrame):
    def __init__(self, text: str, is_user: bool = False, timestamp: str = "",
                 font_size: int = 12, parent=None) -> None:
        super().__init__(parent)
        self._is_user = is_user
        self._text = text

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4 if is_user else 0, 0, 0 if is_user else 4, 0)
        lay.setSpacing(2)

        self._label = QLabel(text)
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.TextFormat.PlainText)
        self._label.setStyleSheet(_msg_user_css(font_size) if is_user else _msg_coach_css(font_size))
        self._label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self._label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        if not timestamp:
            timestamp = datetime.now(timezone.utc).strftime("%H:%M")
        time_label = QLabel(timestamp)
        time_label.setStyleSheet(_TIME_CSS)
        time_label.setAlignment(
            Qt.AlignmentFlag.AlignRight if is_user else Qt.AlignmentFlag.AlignLeft
        )

        lay.addWidget(self._label)
        lay.addWidget(time_label)

    def update_font_size(self, size: int) -> None:
        css = _msg_user_css(size) if self._is_user else _msg_coach_css(size)
        self._label.setStyleSheet(css)


# ======================================================================
#  Main panel
# ======================================================================

class CoachPanel(QFrame):
    user_message = pyqtSignal(str)
    frequency_changed = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("coachPanel")
        self.setStyleSheet(_PANEL_CSS)
        self._font_size = 12
        self._bubbles: list[MessageBubble] = []

        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 8)
        root_lay.setSpacing(0)

        self._title_bar = DraggableTitleBar("COACH")
        self._title_bar.collapse_toggled.connect(self._on_collapse)
        self._title_bar.settings_toggled.connect(self._on_settings_toggle)
        root_lay.addWidget(self._title_bar)

        self._settings = SettingsTray()
        self._settings.setVisible(False)
        self._settings.font_size_changed.connect(self._apply_font_size)
        self._settings.opacity_changed.connect(self._apply_opacity)
        self._settings.width_changed.connect(self._apply_width)
        self._settings.frequency_changed.connect(lambda v: self.frequency_changed.emit(v))
        root_lay.addWidget(self._settings)

        self._body = QWidget()
        body_lay = QVBoxLayout(self._body)
        body_lay.setContentsMargins(8, 8, 8, 8)
        body_lay.setSpacing(8)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setStyleSheet(_SCROLL_CSS)
        self._msg_container = QWidget()
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setContentsMargins(0, 0, 0, 0)
        self._msg_layout.setSpacing(8)
        self._msg_layout.addStretch()
        self._scroll.setWidget(self._msg_container)
        body_lay.addWidget(self._scroll, 1)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask the coach...")
        self._input.setStyleSheet(_input_css(self._font_size))
        self._input.returnPressed.connect(self._on_submit)
        body_lay.addWidget(self._input)

        root_lay.addWidget(self._body, 1)

    # -- settings handlers --

    def _on_settings_toggle(self, show: bool) -> None:
        self._settings.setVisible(show)

    def _apply_font_size(self, size: int) -> None:
        self._font_size = size
        for b in self._bubbles:
            b.update_font_size(size)
        self._input.setStyleSheet(_input_css(size))

    def _apply_opacity(self, pct: int) -> None:
        win = self.window()
        if win:
            win.setWindowOpacity(pct / 100.0)

    def _apply_width(self, px: int) -> None:
        win = self.window()
        if win:
            geo = win.geometry()
            win.setGeometry(geo.x(), geo.y(), px, geo.height())

    # -- collapse --

    def _on_collapse(self, collapsed: bool) -> None:
        self._body.setVisible(not collapsed)
        self._settings.setVisible(False)
        win = self.window()
        if win and collapsed:
            win.setFixedHeight(self._title_bar.height() + 2)
        elif win:
            win.setMinimumHeight(120)
            win.setMaximumHeight(16777215)
            win.resize(win.width(), 160)

    # -- messages --

    def add_coach_message(self, text: str) -> None:
        bubble = MessageBubble(text, is_user=False, font_size=self._font_size)
        self._bubbles.append(bubble)
        self._msg_layout.addWidget(bubble)
        self._scroll_to_bottom()

    def add_user_message(self, text: str) -> None:
        bubble = MessageBubble(text, is_user=True, font_size=self._font_size)
        self._bubbles.append(bubble)
        self._msg_layout.addWidget(bubble)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def _on_submit(self) -> None:
        text = self._input.text().strip()
        if text:
            self._input.clear()
            self.user_message.emit(text)
