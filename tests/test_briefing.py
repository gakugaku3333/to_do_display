from __future__ import annotations

import pytest

from app.models import Task, TodayData, WeatherData, WeatherHour
from app.services.briefing import build_briefing_text
from app.scheduler import refresh_data


def _weather() -> WeatherData:
    return WeatherData(
        condition="晴れ",
        condition_emoji="☀",
        temp_max=28,
        temp_min=18,
        temp_max_delta=2,
        hourly_precip=[
            WeatherHour(label="〜12時", precip_prob=10),
            WeatherHour(label="〜18時", precip_prob=60),
        ],
    )


def test_build_briefing_text_full():
    data = TodayData(
        date="2026-06-16",
        weekday="火曜日",
        events=[],
        stock_tasks=[],
        flow_tasks=[],
        weather=_weather(),
    )
    text = build_briefing_text(data)
    assert text.startswith("おはようございます。")
    assert "6月16日、火曜日です。" in text
    assert "天気は晴れ" in text
    assert "最高気温は28度" in text
    assert "昨日より2度高くなります" in text
    # 降水確率60%は傘の案内が出る
    assert "傘" in text


def test_build_briefing_text_no_data():
    data = TodayData(
        date="2026-06-16",
        weekday="火曜日",
        events=[],
        stock_tasks=[],
        flow_tasks=[],
        weather=None,
    )
    text = build_briefing_text(data)
    assert "天気予報は取得できませんでした。" in text
    assert "今日の予定はありません。" in text
    assert "今日のやることはありません。" in text
    # 読み上げを乱す絵文字が含まれないこと
    assert "☀" not in text


def test_build_briefing_text_weekday_tasks_separate():
    data = TodayData(
        date="2026-06-16",
        weekday="火曜日",
        events=[],
        stock_tasks=[Task(id="s1", title="電気代の支払い", task_type="stock")],
        flow_tasks=[
            Task(id="weekly_1", title="燃えるゴミ出し", task_type="weekly"),
            Task(id="f1", title="牛乳を買う", task_type="flow"),
        ],
    )
    text = build_briefing_text(data)
    # 通常のやることと曜日ごとのやることが別の文で読み上げられる
    assert "今日のやることは、牛乳を買う、電気代の支払い、以上です。" in text
    assert "曜日ごとのやることは、燃えるゴミ出し、以上です。" in text


def test_build_briefing_text_holiday():
    data = TodayData(
        date="2026-01-01",
        weekday="木曜日",
        events=[],
        stock_tasks=[],
        flow_tasks=[],
        is_holiday=True,
        holiday_name="元日",
    )
    text = build_briefing_text(data)
    assert "元日でお休みです。" in text


@pytest.mark.asyncio
async def test_briefing_endpoint(client):
    await refresh_data()
    res = await client.get("/api/briefing")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/plain")
    body = res.text
    assert "おはようございます。" in body
    # モックの予定・タスクが読み上げ文に含まれる
    assert "テスト会議" in body
    assert "今日のやることは、テストフロー" in body


@pytest.mark.asyncio
async def test_briefing_endpoint_requires_token(auth_client):
    res = await auth_client.get("/api/briefing")
    assert res.status_code == 401
