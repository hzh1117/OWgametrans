import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QPushButton, QGroupBox,
    QCheckBox, QPlainTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from config.settings import get_settings
from utils.constants import FONT_FAMILY

logger = logging.getLogger("gametrans.ui")


class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        settings = get_settings()
        w = settings.get("ui", "settings_width", default=450)
        h = settings.get("ui", "settings_height", default=550)
        self.setWindowTitle("GameTrans - 设置")
        self.setFixedSize(w, h)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("设置")
        title.setFont(QFont(FONT_FAMILY, 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        settings = get_settings()

        trans_group = QGroupBox("翻译设置")
        trans_layout = QFormLayout()

        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["中文", "English", "日本語", "한국어"])
        lang_map = {"zh": 0, "en": 1, "ja": 2, "ko": 3}
        current = settings.get("translate", "target_language", default="zh")
        self._lang_combo.setCurrentIndex(lang_map.get(current, 0))
        trans_layout.addRow("目标语言:", self._lang_combo)

        volc_cfg = settings.get("translate", "volcengine", default={})
        self._volc_id = QLineEdit(volc_cfg.get("app_id", ""))
        self._volc_id.setPlaceholderText("留空则使用内置密钥")
        trans_layout.addRow("火山 App ID:", self._volc_id)

        self._volc_key = QLineEdit(volc_cfg.get("app_key", ""))
        self._volc_key.setPlaceholderText("留空则使用内置密钥")
        self._volc_key.setEchoMode(QLineEdit.EchoMode.Password)
        trans_layout.addRow("火山 App Key:", self._volc_key)

        baidu_cfg = settings.get("translate", "baidu", default={})
        self._baidu_id = QLineEdit(baidu_cfg.get("app_id", ""))
        self._baidu_id.setPlaceholderText("留空则使用内置密钥")
        trans_layout.addRow("百度 App ID:", self._baidu_id)

        self._baidu_key = QLineEdit(baidu_cfg.get("app_key", ""))
        self._baidu_key.setPlaceholderText("留空则使用内置密钥")
        self._baidu_key.setEchoMode(QLineEdit.EchoMode.Password)
        trans_layout.addRow("百度 App Key:", self._baidu_key)

        trans_group.setLayout(trans_layout)
        layout.addWidget(trans_group)

        overlay_group = QGroupBox("显示设置")
        overlay_layout = QFormLayout()

        self._font_size = QSpinBox()
        self._font_size.setRange(10, 24)
        self._font_size.setValue(settings.get("overlay", "font_size", default=14))
        overlay_layout.addRow("字体大小:", self._font_size)

        self._opacity = QDoubleSpinBox()
        self._opacity.setRange(0.3, 1.0)
        self._opacity.setSingleStep(0.1)
        self._opacity.setValue(settings.get("overlay", "opacity", default=0.9))
        overlay_layout.addRow("透明度:", self._opacity)

        self._duration = QSpinBox()
        self._duration.setRange(2, 30)
        self._duration.setValue(settings.get("overlay", "display_duration_sec", default=5))
        overlay_layout.addRow("显示时长(秒):", self._duration)

        self._max_msgs = QSpinBox()
        self._max_msgs.setRange(1, 20)
        self._max_msgs.setValue(settings.get("overlay", "max_messages", default=10))
        overlay_layout.addRow("最大消息数:", self._max_msgs)

        self._overlay_height = QSpinBox()
        self._overlay_height.setRange(80, 400)
        self._overlay_height.setValue(settings.get("overlay", "overlay_height", default=200))
        overlay_layout.addRow("悬浮窗高度:", self._overlay_height)

        self._anim_interval = QSpinBox()
        self._anim_interval.setRange(50, 1000)
        self._anim_interval.setSuffix(" ms")
        self._anim_interval.setValue(settings.get("overlay", "animation_interval_ms", default=200))
        overlay_layout.addRow("动画刷新间隔:", self._anim_interval)

        self._show_original = QCheckBox("显示原文")
        self._show_original.setChecked(settings.get("overlay", "show_original", default=False))
        overlay_layout.addRow("", self._show_original)

        overlay_group.setLayout(overlay_layout)
        layout.addWidget(overlay_group)

        # Live preview
        self._preview_label = QLabel("[Player] 集火天使\n    focus the mercy")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._update_preview()
        layout.addWidget(self._preview_label)

        # Connect sliders to preview update
        self._font_size.valueChanged.connect(self._update_preview)
        self._opacity.valueChanged.connect(self._update_preview)

        # Player blacklist
        blacklist_group = QGroupBox("玩家屏蔽")
        blacklist_layout = QVBoxLayout()
        blacklist_layout.addWidget(QLabel("屏蔽的玩家名（每行一个）:"))
        self._blacklist_edit = QPlainTextEdit()
        self._blacklist_edit.setMaximumHeight(80)
        blacklist = settings.get("general", "player_blacklist", default=[])
        self._blacklist_edit.setPlainText("\n".join(blacklist))
        blacklist_layout.addWidget(self._blacklist_edit)
        blacklist_group.setLayout(blacklist_layout)
        layout.addWidget(blacklist_group)

        btn_layout = QVBoxLayout()
        self._save_btn = QPushButton("保存")
        self._save_btn.setMinimumHeight(36)
        self._save_btn.clicked.connect(self._save)
        btn_layout.addWidget(self._save_btn)

        self._reset_btn = QPushButton("重置聊天区域")
        self._reset_btn.setMinimumHeight(36)
        self._reset_btn.clicked.connect(self._reset_region)
        btn_layout.addWidget(self._reset_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _update_preview(self):
        """Update the preview label with current settings."""
        font_size = self._font_size.value()
        opacity = self._opacity.value()
        alpha = int(opacity * 255)
        self._preview_label.setFont(QFont(FONT_FAMILY, font_size - 2))
        self._preview_label.setStyleSheet(
            f"color: rgba(0, 255, 0, {alpha});"
            f"background-color: rgba(0, 0, 0, 150);"
            f"padding: 4px; border-radius: 3px;"
        )

    def _save(self):
        settings = get_settings()
        lang_map = {"中文": "zh", "English": "en", "日本語": "ja", "한국어": "ko"}
        items = [
            (("translate", "target_language"),
             lang_map.get(self._lang_combo.currentText(), "zh")),
            (("overlay", "font_size"), self._font_size.value()),
            (("overlay", "opacity"), self._opacity.value()),
            (("overlay", "display_duration_sec"), self._duration.value()),
            (("overlay", "max_messages"), self._max_msgs.value()),
            (("overlay", "overlay_height"), self._overlay_height.value()),
            (("overlay", "animation_interval_ms"), self._anim_interval.value()),
            (("overlay", "show_original"), self._show_original.isChecked()),
            (("general", "player_blacklist"),
             [name.strip() for name in self._blacklist_edit.toPlainText().splitlines() if name.strip()]),
        ]

        if self._volc_id.text().strip():
            items.append((("translate", "volcengine", "app_id"), self._volc_id.text().strip()))
        if self._volc_key.text().strip():
            items.append((("translate", "volcengine", "app_key"), self._volc_key.text().strip()))
        if self._baidu_id.text().strip():
            items.append((("translate", "baidu", "app_id"), self._baidu_id.text().strip()))
        if self._baidu_key.text().strip():
            items.append((("translate", "baidu", "app_key"), self._baidu_key.text().strip()))

        settings.set_many(items)
        logger.info("Settings saved")
        self.close()

    def _reset_region(self):
        settings = get_settings()
        settings.set("capture", "region", None)
        settings.set("general", "first_run", True)
        settings.save()
        logger.info("Region reset, will show setup wizard on next start")
        self.close()
