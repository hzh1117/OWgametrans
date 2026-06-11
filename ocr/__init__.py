import logging

logger = logging.getLogger("gametrans.ocr")


def create_ocr_engine(config: dict):
    engine = config.get("ocr", {}).get("engine", "winrt")
    if engine == "paddle":
        from ocr.paddle_ocr import PaddleOCR
        return PaddleOCR(config)
    else:
        from ocr.winrt_ocr import WinrtOCR
        return WinrtOCR(config)
