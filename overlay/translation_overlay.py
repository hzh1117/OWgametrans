import logging
import time
from dataclasses import dataclass, field

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

logger = logging.getLogger("gametrans.overlay")


@dataclass
class TranslatedMessage:
    player: str
    original: str
    translated: str
    created_at: float = field(default_factory=time.monotonic)
    opacity: float = 1.0


class TranslationOverlay(QWidget):
    def __init__(self, region: tuple[int, int, int, int], config: dict):
        super().__init__()
        self._region = region
        self._messages: list[TranslatedMessage] = []
        self._labels: list[QLabel] = []
        self._max_messages = config.get("max_messages", 10)
        self._display_duration = config.get("display_duration_sec", 5)
        self._fade_duration = config.get("fade_duration_sec", 1.0)
        self._font_size = config.get("font_size", 14)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        x, y, w, h = region
        overlay_height = 200
        screen = QApplication.primaryScreen()
        screen_geo = screen.geometry() if screen else None

        overlay_y = y - overlay_height - 5
        if screen_geo:
            if overlay_y < screen_geo.y():
                overlay_y = y + h + 5
            elif overlay_y + overlay_height > screen_geo.y() + screen_geo.height():
                overlay_y = y + h + 5

        self.setGeometry(x, overlay_y, w, overlay_height)

        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(2)
        self.setLayout(self._layout)

        self._timer = QTimer()
        self._timer.timeout.connect(self._update_display)
        self._timer.start(200)

    def add_message(self, player: str, original: str, translated: str):
        msg = TranslatedMessage(player=player, original=original, translated=translated)
        self._messages.append(msg)
        if len(self._messages) > self._max_messages:
            self._messages.pop(0)
            if self._labels:
                old = self._labels.pop(0)
                old.deleteLater()
        self._add_label(msg)

    def _add_label(self, msg: TranslatedMessage):
        label = QLabel(f"[{msg.player}] {msg.translated}")
        label.setFont(QFont("Microsoft YaHei", self._font_size))
        label.setStyleSheet(self._style_for(msg.opacity))
        self._layout.addWidget(label)
        self._labels.append(label)

    def _style_for(self, opacity: float) -> str:
        return (
            f"color: rgba(255, 255, 255, {int(opacity * 255)});"
            "background-color: rgba(0, 0, 0, 150);"
            "padding: 2px 6px; border-radius: 3px;"
        )

    def _update_display(self):
        now = time.monotonic()
        to_remove = []
        for i, msg in enumerate(self._messages):
            elapsed = now - msg.created_at
            if elapsed >= self._display_duration + self._fade_duration:
                to_remove.append(i)
            elif elapsed >= self._display_duration:
                msg.opacity = 1.0 - (elapsed - self._display_duration) / self._fade_duration
                if i < len(self._labels):
                    self._labels[i].setStyleSheet(self._style_for(msg.opacity))

        for i in reversed(to_remove):
            self._messages.pop(i)
            if i < len(self._labels):
                label = self._labels.pop(i)
                label.deleteLater()

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
