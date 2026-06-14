from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app import database, scheduler
from app.services import weather as weather_service


def _jma_payload(temp_defines: list[str], temps: list[str]):
    """最小構成の気象庁レスポンス（天気コード/降水確率/気温）を組み立てる。"""
    today = date.today().isoformat()
    return [{
        "timeSeries": [
            {  # 天気コード
                "timeDefines": [f"{today}T05:00:00+09:00"],
                "areas": [{"area": {"name": "筑後地方"}, "weatherCodes": ["100"], "weathers": ["晴れ"]}],
            },
            {  # 降水確率
                "timeDefines": [f"{today}T18:00:00+09:00"],
                "areas": [{"area": {"name": "筑後地方"}, "pops": ["10"]}],
            },
            {  # 気温（久留米）
                "timeDefines": temp_defines,
                "areas": [{"area": {"name": "久留米"}, "temps": temps}],
            },
        ],
    }]


@contextmanager
def _mock_jma(payload):
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    cm = MagicMock()
    cm.__enter__.return_value = resp
    with patch.object(weather_service, "urlopen", return_value=cm):
        yield


def test_temp_max_falls_back_to_next_day_in_evening():
    """夕方以降で当日9時データが消えても、最高気温は翌日9時にフォールバックする"""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    payload = _jma_payload(
        [f"{tomorrow}T00:00:00+09:00", f"{tomorrow}T09:00:00+09:00"],
        ["20", "29"],
    )
    with _mock_jma(payload):
        result = weather_service.fetch_weather()

    assert result is not None
    assert result["temp_max"] == 29   # 翌日9時にフォールバック（null にならない）
    assert result["temp_min"] == 20


def test_temp_uses_today_when_available():
    """当日9時データがあれば当日値を優先する"""
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    payload = _jma_payload(
        [f"{today}T09:00:00+09:00", f"{tomorrow}T00:00:00+09:00", f"{tomorrow}T09:00:00+09:00"],
        ["31", "23", "28"],
    )
    with _mock_jma(payload):
        result = weather_service.fetch_weather()

    assert result["temp_max"] == 31   # 今日の9時
    assert result["temp_min"] == 23   # 今夜の0時


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
