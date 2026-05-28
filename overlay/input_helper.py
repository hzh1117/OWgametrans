import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QLabel, QApplication
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from translate.engine import TranslateEngine
from utils.constants import FONT_FAMILY

logger = logging.getLogger("gametrans.overlay")


class InputHelper(QWidget):
    translated = pyqtSignal(str)

    def __init__(self, translate_engine: TranslateEngine):
        super().__init__()
        self._engine = translate_engine
        self._target_lang = translate_engine.target_lang

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(350, 80)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)

        self._label = QLabel(f"输入中文 -> 翻译为 {self._target_lang}")
        self._label.setFont(QFont(FONT_FAMILY, 10))
        self._label.setStyleSheet("color: white; background: rgba(0,0,0,180); padding: 2px;")
        layout.addWidget(self._label)

        self._input = QLineEdit()
        self._input.setFont(QFont(FONT_FAMILY, 12))
        self._input.setStyleSheet(
            "background: rgba(30,30,30,200); color: white; "
            "border: 1px solid #00c8ff; padding: 4px;"
        )
        self._input.setPlaceholderText("输入文字后按 Enter 翻译...")
        self._input.returnPressed.connect(self._on_translate)
        layout.addWidget(self._input)

        self.setLayout(layout)

    def _on_translate(self):
        text = self._input.text().strip()
        if not text:
            return

        try:
            result = self._engine.translate_with_retry(text, source="zh")
            if result:
                clipboard = QApplication.clipboard()
                clipboard.setText(result)
                self._label.setText(f"已复制: {result}")
                self.translated.emit(result)
                logger.info("Translated: %s -> %s", text[:30], result[:30])
            else:
                self._label.setText("翻译失败，请重试")
        except Exception as e:
            logger.warning("Translation error: %s", e)
            self._label.setText("翻译出错")

        self._input.clear()

    def show_at(self, x: int, y: int):
        self.move(x, y)
        self.show()
        self._input.setFocus()
        self._input.clear()
        self._label.setText(f"输入中文 -> 翻译为 {self._target_lang}")


def create_input_helper(translate_engine: TranslateEngine) -> InputHelper:
    return InputHelper(translate_engine)
