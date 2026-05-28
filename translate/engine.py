import logging
from config.settings import get_settings
from translate.volcengine_api import VolcengineTranslator
from translate.baidu_api import BaiduTranslator

logger = logging.getLogger("gametrans.translate")


class TranslateEngine:
    def __init__(self):
        settings = get_settings()
        volc_cfg = settings.get("translate", "volcengine")
        baidu_cfg = settings.get("translate", "baidu")
        self.target_lang = settings.get("translate", "target_language", default="zh")

        self.primary = VolcengineTranslator(
            app_id=volc_cfg.get("app_id", ""),
            app_key=volc_cfg.get("app_key", ""),
        )
        self.fallback = BaiduTranslator(
            app_id=baidu_cfg.get("app_id", ""),
            app_key=baidu_cfg.get("app_key", ""),
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
