import time
import logging
from collections import deque
from dataclasses import dataclass, field

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from utils.constants import FONT_FAMILY

logger = logging.getLogger("gametrans.ui")


@dataclass
class HistoryEntry:
    player: str
    original: str
    translated: str
    timestamp: float = field(default_factory=time.monotonic)


class HistoryWindow(QWidget):
    """Scrollable window showing recent translation history."""

    def __init__(self, max_entries: int = 100):
        super().__init__()
        self._max_entries = max_entries
        self._entries: deque[HistoryEntry] = deque(maxlen=max_entries)

        self.setWindowTitle("GameTrans - 翻译历史")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        )
        self.resize(400, 300)

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)

        self._container = QWidget()
        self._container_layout = QVBoxLayout()
        self._container_layout.setContentsMargins(4, 4, 4, 4)
        self._container_layout.setSpacing(2)
        self._container.setLayout(self._container_layout)
        self._scroll.setWidget(self._container)

        layout.addWidget(self._scroll)
        self.setLayout(layout)

    def add_entry(self, player: str, original: str, translated: str):
        """Add a translation to the history."""
        entry = HistoryEntry(player=player, original=original, translated=translated)
        self._entries.append(entry)

        label = QLabel(
            f"[{player}] {translated}\n    {original}"
        )
        label.setFont(QFont(FONT_FAMILY, 10))
        label.setStyleSheet(
            "color: white; background-color: rgba(30, 30, 30, 200); "
            "padding: 4px; border-radius: 3px;"
        )
        label.setWordWrap(True)
        self._container_layout.addWidget(label)

        # Remove old labels if over limit
        while self._container_layout.count() > self._max_entries:
            old = self._container_layout.takeAt(0)
            if old.widget():
                old.widget().deleteLater()

        # Auto-scroll to bottom
        QTimer.singleShot(0, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def clear_history(self):
        """Clear all history entries."""
        self._entries.clear()
        while self._container_layout.count():
            old = self._container_layout.takeAt(0)
            if old.widget():
                old.widget().deleteLater()


def create_history_window() -> HistoryWindow:
    return HistoryWindow()
