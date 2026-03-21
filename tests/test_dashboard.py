from __future__ import annotations

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
