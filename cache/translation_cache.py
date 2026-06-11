import json
import logging
import time
from collections import OrderedDict
from pathlib import Path

logger = logging.getLogger("gametrans.cache")


class TranslationCache:
    """LRU translation cache with TTL and file persistence."""

    def __init__(self, max_size: int = 500, ttl_sec: float = 600.0,
                 cache_file: Path | None = None):
        self._max_size = max_size
        self._ttl = ttl_sec
        self._cache_file = cache_file or (
            Path(__file__).parent / "translation_cache.json"
        )
        self._cache: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self._load()

    def _key(self, text: str, source: str, target: str) -> str:
        return f"{source}:{target}:{text}"

    def get(self, text: str, source: str, target: str) -> str | None:
        key = self._key(text, source, target)
        if key in self._cache:
            result, ts = self._cache[key]
            if time.time() - ts < self._ttl:
                self._cache.move_to_end(key)
                return result
            else:
                del self._cache[key]
        return None

    def put(self, text: str, source: str, target: str, result: str):
        key = self._key(text, source, target)
        self._cache[key] = (result, time.time())
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def _load(self):
        try:
            if self._cache_file.exists():
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                now = time.time()
                for key, (result, ts) in data.items():
                    if now - ts < self._ttl:
                        self._cache[key] = (result, ts)
                logger.info("Loaded %d cached translations", len(self._cache))
        except Exception as e:
            logger.debug("Failed to load translation cache: %s", e)

    def save(self):
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v for k, v in self._cache.items()}
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            logger.info("Saved %d translations to cache", len(self._cache))
        except Exception as e:
            logger.debug("Failed to save translation cache: %s", e)
