import logging
import time

from PyQt6.QtCore import QThread

from config.settings import get_settings
from cache.translation_cache import TranslationCache
from translate.volcengine_api import VolcengineTranslator
from translate.baidu_api import BaiduTranslator

logger = logging.getLogger("gametrans.translate")


class TranslateEngine:
    def __init__(self):
        settings = get_settings()
        volc_cfg = settings.get("translate", "volcengine", default={})
        baidu_cfg = settings.get("translate", "baidu", default={})
        self.target_lang = settings.get("translate", "target_language", default="zh")

        # Enhanced pipeline (optional, toggled via config)
        self._enhanced_enabled = settings.get("translate_enhanced", "enabled", default=False)
        self._enhanced = None
        if self._enhanced_enabled:
            try:
                from pipeline.translator import EnhancedTranslator
                self._enhanced = EnhancedTranslator()
                logger.info("Enhanced translator loaded")
            except Exception as e:
                logger.warning("Failed to load enhanced translator: %s", e)
                self._enhanced = None

        self.primary = VolcengineTranslator(
            app_id=volc_cfg.get("app_id", ""),
            app_key=volc_cfg.get("app_key", ""),
            endpoint=volc_cfg.get("endpoint", ""),
        )
        self._baidu_cfg = baidu_cfg
        self._fallback = None  # lazy initialization

        self._cache = TranslationCache(
            max_size=settings.get("translate", "cache_max", default=500),
            ttl_sec=settings.get("translate", "cache_ttl_sec", default=600.0),
        )

    def translate(self, text: str, source: str = "auto") -> str | None:
        cached = self._cache.get(text, source, self.target_lang)
        if cached:
            logger.debug("Translation cache hit for: %s", text[:30])
            return cached

        # Enhanced pipeline (Tier 1/2/3)
        if self._enhanced:
            result = self._enhanced.translate(text, source_lang=source)
            if result:
                self._cache.put(text, source, self.target_lang, result)
                return result
            logger.debug("Enhanced translate failed, falling back to NMT")

        t0 = time.perf_counter()
        result = self.primary.translate(text, source=source, target=self.target_lang)
        t1 = time.perf_counter()

        if result:
            self._cache.put(text, source, self.target_lang, result)
            logger.info("Primary translate: %.1fms, text_len=%d", (t1 - t0) * 1000, len(text))
            return result

        logger.info("Primary translator failed after %.1fms, trying fallback", (t1 - t0) * 1000)
        if self._fallback is None:
            self._fallback = BaiduTranslator(
                app_id=self._baidu_cfg.get("app_id", ""),
                app_key=self._baidu_cfg.get("app_key", ""),
                endpoint=self._baidu_cfg.get("endpoint", ""),
            )
        t2 = time.perf_counter()
        result = self._fallback.translate(text, source=source, target=self.target_lang)
        t3 = time.perf_counter()

        if result:
            self._cache.put(text, source, self.target_lang, result)
            logger.info("Fallback translate: %.1fms, text_len=%d", (t3 - t2) * 1000, len(text))
            return result

        logger.error("All engines failed: primary=%.1fms, fallback=%.1fms",
                     (t1 - t0) * 1000, (t3 - t2) * 1000)
        return None

    def translate_with_retry(self, text: str, source: str = "auto", retries: int = 1) -> str | None:
        for attempt in range(retries + 1):
            result = self.translate(text, source=source)
            if result:
                return result
            if attempt < retries:
                QThread.msleep(200)
        return None

    def save_cache(self):
        self._cache.save()
