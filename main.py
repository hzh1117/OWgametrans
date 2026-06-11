import ctypes
import sys
import time
import logging

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject

from config.settings import get_settings
from utils.logging_config import setup_logging
from capture.screen_capture import ScreenCapture, set_dpi_awareness
from ocr import create_ocr_engine
from parser.message_parser import parse_messages, detect_source_language
from parser.system_filter import filter_messages
from translate.engine import TranslateEngine
from cache.dedup_cache import DedupCache
from overlay.translation_overlay import TranslationOverlay
from overlay.input_helper import create_input_helper
from ui.setup_wizard import SetupWizard
from ui.tray_icon import create_tray_icon
from ui.history_window import create_history_window
from utils.hotkey import HotkeyManager

logger = setup_logging()


class PipelineWorker(QObject):
    """Full capture→OCR→parse→filter→dedup→translate pipeline on a worker thread.

    Architecture:
        QTimer → _tick() [capture+OCR+parse, fast] → emit translate_request
        translate_request → _do_translate [blocking, queued] → emit translation_done
    """

    translation_done = pyqtSignal(str, str, str)   # player, original, translated
    translation_pending = pyqtSignal()              # a translation was dispatched
    pipeline_error = pyqtSignal(str)
    _translate_request = pyqtSignal(str, str, str)  # player, message, source_lang

    _MAX_CONSECUTIVE_ERRORS = 10

    def __init__(self, settings_data: dict, region: dict, interval_ms: int):
        super().__init__()
        self._settings_data = settings_data
        self._region = region
        self._interval_ms = interval_ms
        self._paused = False
        self._capture = None
        self._ocr = None
        self._translate_engine = None
        self._dedup = None
        self._timer = None
        self._consecutive_errors = 0
        self._translate_request.connect(self._do_translate)

    @property
    def translate_engine(self):
        """Public access to the translate engine (for InputHelper)."""
        return self._translate_engine

    def _init_pipeline(self):
        """Initialize pipeline components on the worker thread."""
        self._capture = ScreenCapture()
        self._capture.set_region(
            self._region["x"], self._region["y"],
            self._region["width"], self._region["height"],
        )
        self._ocr = create_ocr_engine(self._settings_data)
        self._ocr.initialize()
        self._translate_engine = TranslateEngine()
        self._dedup = DedupCache()

        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(self._interval_ms)
        logger.info("Pipeline worker started, interval=%dms", self._interval_ms)

    def set_interval(self, ms: int):
        self._interval_ms = ms
        if self._timer:
            self._timer.setInterval(ms)

    def set_paused(self, paused: bool):
        self._paused = paused

    def trigger_tick(self):
        """Force a pipeline tick (for manual translate)."""
        if not self._paused:
            self._tick()

    def _tick(self):
        """Fast tick: capture + OCR + parse + dedup, then dispatch translations."""
        if self._paused or self._capture is None:
            return

        t0 = time.perf_counter()
        img = self._capture.capture()
        t1 = time.perf_counter()
        if img is None:
            return

        try:
            text = self._ocr.preprocess_and_ocr(img)
            self._consecutive_errors = 0  # reset on success
        except Exception as e:
            self._consecutive_errors += 1
            logger.warning("OCR error (%d/%d): %s",
                           self._consecutive_errors, self._MAX_CONSECUTIVE_ERRORS, e)
            if self._consecutive_errors >= self._MAX_CONSECUTIVE_ERRORS:
                self._reinitialize_ocr()
            return
        t2 = time.perf_counter()

        if not text:
            return

        messages = parse_messages(text)
        messages = filter_messages(messages)
        t3 = time.perf_counter()

        # Detect source language from the full OCR text
        source_lang = detect_source_language(text)

        # Filter blacklisted players
        blacklist = set(self._settings_data.get("general", {}).get("player_blacklist", []))

        for msg in messages:
            if msg.player in blacklist:
                continue
            if self._dedup.check_and_add(msg.player, msg.message):
                continue
            # Dispatch translation asynchronously via signal queue
            self.translation_pending.emit()
            self._translate_request.emit(msg.player, msg.message, source_lang)

        t4 = time.perf_counter()
        total_ms = (t4 - t0) * 1000
        if total_ms > 100:
            logger.info(
                "Pipeline tick: capture=%.1fms, ocr=%.1fms, parse=%.1fms, dispatch=%.1fms, total=%.1fms",
                (t1 - t0) * 1000, (t2 - t1) * 1000,
                (t3 - t2) * 1000, (t4 - t3) * 1000, total_ms,
            )

    def _do_translate(self, player: str, message: str, source_lang: str):
        """Slot: perform the actual translation (runs on worker thread, queued)."""
        try:
            result = self._translate_engine.translate_with_retry(
                message, source=source_lang,
            )
            if result:
                self.translation_done.emit(player, message, result)
        except Exception as e:
            self.pipeline_error.emit(str(e))

    def shutdown(self):
        if self._timer:
            self._timer.stop()
        if self._translate_engine:
            self._translate_engine.save_cache()
        if self._capture:
            self._capture.close()

    def _reinitialize_ocr(self):
        """Attempt to recover from persistent OCR errors."""
        logger.warning("OCR circuit breaker triggered after %d consecutive errors, reinitializing...",
                        self._consecutive_errors)
        self._consecutive_errors = 0
        try:
            self._ocr = create_ocr_engine(self._settings_data)
            self._ocr.initialize()
            logger.info("OCR engine reinitialized successfully")
        except Exception as e:
            logger.error("Failed to reinitialize OCR engine: %s", e)
            self._paused = True
            logger.error("Pipeline paused due to unrecoverable OCR failure")


