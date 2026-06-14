from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app import database, scheduler


def _fake_weather(temp_max: int, temp_min: int):
    def _fetch():
        return {
            "condition": "晴れ",
            "condition_emoji": "☀",
            "temp_max": temp_max,
            "temp_min": temp_min,
            "hourly_precip": [],
        }
    return _fetch


@pytest.mark.asyncio
async def test_weather_delta_computed_from_previous_day(client):
    """前日の気温が DB にあれば前日比が算出される"""
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    # 前日分を保存（最高28 / 最低20）
    await database.save_weather_cache(yesterday, 28, 20, '{"placeholder": true}')

    # 今日は最高25 / 最低22 を取得
    with patch.object(scheduler.weather_service, "fetch_weather", _fake_weather(25, 22)):
        await scheduler.refresh_weather(force=True)

    w = scheduler._cached_weather
    assert w.temp_max == 25
    assert w.temp_min == 22
    assert w.temp_max_delta == -3   # 25 - 28
    assert w.temp_min_delta == 2    # 22 - 20

    # 当日分が DB に保存されている
    cached = await database.get_weather_cache(today)
    assert cached is not None
    assert cached["temp_max"] == 25


@pytest.mark.asyncio
async def test_weather_delta_none_without_previous(client):
    """前日データが無ければ前日比は None"""
    with patch.object(scheduler.weather_service, "fetch_weather", _fake_weather(30, 21)):
        await scheduler.refresh_weather(force=True)

    w = scheduler._cached_weather
    assert w.temp_max_delta is None
    assert w.temp_min_delta is None


@pytest.mark.asyncio
async def test_weather_catchup_restores_from_db_without_api(client):
    """force=False は当日分が既にあれば API を叩かずDBから復元する（1日1回担保）"""
    # まず1回取得して当日分を保存
    with patch.object(scheduler.weather_service, "fetch_weather", _fake_weather(26, 19)):
        await scheduler.refresh_weather(force=True)

    # 2回目（起動キャッチアップ想定）。fetch_weather が呼ばれたら失敗扱いにする
    def _must_not_call():
        raise AssertionError("当日分があるのに fetch_weather が呼ばれた")

    with patch.object(scheduler.weather_service, "fetch_weather", _must_not_call):
        await scheduler.refresh_weather(force=False)

    w = scheduler._cached_weather
    assert w.temp_max == 26
    assert w.temp_min == 19
