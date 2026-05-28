import hashlib
import logging
import time
from collections import OrderedDict
from difflib import SequenceMatcher

logger = logging.getLogger("gametrans.cache")


class DedupCache:
    def __init__(self, max_size: int = None, ttl: float = None,
                 similarity_threshold: float = 0.85, window_size: int = 50):
        if max_size is None or ttl is None:
            from config.settings import get_settings
            settings = get_settings()
            if max_size is None:
                max_size = settings.get("cache", "max_size", default=1000)
            if ttl is None:
                ttl = settings.get("cache", "ttl_sec", default=30.0)
        self._max_size = max_size
        self._ttl = ttl
        self._similarity_threshold = similarity_threshold
        self._window_size = window_size
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._window: list[tuple[str, str, float]] = []

    def _make_key(self, player: str, message: str) -> str:
        raw = f"{player}{message[:50]}"
        return hashlib.blake2b(raw.encode("utf-8"), digest_size=16).hexdigest()

    def _is_similar(self, msg1: str, msg2: str) -> bool:
        len1, len2 = len(msg1), len(msg2)
        if len1 == 0 or len2 == 0:
            return False
        if max(len1, len2) / min(len1, len2) > 1.3:
            return False
        return SequenceMatcher(None, msg1, msg2).ratio() >= self._similarity_threshold

    def check_and_add(self, player: str, message: str) -> bool:
        """Atomically check if duplicate and add if not. Returns True if duplicate."""
        now = time.time()

        # Exact dedup
        key = self._make_key(player, message)
        if key in self._cache:
            created = self._cache[key]
            if now - created < self._ttl:
                self._cache.move_to_end(key)
                return True
            else:
                del self._cache[key]

        # Fuzzy dedup against sliding window
        for win_player, win_message, win_time in self._window:
            if win_player == player and now - win_time < self._ttl:
                if self._is_similar(message, win_message):
                    logger.debug("Fuzzy duplicate: '%s' ~= '%s'", message[:30], win_message[:30])
                    return True

        # Add to exact cache
        self._cache[key] = now
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

        # Add to sliding window
        self._window.append((player, message, now))
        if len(self._window) > self._window_size:
            self._window.pop(0)

        # Cleanup expired window entries
        if len(self._window) > self._window_size * 0.8:
            self._window = [(p, m, t) for p, m, t in self._window if now - t < self._ttl]

        return False

    def clear(self):
        self._cache.clear()
        self._window.clear()
