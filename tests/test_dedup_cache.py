import time
from cache.dedup_cache import DedupCache


class TestDedupCache:
    def setup_method(self):
        self.cache = DedupCache(max_size=100, ttl=1.0)

    def test_exact_duplicate(self):
        assert self.cache.check_and_add("Player", "hello") is False
        assert self.cache.check_and_add("Player", "hello") is True

    def test_different_messages(self):
        assert self.cache.check_and_add("Player", "hello") is False
        assert self.cache.check_and_add("Player", "world") is False

    def test_different_players_same_message(self):
        assert self.cache.check_and_add("Player1", "hello") is False
        assert self.cache.check_and_add("Player2", "hello") is False

    def test_ttl_expiry(self):
        self.cache = DedupCache(max_size=100, ttl=0.1)
        self.cache.check_and_add("Player", "hello")
        time.sleep(0.15)
        assert self.cache.check_and_add("Player", "hello") is False

    def test_lru_eviction(self):
        cache = DedupCache(max_size=3, ttl=60.0, window_size=3)
        cache.check_and_add("P", "aaaa")
        cache.check_and_add("P", "bbbb")
        cache.check_and_add("P", "cccc")
        cache.check_and_add("P", "dddd")
        # After 4 inserts with max_size=3, "aaaa" was evicted from exact cache.
        # Sliding window now has bbbb, ccccc, dddd — "aaaa" is gone from both.
        assert cache.check_and_add("P", "aaaa") is False

    def test_fuzzy_duplicate(self):
        cache = DedupCache(max_size=100, ttl=30.0, similarity_threshold=0.85)
        cache.check_and_add("Player", "你好世界欢迎来到守望先锋")
        assert cache.check_and_add("Player", "你好世界欢迎来到守望锋") is True

    def test_fuzzy_different_players(self):
        cache = DedupCache(max_size=100, ttl=30.0, similarity_threshold=0.85)
        cache.check_and_add("Player1", "你好世界欢迎来到守望先锋")
        assert cache.check_and_add("Player2", "你好世界欢迎来到守望先锋") is False

    def test_clear(self):
        self.cache.check_and_add("Player", "hello")
        self.cache.clear()
        assert self.cache.check_and_add("Player", "hello") is False
