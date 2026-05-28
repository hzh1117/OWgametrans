import numpy as np
import mss
import mss.tools


class ScreenCapture:
    def __init__(self):
        self._sct = mss.mss()
        self._region = None

    def set_region(self, x: int, y: int, width: int, height: int):
        self._region = {"left": x, "top": y, "width": width, "height": height}

    def get_region(self):
        return self._region

    def capture(self) -> np.ndarray | None:
        if self._region is None:
            return None
        screenshot = self._sct.grab(self._region)
        img = np.array(screenshot, dtype=np.uint8)
        return img[:, :, :3]

    def close(self):
        self._sct.close()
