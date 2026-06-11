import logging
import time

import numpy as np
from PIL import Image

logger = logging.getLogger("gametrans.ocr")


class PaddleOCR:
    def __init__(self, config: dict = None):
        cfg = config or {}
        ocr_cfg = cfg.get("ocr", {})
        self._lang = ocr_cfg.get("language", "ch")
        self._target_height = ocr_cfg.get("target_height", 960)
        self._ocr = None

    def initialize(self):
        try:
            from paddleocr import PaddleOCR as _PaddleOCR
            self._ocr = _PaddleOCR(
                lang=self._lang,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=True,
            )
            logger.info("PaddleOCR engine initialized, lang=%s", self._lang)
        except Exception as e:
            logger.error("Failed to initialize PaddleOCR: %s", e)
            raise

    def _scale_image(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        if h >= self._target_height:
            return image
        scale = self._target_height / h
        new_w = int(w * scale)
        new_h = self._target_height
        img = Image.fromarray(image[..., ::-1])
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        return np.array(img)[..., ::-1]

    def preprocess_and_ocr(self, bgr_image: np.ndarray) -> str:
        t0 = time.perf_counter()

        scaled = self._scale_image(bgr_image)
        t1 = time.perf_counter()

        result = self._ocr.ocr(scaled)
        t2 = time.perf_counter()

        lines = []
        if result and result[0]:
            for line in result[0]:
                if line and len(line) >= 2:
                    text, confidence = line[1]
                    if confidence > 0.5:
                        lines.append(text)

        text = "\n".join(lines).strip()

        total_ms = (t2 - t0) * 1000
        if total_ms > 50:
            logger.info(
                "OCR perf: preprocess=%.1fms, recognize=%.1fms, total=%.1fms, chars=%d",
                (t1 - t0) * 1000, (t2 - t1) * 1000, total_ms, len(text),
            )

        return text
