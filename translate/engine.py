import logging
import time

from config.settings import get_settings
from translate.volcengine_api import VolcengineTranslator
from translate.baidu_api import BaiduTranslator

logger = logging.getLogger("gametrans.translate")


class TranslateEngine:
    def __init__(self):
        settings = get_settings()
        volc_cfg = settings.get("translate", "volcengine", default={})
        baidu_cfg = settings.get("translate", "baidu", default={})
        self.target_lang = settings.get("translate", "target_language", default="zh")

        self.primary = VolcengineTranslator(
            app_id=volc_cfg.get("app_id", ""),
            app_key=volc_cfg.get("app_key", ""),
            endpoint=volc_cfg.get("endpoint", ""),
        )
        self.fallback = BaiduTranslator(
            app_id=baidu_cfg.get("app_id", ""),
            app_key=baidu_cfg.get("app_key", ""),
            endpoint=baidu_cfg.get("endpoint", ""),
        )

    def translate(self, text: str, source: str = "auto") -> str | None:
        result = self.primary.translate(text, source=source, target=self.target_lang)
        if result:
            return result

        logger.info("Primary translator failed, trying fallback")
        result = self.fallback.translate(text, source=source, target=self.target_lang)
        if result:
            return result

        logger.error("All translation engines failed for: %s", text[:50])
        return None

    def translate_with_retry(self, text: str, source: str = "auto", retries: int = 1) -> str | None:
        for attempt in range(retries + 1):
            result = self.translate(text, source=source)
            if result:
                return result
            if attempt < retries:
                time.sleep(0.2)
        return None
