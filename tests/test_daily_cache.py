from unittest.mock import patch

from app.daily_cache import DailyTTLCache


def test_hit_within_ttl_same_day():
    cache: DailyTTLCache[str] = DailyTTLCache(ttl_seconds=10)
    with patch("time.monotonic", return_value=100.0):
        cache.set("2026-09-30", "v")
    with patch("time.monotonic", return_value=109.9):
        assert cache.get("2026-09-30") == "v"


def test_miss_after_ttl_or_other_day():
    cache: DailyTTLCache[str] = DailyTTLCache(ttl_seconds=10)
    cache.set("2026-09-30", "v", saved_at=100.0)
    with patch("time.monotonic", return_value=110.0):
        assert cache.get("2026-09-30") is None
    with patch("time.monotonic", return_value=101.0):
        assert cache.get("2026-10-01") is None


def test_clear():
    cache: DailyTTLCache[int] = DailyTTLCache(ttl_seconds=10)
    cache.set("2026-09-30", 1)
    cache.clear()
    assert cache.get("2026-09-30") is None
