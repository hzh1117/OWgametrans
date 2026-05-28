import ctypes
import sys
import time
import logging

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, QObject

from config.settings import get_settings
from utils.logging_config import setup_logging
from capture.screen_capture import ScreenCapture, set_dpi_awareness
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
    request = pyqtSignal(str, str)

    def __init__(self, engine: TranslateEngine):
        super().__init__()
        self._engine = engine
        self.request.connect(self._process)

    def _process(self, player: str, message: str):
        try:
            result = self._engine.translate_with_retry(message)
            if result:
                self.finished.emit(player, message, result)
        except Exception as e:
            self.error.emit(str(e))


class GameTransApp:
    def __init__(self):
        set_dpi_awareness()
        self.settings = get_settings()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.capture = ScreenCapture()
        self.ocr = WinrtOCR(config=self.settings.data)
        self.translate_engine = TranslateEngine()
        self.dedup = DedupCache()
        self.hotkey_mgr = HotkeyManager()
        self.overlay = None
        self.input_helper = None
        self._paused = False
        self._exiting = False
        self._timer = None
        self._fps_timer = None
        self._worker = None
        self._worker_thread = None

        self._base_interval = self.settings.get("capture", "interval_ms", default=500)
        self._config_reload_timer = QTimer()
        self._config_reload_timer.timeout.connect(self.settings.check_reload)
        self._config_reload_timer.start(5000)

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
        self._worker.finished.connect(self._on_translation_done)
        self._worker.error.connect(lambda e: logger.warning("Translation error: %s", e))
        self._worker_thread.start()

    def _on_translation_done(self, player: str, message: str, translated: str):
        if self.overlay:
            self.overlay.add_message(player, message, translated)
        logger.debug("[%s] %s -> %s", player, message[:30], translated[:30])
        logger.info("[%s] translated %d chars", player, len(message))

    def _start_ocr_loop(self):
        self.ocr.initialize()

        overlay_cfg = self.settings.get("overlay", default={})
        region = self.capture.get_region()
        if region:
            self.overlay = TranslationOverlay(
                (region["x"], region["y"], region["width"], region["height"]),
                overlay_cfg,
            )
            # Restore saved position
            saved_pos = self.settings.get("overlay", "position")
            if saved_pos:
                self.overlay.move(saved_pos["x"], saved_pos["y"])
            self.overlay.show()

        self._start_translation_worker()

        self._timer = QTimer()
        self._timer.timeout.connect(self._ocr_tick)
        self._timer.start(self._base_interval)
        logger.info("OCR loop started, interval=%dms", self._base_interval)

        # Frame rate adaptation timer
        self._fps_timer = QTimer()
        self._fps_timer.timeout.connect(self._adapt_frame_rate)
        self._fps_timer.start(3000)

    def _ocr_tick(self):
        if self._paused:
            return

        t0 = time.perf_counter()
        img = self.capture.capture()
        t1 = time.perf_counter()
        if img is None:
            return

        try:
            text = self.ocr.preprocess_and_ocr(img)
        except Exception as e:
            logger.warning("OCR error: %s", e)
            return
        t2 = time.perf_counter()

        if not text:
            return

        messages = parse_messages(text)
        messages = filter_messages(messages)
        t3 = time.perf_counter()

        for msg in messages:
            if self.dedup.check_and_add(msg.player, msg.message):
                continue
            if self._worker:
                self._worker.request.emit(msg.player, msg.message)

        t4 = time.perf_counter()
        total_ms = (t4 - t0) * 1000
        if total_ms > 100:
            logger.info(
                "OCR tick: capture=%.1fms, ocr=%.1fms, parse=%.1fms, dispatch=%.1fms, total=%.1fms",
                (t1 - t0) * 1000, (t2 - t1) * 1000,
                (t3 - t2) * 1000, (t4 - t3) * 1000, total_ms,
            )

    def _adapt_frame_rate(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value.lower()
                if "overwatch" in title or "守望先锋" in title:
                    if self._timer and self._timer.interval() != self._base_interval:
                        self._timer.setInterval(self._base_interval)
                        logger.debug("Timer interval: %dms (game focused)", self._base_interval)
                else:
                    idle_interval = min(self._base_interval * 2, 2000)
                    if self._timer and self._timer.interval() != idle_interval:
                        self._timer.setInterval(idle_interval)
                        logger.debug("Timer interval: %dms (game not focused)", idle_interval)
        except Exception:
            pass

    def _toggle_overlay_drag(self):
        if self.overlay:
            self.overlay.enable_drag()
            logger.info("Overlay drag enabled, drag to reposition then release")

    def _manual_translate(self):
        logger.info("Manual translate triggered")
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
        if self._exiting:
            return
        self._exiting = True

        if self._timer:
            self._timer.stop()
        if self._worker:
            self._worker.request.disconnect()
        if self._worker_thread:
            self._worker_thread.quit()
            if not self._worker_thread.wait(2000):
                logger.warning("Worker thread did not exit in time, terminating")
                self._worker_thread.terminate()
                self._worker_thread.wait(1000)
        self.translate_engine.save_cache()
        self._config_reload_timer.stop()
        if self._fps_timer:
            self._fps_timer.stop()
        self.hotkey_mgr.unregister_all()
        try:
            self.capture.close()
        except Exception as e:
            logger.warning("Error closing screen capture: %s", e)
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
        self.hotkey_mgr.register(
            hotkeys.get("exit", "ctrl+q"),
            self._exit,
        )
        self.hotkey_mgr.register(
            hotkeys.get("move_overlay", "ctrl+m"),
            self._toggle_overlay_drag,
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
