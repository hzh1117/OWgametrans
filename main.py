import sys
import logging
import queue

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, QObject

from config.settings import get_settings
from utils.logging_config import setup_logging
from capture.screen_capture import ScreenCapture
from ocr.winrt_ocr import WinrtOCR
from parser.message_parser import parse_messages
from parser.system_filter import filter_messages
from translate.engine import TranslateEngine
from cache.dedup_cache import DedupCache
from overlay.translation_overlay import TranslationOverlay
from overlay.input_helper import create_input_helper
from ui.setup_wizard import SetupWizard
from ui.tray_icon import create_tray_icon
from utils.hotkey import HotkeyManager

logger = setup_logging()


class TranslationWorker(QObject):
    finished = pyqtSignal(str, str, str)
    error = pyqtSignal(str)

    def __init__(self, engine: TranslateEngine):
        super().__init__()
        self._engine = engine
        self._queue: queue.Queue[tuple[str, str] | None] = queue.Queue()

    def enqueue(self, player: str, message: str):
        self._queue.put((player, message))

    def process(self):
        while True:
            item = self._queue.get()
            if item is None:
                break
            player, message = item
            try:
                result = self._engine.translate(message)
                if result:
                    self.finished.emit(player, message, result)
            except Exception as e:
                self.error.emit(str(e))

    def stop(self):
        self._queue.put(None)


class GameTransApp:
    def __init__(self):
        self.settings = get_settings()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.capture = ScreenCapture()
        self.ocr = WinrtOCR()
        self.translate_engine = TranslateEngine()
        self.dedup = DedupCache()
        self.hotkey_mgr = HotkeyManager()
        self.overlay = None
        self.input_helper = None
        self._paused = False
        self._last_text = ""
        self._timer = None
        self._worker = None
        self._worker_thread = None

        self._load_region()

    def _load_region(self):
        region = self.settings.get("capture", "region")
        if region:
            self.capture.set_region(
                region["x"], region["y"],
                region["width"], region["height"],
            )
            logger.info("Loaded region: %s", region)
        else:
            logger.info("No region configured, will show setup wizard")

    def _run_setup(self):
        wizard = SetupWizard()
        wizard.show()
        self.app.exec()
        self._load_region()

    def _start_translation_worker(self):
        self._worker_thread = QThread()
        self._worker = TranslationWorker(self.translate_engine)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.process)
        self._worker.finished.connect(self._on_translation_done)
        self._worker.error.connect(lambda e: logger.warning("Translation error: %s", e))
        self._worker_thread.start()

    def _on_translation_done(self, player: str, message: str, translated: str):
        if self.overlay:
            self.overlay.add_message(player, message, translated)
        logger.info("[%s] %s → %s", player, message[:30], translated[:30])

    def _start_ocr_loop(self):
        self.ocr.initialize()

        overlay_cfg = self.settings.get("overlay", default={})
        region = self.capture.get_region()
        if region:
            self.overlay = TranslationOverlay(
                (region["x"], region["y"], region["width"], region["height"]),
                overlay_cfg,
            )
            self.overlay.show()

        self._start_translation_worker()

        self._timer = QTimer()
        self._timer.timeout.connect(self._ocr_tick)
        interval = self.settings.get("capture", "interval_ms", default=500)
        self._timer.start(interval)
        logger.info("OCR loop started, interval=%dms", interval)

    def _ocr_tick(self):
        if self._paused:
            return

        img = self.capture.capture()
        if img is None:
            return

        try:
            text = self.ocr.preprocess_and_ocr(img)
        except Exception as e:
            logger.warning("OCR error: %s", e)
            return

        if not text or text == self._last_text:
            return
        self._last_text = text

        messages = parse_messages(text)
        messages = filter_messages(messages)

        for msg in messages:
            if self.dedup.is_duplicate(msg.player, msg.message):
                continue
            self.dedup.add(msg.player, msg.message)
            if self._worker:
                self._worker.enqueue(msg.player, msg.message)

    def _manual_translate(self):
        logger.info("Manual translate triggered")
        self._last_text = ""
        self._ocr_tick()

    def _toggle_pause(self, running: bool):
        self._paused = not running
        logger.info("Translation %s", "resumed" if running else "paused")

    def _show_input_helper(self):
        if self.input_helper is None:
            self.input_helper = create_input_helper(self.translate_engine)
        screen = self.app.primaryScreen().geometry()
        self.input_helper.show_at(
            screen.width() // 2 - 175,
            screen.height() // 2 - 40,
        )

    def _exit(self):
        if self._timer:
            self._timer.stop()
        if self._worker:
            self._worker.stop()
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait(2000)
        self.hotkey_mgr.unregister_all()
        self.capture.close()
        logger.info("GameTrans exiting")

    def run(self):
        if self.settings.get("general", "first_run") or self.capture.get_region() is None:
            self._run_setup()

        if self.capture.get_region() is None:
            logger.error("No region selected, exiting")
            return

        self._start_ocr_loop()

        hotkeys = self.settings.get("hotkeys", default={})
        self.hotkey_mgr.register(
            hotkeys.get("manual_translate", "ctrl+t"),
            self._manual_translate,
        )
        self.hotkey_mgr.register(
            hotkeys.get("input_helper", "ctrl+shift+t"),
            self._show_input_helper,
        )

        self.tray = create_tray_icon(
            on_toggle=self._toggle_pause,
            on_exit=self._exit,
        )
        self.tray.show()

        logger.info("GameTrans ready")
        self.app.exec()


def main():
    app = GameTransApp()
    app.run()


if __name__ == "__main__":
    main()
