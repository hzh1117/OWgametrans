import logging
import time

import numpy as np
from PIL import Image, ImageFilter
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

    def _otsu_threshold(self, gray: np.ndarray) -> int:
        hist = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
        total = gray.size
        sum_total = np.dot(np.arange(256), hist)
        sum_bg = 0.0
        weight_bg = 0
        max_variance = 0
        threshold = 128
        for t in range(256):
            weight_bg += hist[t]
            if weight_bg == 0:
                continue
            weight_fg = total - weight_bg
            if weight_fg == 0:
                break
            sum_bg += t * hist[t]
            mean_bg = sum_bg / weight_bg
            mean_fg = (sum_total - sum_bg) / weight_fg
            variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
            if variance > max_variance:
                max_variance = variance
                threshold = t
        return threshold

    def preprocess_and_ocr(self, bgr_image: np.ndarray) -> str:
        t0 = time.perf_counter()

        gray = np.dot(bgr_image[..., :3], [0.114, 0.587, 0.299]).astype(np.uint8)

        gray = self._scale_to_target_height(gray)

        p_low, p_high = np.percentile(gray, list(self._contrast_percentiles))
        if p_high <= p_low:
            p_high = p_low + 1
        stretched = np.clip(
            (gray.astype(np.float32) - p_low) / (p_high - p_low) * 255, 0, 255
        ).astype(np.uint8)

        threshold = self._otsu_threshold(stretched)
        threshold = max(threshold - 10, 80)
        binary = np.where(stretched >= threshold, 255, 0).astype(np.uint8)

        img = Image.fromarray(binary, mode="L")
        img = img.filter(ImageFilter.MedianFilter(size=3))
        img = img.convert("RGB")
        t1 = time.perf_counter()

        result = winocr.recognize_pil_sync(img, lang=self._lang)

        # Handle dict result from winocr
        if isinstance(result, dict):
            text = result.get("text", "") or ""
        else:
            text = getattr(result, "text", "") or ""

        # Fallback: try with grayscale if binarized image fails
        if not text:
            gray_rgb = Image.fromarray(stretched, mode="L").convert("RGB")
            result2 = winocr.recognize_pil_sync(gray_rgb, lang=self._lang)
            if isinstance(result2, dict):
                text2 = result2.get("text", "") or ""
            else:
                text2 = getattr(result2, "text", "") or ""
            if text2:
                logger.info("OCR fallback (grayscale) succeeded: %s", text2[:50])
                text = text2
                img = gray_rgb
        t2 = time.perf_counter()

        total_ms = (t2 - t0) * 1000
        if total_ms > 50:
            logger.info(
                "OCR perf: preprocess=%.1fms, recognize=%.1fms, total=%.1fms, chars=%d",
                (t1 - t0) * 1000, (t2 - t1) * 1000, total_ms, len(text),
            )

        return text.strip()
