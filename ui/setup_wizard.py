import sys
import logging
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QComboBox, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from config.settings import get_settings
from overlay.region_selector import select_region

logger = logging.getLogger("gametrans.ui")


class SetupWizard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GameTrans - 首次设置")
        self.setFixedSize(420, 300)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("守望先锋聊天翻译 - 设置向导")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        step1 = QLabel("第1步：选择游戏聊天区域")
        step1.setFont(QFont("Microsoft YaHei", 12))
        layout.addWidget(step1)

        self._region_btn = QPushButton("点击后拖动框选聊天区域")
        self._region_btn.setMinimumHeight(40)
        self._region_btn.clicked.connect(self._select_region)
        layout.addWidget(self._region_btn)

        step2 = QLabel("第2步：选择翻译目标语言")
        step2.setFont(QFont("Microsoft YaHei", 12))
        layout.addWidget(step2)

        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("翻译为:"))
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["中文", "English", "日本語", "한국어"])
        self._lang_combo.setMinimumHeight(35)
        lang_layout.addWidget(self._lang_combo)
        layout.addLayout(lang_layout)

        self._done_btn = QPushButton("完成设置")
        self._done_btn.setMinimumHeight(40)
        self._done_btn.clicked.connect(self._finish)
        layout.addWidget(self._done_btn)

        self.setLayout(layout)
        self._selected_region = None

    def _select_region(self):
        self.hide()
        QApplication.processEvents()
        region = select_region()
        self.show()
        if region:
            self._selected_region = region
            x, y, w, h = region
            self._region_btn.setText(f"已选择: ({x}, {y}) {w}×{h}")
            logger.info("Region selected: %s", region)

    def _finish(self):
        settings = get_settings()
        lang_map = {"中文": "zh", "English": "en", "日本語": "ja", "한국어": "ko"}
        target = lang_map.get(self._lang_combo.currentText(), "zh")

        if self._selected_region:
            settings.set("capture", "region", {
                "x": self._selected_region[0],
                "y": self._selected_region[1],
                "width": self._selected_region[2],
                "height": self._selected_region[3],
            })
        settings.set("translate", "target_language", target)
        settings.set("general", "first_run", False)
        logger.info("Setup complete: target=%s, region=%s", target, self._selected_region)
        self.close()


def run_setup_wizard():
    app = QApplication.instance() or QApplication(sys.argv)
    wizard = SetupWizard()
    wizard.show()
    app.exec()
    return wizard._selected_region
