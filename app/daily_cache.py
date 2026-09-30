from __future__ import annotations

import time


class DailyTTLCache[T]:
    """日付キーつきの単一値 TTL キャッシュ。

    日付が変わるか TTL を過ぎたら無効。計算に時間がかかる値（音声合成・外部 API）を
    短時間の連打で作り直さないために使う。
    """

    def __init__(self, ttl_seconds: float):
        self._ttl = ttl_seconds
        self._entry: tuple[float, str, T] | None = None  # (保存時刻, 日付, 値)

    def get(self, day: str) -> T | None:
        if self._entry is None:
            return None
        saved_at, saved_day, value = self._entry
        if saved_day != day or time.monotonic() - saved_at >= self._ttl:
            return None
        return value

    def set(self, day: str, value: T, saved_at: float | None = None) -> None:
        """saved_at を省略すると現在時刻。取得開始時刻を渡せば取得中の経過も TTL に含められる。"""
        self._entry = (time.monotonic() if saved_at is None else saved_at, day, value)

    def clear(self) -> None:
        self._entry = None
