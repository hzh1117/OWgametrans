import sys
import logging
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QCursor

logger = logging.getLogger("gametrans.overlay")


class RegionSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        self._start = QPoint()
        self._end = QPoint()
        self._selecting = False
        self._result = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self._selecting:
            rect = QRect(self._start, self._end).normalized()
            pen = QPen(QColor(0, 200, 255), 2)
            painter.setPen(pen)
            painter.drawRect(rect)
            painter.fillRect(rect, QColor(0, 200, 255, 30))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.pos()
            self._end = event.pos()
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self._selecting:
            self._end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._selecting = False
            rect = QRect(self._start, self._end).normalized()
            if rect.width() > 10 and rect.height() > 10:
                self._result = (rect.x(), rect.y(), rect.width(), rect.height())
                self.close()
            else:
                self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._result = None
            self.close()

    def get_region(self) -> tuple[int, int, int, int] | None:
        return self._result


def select_region() -> tuple[int, int, int, int] | None:
    app = QApplication.instance() or QApplication(sys.argv)
    selector = RegionSelector()
    selector.showFullScreen()
    app.exec()
    return selector.get_region()