class GameTransApp:
    def __init__(self):
        set_dpi_awareness()
        self.settings = get_settings()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.hotkey_mgr = HotkeyManager()
        self.overlay = None
        self.input_helper = None
        self._history_window = None
        self._paused = False
        self._exiting = False
        self._fps_timer = None
        self._pipeline_worker = None
        self._pipeline_thread = None

        self._base_interval = self.settings.get("capture", "interval_ms", default=500)
        self._config_reload_timer = QTimer()
        self._config_reload_timer.timeout.connect(self.settings.check_reload)
        self._config_reload_timer.start(5000)

        self._region = self.settings.get("capture", "region")

    def _load_region(self):
        self._region = self.settings.get("capture", "region")
        if self._region:
            logger.info("Loaded region: %s", self._region)
        else:
            logger.info("No region configured, will show setup wizard")

    def _run_setup(self):
        wizard = SetupWizard()
        wizard.finished.connect(lambda: self.app.quit())
        wizard.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        wizard.destroyed.connect(lambda: self.app.quit())
        wizard.show()
        self.app.exec()
        self._load_region()

    def _start_pipeline(self):
        overlay_cfg = self.settings.get("overlay", default={})
        if self._region:
            logger.info("Creating overlay for region: %s", self._region)
            self.overlay = TranslationOverlay(
                (self._region["left"], self._region["top"],
                 self._region["width"], self._region["height"]),
                overlay_cfg,
            )
            saved_pos = self.settings.get("overlay", "position")
            if saved_pos:
                self.overlay.move(saved_pos["x"], saved_pos["y"])
            self.overlay.show()
            logger.info("Overlay shown")

        self._pipeline_thread = QThread()
        self._pipeline_worker = PipelineWorker(
            self.settings.data, self._region, self._base_interval,
        )
        self._pipeline_worker.moveToThread(self._pipeline_thread)
        self._pipeline_worker.translation_done.connect(self._on_translation_done)
        if self.overlay:
            self._pipeline_worker.translation_pending.connect(self.overlay.mark_pending)
        self._pipeline_worker.pipeline_error.connect(
            lambda e: logger.warning("Pipeline error: %s", e)
        )
        self._pipeline_thread.started.connect(self._pipeline_worker._init_pipeline)
        self._pipeline_thread.start()
        logger.info("Pipeline worker thread started")

        # Frame rate adaptation timer (stays on main thread)
        self._fps_timer = QTimer()
        self._fps_timer.timeout.connect(self._adapt_frame_rate)
        self._fps_timer.start(3000)

    def _on_translation_done(self, player: str, message: str, translated: str):
        if self.overlay:
            self.overlay.add_message(player, message, translated)
        if self._history_window:
            self._history_window.add_entry(player, message, translated)
        logger.debug("[%s] %s -> %s", player, message[:30], translated[:30])
        logger.info("[%s] translated %d chars", player, len(message))

    def _show_history(self):
        if self._history_window is None:
            self._history_window = create_history_window()
        if self._history_window.isVisible():
            self._history_window.hide()
        else:
            self._history_window.show()

    def _adapt_frame_rate(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value.lower()
                if "overwatch" in title or "守望先锋" in title:
                    if self._pipeline_worker:
                        self._pipeline_worker.set_interval(self._base_interval)
                        logger.debug("Timer interval: %dms (game focused)", self._base_interval)
                else:
                    idle_interval = min(self._base_interval * 2, 2000)
                    if self._pipeline_worker:
                        self._pipeline_worker.set_interval(idle_interval)
                        logger.debug("Timer interval: %dms (game not focused)", idle_interval)
        except Exception:
            pass

    def _toggle_overlay_drag(self):
        if self.overlay:
            self.overlay.enable_drag()
            logger.info("Overlay drag enabled, drag to reposition then release")

    def _manual_translate(self):
        logger.info("Manual translate triggered")
        if self._pipeline_worker:
            self._pipeline_worker.trigger_tick()

    def _toggle_pause(self, running: bool):
        self._paused = not running
        if self._pipeline_worker:
            self._pipeline_worker.set_paused(not running)
        logger.info("Translation %s", "resumed" if running else "paused")

    def _show_input_helper(self):
        if self.input_helper is None:
            engine = (self._pipeline_worker.translate_engine if self._pipeline_worker
                      else TranslateEngine())
            self.input_helper = create_input_helper(engine)
        screen = self.app.primaryScreen()
        if screen is None:
            logger.warning("No primary screen found, cannot show input helper")
            return
        geo = screen.geometry()
        self.input_helper.show_at(
            geo.width() // 2 - 175,
            geo.height() // 2 - 40,
        )

    def _exit(self):
        if self._exiting:
            return
        self._exiting = True

        if self._pipeline_worker:
            self._pipeline_worker.shutdown()
        if self._pipeline_thread:
            self._pipeline_thread.quit()
            if not self._pipeline_thread.wait(3000):
                logger.warning("Pipeline thread did not exit in time, terminating")
                self._pipeline_thread.terminate()
                self._pipeline_thread.wait(1000)
        self._config_reload_timer.stop()
        if self._fps_timer:
            self._fps_timer.stop()
        self.hotkey_mgr.unregister_all()
        logger.info("GameTrans exiting")

    def run(self):
        if self.settings.get("general", "first_run") or self._region is None:
            self._run_setup()

        if self._region is None:
            logger.error("No region selected, exiting")
            return

        logger.info("Region ready, starting pipeline...")
        try:
            self._start_pipeline()
        except Exception as e:
            logger.error("Failed to start pipeline: %s", e, exc_info=True)
            return

        logger.info("Pipeline started, registering hotkeys...")
        hotkeys = self.settings.get("hotkeys", default={})
        self.hotkey_mgr.register(
            hotkeys.get("manual_translate", "ctrl+t"),
            lambda: QTimer.singleShot(0, self._manual_translate),
        )
        self.hotkey_mgr.register(
            hotkeys.get("input_helper", "ctrl+shift+t"),
            lambda: QTimer.singleShot(0, self._show_input_helper),
        )
        self.hotkey_mgr.register(
            hotkeys.get("exit", "ctrl+y"),
            lambda: QTimer.singleShot(0, self._exit),
        )
        self.hotkey_mgr.register(
            hotkeys.get("move_overlay", "ctrl+m"),
            lambda: QTimer.singleShot(0, self._toggle_overlay_drag),
        )
        self.hotkey_mgr.register(
            hotkeys.get("history", "ctrl+h"),
            lambda: QTimer.singleShot(0, self._show_history),
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
