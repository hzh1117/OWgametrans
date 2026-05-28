import logging
import time
from dataclasses import dataclass, field

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from utils.constants import FONT_FAMILY

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
        self._entries: list[tuple[TranslatedMessage, QLabel]] = []
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

        opacity = config.get("opacity", 0.9)
        self.setWindowOpacity(opacity)

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
        label = self._create_label(msg)
        self._entries.append((msg, label))

        while len(self._entries) > self._max_messages:
            _, old_label = self._entries.pop(0)
            old_label.deleteLater()

    def _create_label(self, msg: TranslatedMessage) -> QLabel:
        label = QLabel(f"[{msg.player}] {msg.translated}")
        label.setFont(QFont(FONT_FAMILY, self._font_size))
        label.setStyleSheet(self._style_for(msg.opacity))
        self._layout.addWidget(label)
        return label

    def _style_for(self, opacity: float) -> str:
        return (
            f"color: rgba(255, 255, 255, {int(opacity * 255)});"
            "background-color: rgba(0, 0, 0, 150);"
            "padding: 2px 6px; border-radius: 3px;"
        )

    def _update_display(self):
        now = time.monotonic()
        to_remove = []
        for i, (msg, label) in enumerate(self._entries):
            elapsed = now - msg.created_at
            if elapsed >= self._display_duration + self._fade_duration:
                to_remove.append(i)
            elif elapsed >= self._display_duration:
                msg.opacity = 1.0 - (elapsed - self._display_duration) / self._fade_duration
                label.setStyleSheet(self._style_for(msg.opacity))

        for i in reversed(to_remove):
            _, label = self._entries.pop(i)
            label.deleteLater()

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
