import logging
import time

import numpy as np
from PIL import Image
import winocr

logger = logging.getLogger("gametrans.ocr")



class WinrtOCR:
    def __init__(self, config: dict = None):
        cfg = config or {}
        ocr_cfg = cfg.get("ocr", {})
        capture_cfg = cfg.get("capture", {}).get("preprocessing", {})

        self._lang = ocr_cfg.get("language", "auto")
        if self._lang == "auto":
            self._lang = "en"

        percentiles = capture_cfg.get("contrast_percentiles", [5, 95])
        self._contrast_percentiles = tuple(percentiles)
        self._target_height = ocr_cfg.get("target_height", 360)

    def initialize(self):
        try:
            test_img = Image.new("RGB", (100, 30), color=(255, 255, 255))
            winocr.recognize_pil_sync(test_img, lang=self._lang)
            logger.info("Windows OCR engine initialized (winocr), lang=%s", self._lang)
        except Exception as e:
            logger.error("Failed to initialize OCR: %s", e)
            raise

    def _scale_to_target_height(self, gray: np.ndarray) -> np.ndarray:
        h, w = gray.shape[:2]
        if h == self._target_height:
            return gray
        scale = self._target_height / h
        new_w = int(w * scale)
        img = Image.fromarray(gray, mode="L")
        img = img.resize((new_w, self._target_height), Image.Resampling.LANCZOS)
        return np.array(img)

    def preprocess_and_ocr(self, bgr_image: np.ndarray) -> str:
        t0 = time.perf_counter()

        # BGR weights: B=0.114, G=0.587, R=0.299
        gray = np.dot(bgr_image[..., :3], [0.114, 0.587, 0.299]).astype(np.uint8)

        gray = self._scale_to_target_height(gray)

        p_low, p_high = np.percentile(gray, list(self._contrast_percentiles))
        if p_high <= p_low:
            p_high = p_low + 1
        stretched = np.clip(
            (gray.astype(np.float32) - p_low) / (p_high - p_low) * 255, 0, 255
        ).astype(np.uint8)

        # Skip binarization — go directly to grayscale OCR.
        # Overwatch chat has high-contrast text; binarization (Otsu) adds latency
        # without improving recognition, and the old fallback path doubled OCR time.
        img = Image.fromarray(stretched, mode="L").convert("RGB")
        t1 = time.perf_counter()

        result = winocr.recognize_pil_sync(img, lang=self._lang)

        # Handle dict result from winocr
        if isinstance(result, dict):
            text = result.get("text", "") or ""
        else:
            text = getattr(result, "text", "") or ""

        t2 = time.perf_counter()

        total_ms = (t2 - t0) * 1000
        if total_ms > 50:
            logger.info(
                "OCR perf: preprocess=%.1fms, recognize=%.1fms, total=%.1fms, chars=%d",
                (t1 - t0) * 1000, (t2 - t1) * 1000, total_ms, len(text),
            )

        return text.strip()
