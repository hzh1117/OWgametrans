import logging
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt

from ui.settings_window import SettingsWindow

logger = logging.getLogger("gametrans.ui")


def _create_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 150, 200))
    painter = QPainter(pixmap)
    painter.setPen(QColor(255, 255, 255))
    painter.setFont(QFont("Arial", 28, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "G")
    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, on_toggle=None, on_exit=None):
        super().__init__(_create_icon())
        self._paused = False
        self._on_toggle = on_toggle
        self._on_exit = on_exit
        self._settings_window = None

        self.menu = QMenu()
        self._toggle_action = self.menu.addAction("暂停翻译")
        self._toggle_action.triggered.connect(self._toggle)

        settings_action = self.menu.addAction("设置")
        settings_action.triggered.connect(self._open_settings)

        self.menu.addSeparator()
        exit_action = self.menu.addAction("退出")
        exit_action.triggered.connect(self._exit)

        self.setContextMenu(self.menu)
        self.setToolTip("GameTrans - 守望先锋聊天翻译")
        self.activated.connect(self._on_activated)

    def _toggle(self):
        self._paused = not self._paused
        self._toggle_action.setText("继续翻译" if self._paused else "暂停翻译")
        if self._on_toggle:
            self._on_toggle(not self._paused)

    def _open_settings(self):
        if self._settings_window is None or not self._settings_window.isVisible():
            self._settings_window = SettingsWindow()
            self._settings_window.show()

    def _exit(self):
        if self._on_exit:
            self._on_exit()
        self.hide()
        QApplication.instance().quit()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle()


def create_tray_icon(on_toggle=None, on_exit=None) -> TrayIcon:
    return TrayIcon(on_toggle=on_toggle, on_exit=on_exit)
