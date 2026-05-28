import json
import logging
import time
from collections import OrderedDict
from pathlib import Path

from PyQt6.QtCore import QThread

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

        self._cache: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self._cache_max = settings.get("translate", "cache_max", default=500)
        self._cache_ttl = settings.get("translate", "cache_ttl_sec", default=600.0)
        self._cache_file = Path(__file__).parent.parent / "cache" / "translation_cache.json"
        self._load_cache()

    def _cache_key(self, text: str, source: str) -> str:
        return f"{source}:{self.target_lang}:{text}"

    def _get_cached(self, text: str, source: str) -> str | None:
        key = self._cache_key(text, source)
        if key in self._cache:
            result, ts = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                self._cache.move_to_end(key)
                return result
            else:
                del self._cache[key]
        return None

    def _put_cache(self, text: str, source: str, result: str):
        key = self._cache_key(text, source)
        self._cache[key] = (result, time.time())
        if len(self._cache) > self._cache_max:
            self._cache.popitem(last=False)

    def _load_cache(self):
        try:
            if self._cache_file.exists():
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                now = time.time()
                for key, (result, ts) in data.items():
                    if now - ts < self._cache_ttl:
                        self._cache[key] = (result, ts)
                logger.info("Loaded %d cached translations", len(self._cache))
        except Exception as e:
            logger.debug("Failed to load translation cache: %s", e)

    def save_cache(self):
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v for k, v in self._cache.items()}
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            logger.info("Saved %d translations to cache", len(self._cache))
        except Exception as e:
            logger.debug("Failed to save translation cache: %s", e)

    def translate(self, text: str, source: str = "auto") -> str | None:
        cached = self._get_cached(text, source)
        if cached:
            logger.debug("Translation cache hit for: %s", text[:30])
            return cached

        t0 = time.perf_counter()
        result = self.primary.translate(text, source=source, target=self.target_lang)
        t1 = time.perf_counter()

        if result:
            self._put_cache(text, source, result)
            logger.info("Primary translate: %.1fms, text_len=%d", (t1 - t0) * 1000, len(text))
            return result

        logger.info("Primary translator failed after %.1fms, trying fallback", (t1 - t0) * 1000)
        t2 = time.perf_counter()
        result = self.fallback.translate(text, source=source, target=self.target_lang)
        t3 = time.perf_counter()

        if result:
            self._put_cache(text, source, result)
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
