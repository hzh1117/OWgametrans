import ctypes
import ctypes.wintypes
import logging
import platform
import time

import numpy as np
import mss
import mss.tools

logger = logging.getLogger("gametrans.capture")

if platform.system() == "Windows":
    user32 = ctypes.windll.user32
else:
    user32 = None

OW_CLASS_NAMES = ["TankWindowClass", "OsWindow"]
OW_TITLE_KEYWORDS = ["overwatch", "守望先锋"]


def set_dpi_awareness():
    if user32 is None:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def find_overwatch_window() -> tuple[int, int, int, int] | None:
    if user32 is None:
        return None
    result = []

    def enum_callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.lower()
        class_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buf, 256)
        class_name = class_buf.value

        if class_name in OW_CLASS_NAMES or any(kw in title for kw in OW_TITLE_KEYWORDS):
            client_rect = ctypes.wintypes.RECT()
            user32.GetClientRect(hwnd, client_rect)
            point = ctypes.wintypes.POINT(0, 0)
            user32.ClientToScreen(hwnd, ctypes.byref(point))
            # ClientToScreen returns physical pixels when DPI awareness is set
            left = point.x
            top = point.y
            width = client_rect.right
            height = client_rect.bottom
            result.append((left, top, width, height))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
    )
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
    return result[0] if result else None


def compute_chat_roi(window_rect: tuple[int, int, int, int]) -> dict[str, int]:
    win_left, win_top, win_w, win_h = window_rect
    chat_w = int(win_w * 0.42)
    chat_h = int(win_h * 0.18)
    chat_left = win_left + int(win_w * 0.04)
    chat_top = win_top + win_h - int(win_h * 0.03) - chat_h
    return {"left": chat_left, "top": chat_top, "width": chat_w, "height": chat_h}


class ScreenCapture:
    def __init__(self):
        self._sct = mss.mss()
        self._region = None
        self._auto_roi = False
        self._window_rect = None
        self._last_recompute = 0.0
        self._recompute_interval = 2.0

    def set_region(self, x: int, y: int, width: int, height: int):
        self._region = {"left": x, "top": y, "width": width, "height": height}
        self._auto_roi = False

    def set_auto_roi(self):
        self._auto_roi = True
        self._recompute_roi()

    def _recompute_roi(self):
        window_rect = find_overwatch_window()
        if window_rect is None:
            logger.debug("Overwatch window not found")
            return False
        self._window_rect = window_rect
        self._region = compute_chat_roi(window_rect)
        self._last_recompute = time.monotonic()
        logger.info("Auto ROI computed: %s", self._region)
        return True

    def _maybe_recompute(self):
        if not self._auto_roi:
            return
        now = time.monotonic()
        if now - self._last_recompute < self._recompute_interval:
            return
        self._last_recompute = now
        window_rect = find_overwatch_window()
        if window_rect and window_rect != self._window_rect:
            self._window_rect = window_rect
            self._region = compute_chat_roi(window_rect)
            logger.info("Window moved, recomputed ROI: %s", self._region)

    def get_region(self):
        return self._region

    def capture(self) -> np.ndarray | None:
        if self._region is None:
            return None
        try:
            self._maybe_recompute()
            screenshot = self._sct.grab(self._region)
            img = np.array(screenshot, dtype=np.uint8)
            return img[:, :, :3]
        except Exception as e:
            logger.warning("Screen capture failed: %s", e)
            return None

    def close(self):
        self._sct.close()
