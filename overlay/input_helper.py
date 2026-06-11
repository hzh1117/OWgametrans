import ctypes
import ctypes.wintypes
import logging
import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QLabel, QApplication
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from translate.engine import TranslateEngine
from utils.constants import FONT_FAMILY
from config.settings import get_settings

logger = logging.getLogger("gametrans.overlay")

# Win32 SendInput constants
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("_input", _INPUT),
    ]


def _type_unicode_text(text: str):
    """Type text using Win32 SendInput with Unicode flag."""
    for ch in text:
        # Key down
        down = INPUT(type=INPUT_KEYBOARD)
        down.ki = KEYBDINPUT(wVk=0, wScan=ord(ch), dwFlags=KEYEVENTF_UNICODE)
        # Key up
        up = INPUT(type=INPUT_KEYBOARD)
        up.ki = KEYBDINPUT(wVk=0, wScan=ord(ch), dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)
        inputs = (INPUT * 2)(down, up)
        ctypes.windll.user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
        time.sleep(0.005)  # small delay between keystrokes


class InputHelper(QWidget):
    translated = pyqtSignal(str)

    def __init__(self, translate_engine: TranslateEngine):
        super().__init__()
        self._engine = translate_engine
        self._target_lang = translate_engine.target_lang

        settings = get_settings()
        self._auto_type = settings.get("overlay", "auto_type", default=False)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(350, 80)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)

        mode = "自动输入" if self._auto_type else "复制到剪贴板"
        self._label = QLabel(f"输入中文 -> 翻译为 {self._target_lang} ({mode})")
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
                if self._auto_type:
                    # Hide the input helper, then type the translated text
                    self.hide()
                    QApplication.processEvents()
                    time.sleep(0.1)
                    _type_unicode_text(result)
                    self._label.setText(f"已输入: {result}")
                else:
                    clipboard = QApplication.clipboard()
                    clipboard.setText(result)
                    self._label.setText(f"已复制: {result}")
                self.translated.emit(result)
                logger.info("Translated: %s -> %s (auto_type=%s)",
                            text[:30], result[:30], self._auto_type)
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
        mode = "自动输入" if self._auto_type else "复制到剪贴板"
        self._label.setText(f"输入中文 -> 翻译为 {self._target_lang} ({mode})")


def create_input_helper(translate_engine: TranslateEngine) -> InputHelper:
    return InputHelper(translate_engine)
