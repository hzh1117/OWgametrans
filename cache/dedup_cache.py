import hashlib
import logging
import time
from collections import OrderedDict

logger = logging.getLogger("gametrans.cache")


class DedupCache:
    def __init__(self, max_size: int = 1000, ttl: float = 30.0):
        self._max_size = max_size
        self._ttl = ttl
        self._cache: OrderedDict[str, float] = OrderedDict()

    def _make_key(self, player: str, message: str) -> str:
        raw = f"{player}{message[:50]}"
        return hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()

    def is_duplicate(self, player: str, message: str) -> bool:
        key = self._make_key(player, message)
        now = time.time()

        if key in self._cache:
            created = self._cache[key]
            if now - created < self._ttl:
                self._cache.move_to_end(key)
                return True
            else:
                del self._cache[key]

        return False

    def add(self, player: str, message: str):
        key = self._make_key(player, message)
        now = time.time()

        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = now
        else:
            self._cache[key] = now
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

        self._cleanup(now)

    def _cleanup(self, now: float):
        expired = [k for k, v in self._cache.items() if now - v >= self._ttl]
        for k in expired:
            del self._cache[k]

    def clear(self):
        self._cache.clear()
