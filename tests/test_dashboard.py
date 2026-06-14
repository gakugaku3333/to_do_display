from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app.data_assembler import get_current_data
from app.scheduler import refresh_data


@pytest.mark.asyncio
async def test_get_current_data_returns_valid_structure(client):
    await refresh_data()
    data = await get_current_data()
    assert data is not None
    assert hasattr(data, "date")
    assert hasattr(data, "weekday")
    assert hasattr(data, "events")
    assert hasattr(data, "stock_tasks")
    assert hasattr(data, "flow_tasks")


@pytest.mark.asyncio
async def test_get_current_data_contains_mock_events(client):
    await refresh_data()
    data = await get_current_data()
    assert data is not None
    assert len(data.events) >= 1
    assert data.events[0].title == "テスト会議"


@pytest.mark.asyncio
async def test_get_current_data_contains_mock_tasks(client):
    await refresh_data()
    data = await get_current_data()
    assert data is not None
    assert len(data.stock_tasks) >= 1
    assert data.stock_tasks[0].title == "テストタスク"
    assert len(data.flow_tasks) >= 1
    assert data.flow_tasks[0].title == "テストフロー"


@pytest.mark.asyncio
async def test_week_endpoint_returns_seven_days(client):
    """/api/week は今日起点で7日分の構造を返す"""
    import app.routers.dashboard as dashboard_module

    dashboard_module._week_cache = None  # TTLキャッシュをリセット
    today = date.today()

    def _mock_week(tz_name="Asia/Tokyo", days=7):
        return {(today + timedelta(days=i)).isoformat(): [] for i in range(days)}

    with patch("app.services.google_calendar.fetch_week_events", _mock_week):
        res = await client.get("/api/week")

    assert res.status_code == 200
    body = res.json()
    assert len(body["days"]) == 7
    assert body["days"][0]["date"] == today.isoformat()
    assert body["days"][0]["is_today"] is True
    assert body["days"][1]["is_today"] is False
    assert "weekday" in body["days"][0]
