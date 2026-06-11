import logging
import time
from dataclasses import dataclass, field

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt6.QtCore import Qt, QTimer, QPoint, QObject, QEvent
from PyQt6.QtGui import QFont, QCursor

from utils.constants import FONT_FAMILY
from config.settings import get_settings

logger = logging.getLogger("gametrans.overlay")


class _AltDragFilter(QObject):
    """Global event filter: holds Alt to temporarily enable overlay dragging."""

    def __init__(self, overlay: "TranslationOverlay"):
        super().__init__(overlay)
        self._overlay = overlay
        self._alt_held = False

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Alt:
            if not self._alt_held:
                self._alt_held = True
                self._overlay.enable_drag()
        elif event.type() == QEvent.Type.KeyRelease and event.key() == Qt.Key.Key_Alt:
            if self._alt_held:
                self._alt_held = False
                if not self._overlay._dragging:
                    self._overlay.disable_drag()
        return False


@dataclass
class TranslatedMessage:
    player: str
    original: str
    translated: str
    created_at: float = field(default_factory=time.monotonic)
    opacity: float = 1.0


class TranslationOverlay(QWidget):
    _CLICK_THROUGH_FLAGS = (
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.Tool
        | Qt.WindowType.WindowTransparentForInput
    )

    def __init__(self, region: tuple[int, int, int, int], config: dict):
        super().__init__()
        self._region = region
        self._entries: list[tuple[TranslatedMessage, QLabel]] = []
        self._max_messages = config.get("max_messages", 10)
        self._display_duration = config.get("display_duration_sec", 5)
        self._fade_duration = config.get("fade_duration_sec", 1.0)
        self._font_size = config.get("font_size", 14)
        self._bg_color = config.get("bg_color", "rgba(0, 0, 0, 150)")
        self._show_original = config.get("show_original", False)
        self._pending_count = 0
        self._pending_label: QLabel | None = None
        self._dragging = False
        self._drag_offset = QPoint()

        self.setWindowFlags(self._CLICK_THROUGH_FLAGS)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        opacity = config.get("opacity", 0.9)
        self.setWindowOpacity(opacity)

        x, y, w, h = region
        overlay_height = config.get("overlay_height", 200)
        overlay_gap = config.get("overlay_gap", 5)
        screens = QApplication.screens()
        target_screen = None
        for s in screens:
            geo = s.geometry()
            if geo.x() <= x < geo.x() + geo.width() and geo.y() <= y < geo.y() + geo.height():
                target_screen = s
                break
        if target_screen is None:
            target_screen = QApplication.primaryScreen()
        screen_geo = target_screen.geometry() if target_screen else None

        overlay_y = y - overlay_height - overlay_gap
        if screen_geo:
            if overlay_y < screen_geo.y():
                overlay_y = y + h + overlay_gap
            elif overlay_y + overlay_height > screen_geo.y() + screen_geo.height():
                overlay_y = y + h + overlay_gap

        self.setGeometry(x, overlay_y, w, overlay_height)

        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(2)
        self.setLayout(self._layout)

        self._status_label = QLabel("GameTrans 就绪 - 等待聊天消息...")
        self._status_label.setFont(QFont(FONT_FAMILY, self._font_size - 2))
        self._status_label.setStyleSheet("color: red; padding: 2px 6px;")
        self._layout.addWidget(self._status_label)

        animation_interval = config.get("animation_interval_ms", 200)
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_display)
        self._timer.start(animation_interval)

        # Alt+drag: install global event filter to detect Alt key
        self._alt_filter = _AltDragFilter(self)
        QApplication.instance().installEventFilter(self._alt_filter)

    def add_message(self, player: str, original: str, translated: str):
        try:
            if self._status_label.isVisible():
                self._status_label.hide()
            self.mark_done()
            msg = TranslatedMessage(player=player, original=original, translated=translated)
            label = self._create_label(msg)
            self._entries.append((msg, label))

            while len(self._entries) > self._max_messages:
                _, old_label = self._entries.pop(0)
                old_label.deleteLater()
        except Exception as e:
            logger.warning("Failed to add overlay message: %s", e)

    def mark_pending(self):
        """Show a 'translating...' indicator when a translation is in progress."""
        self._pending_count += 1
        if self._pending_label is None:
            if self._status_label.isVisible():
                self._status_label.hide()
            self._pending_label = QLabel("翻译中...")
            self._pending_label.setFont(QFont(FONT_FAMILY, self._font_size - 2))
            self._pending_label.setStyleSheet(
                f"color: rgba(255, 200, 0, 200); background-color: {self._bg_color}; padding: 2px 6px; border-radius: 3px;"
            )
            self._layout.addWidget(self._pending_label)

    def mark_done(self):
        """Remove the 'translating...' indicator when translation completes."""
        if self._pending_count > 0:
            self._pending_count -= 1
        if self._pending_count <= 0 and self._pending_label is not None:
            self._pending_label.deleteLater()
            self._pending_label = None
            self._pending_count = 0

    def _create_label(self, msg: TranslatedMessage) -> QLabel:
        if self._show_original and msg.original != msg.translated:
            text = f"[{msg.player}] {msg.translated}\n    {msg.original}"
        else:
            text = f"[{msg.player}] {msg.translated}"
        label = QLabel(text)
        label.setFont(QFont(FONT_FAMILY, self._font_size - 2))
        label.setStyleSheet(self._style_for(msg.opacity))
        self._layout.addWidget(label)
        return label

    def _style_for(self, opacity: float) -> str:
        return (
            f"color: rgba(0, 255, 0, {int(opacity * 255)});"
            f"background-color: {self._bg_color};"
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

        if not self._entries and not self._status_label.isVisible():
            self._status_label.show()

    def enable_drag(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.show()

    def disable_drag(self):
        self.setWindowFlags(self._CLICK_THROUGH_FLAGS)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            pos = self.pos()
            settings = get_settings()
            settings.set_and_save("overlay", "position", {"x": pos.x(), "y": pos.y()})
            logger.info("Overlay position saved: (%d, %d)", pos.x(), pos.y())
            # Only disable drag if Alt is not held (Alt+drag mode)
            if not self._alt_filter._alt_held:
                self.disable_drag()

    def closeEvent(self, event):
        QApplication.instance().removeEventFilter(self._alt_filter)
        self._timer.stop()
        super().closeEvent(event)
