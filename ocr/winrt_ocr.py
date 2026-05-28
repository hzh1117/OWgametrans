import logging

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

        self._binarize_threshold = capture_cfg.get("binarize_threshold", 180)
        self._contrast_percentiles = (5, 95)

    def initialize(self):
        try:
            test_img = Image.new("RGB", (100, 30), color=(255, 255, 255))
            winocr.recognize_pil_sync(test_img, lang=self._lang)
            logger.info("Windows OCR engine initialized (winocr), lang=%s", self._lang)
        except Exception as e:
            logger.error("Failed to initialize OCR: %s", e)
            raise

    def preprocess_and_ocr(self, bgr_image: np.ndarray) -> str:
        gray = np.dot(bgr_image[..., :3], [0.114, 0.587, 0.299]).astype(np.uint8)

        p_low, p_high = np.percentile(gray, list(self._contrast_percentiles))
        if p_high <= p_low:
            p_high = p_low + 1
        stretched = np.clip(
            (gray.astype(np.float32) - p_low) / (p_high - p_low) * 255, 0, 255
        ).astype(np.uint8)

        binary = np.where(stretched >= self._binarize_threshold, 255, 0).astype(np.uint8)

        img = Image.fromarray(binary, mode="L").convert("RGB")
        result = winocr.recognize_pil_sync(img, lang=self._lang)
        text = result.text if result else ""
        return text.strip()
