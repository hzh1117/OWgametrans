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
        cache = DedupCache(max_size=3, ttl=60.0)
        cache.check_and_add("P", "a")
        cache.check_and_add("P", "b")
        cache.check_and_add("P", "c")
        cache.check_and_add("P", "d")
        assert cache.check_and_add("P", "a") is False

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
