import pytest


@pytest.mark.asyncio
async def test_get_today_returns_valid_data(client):
    res = await client.get("/api/today")
    assert res.status_code == 200
    data = res.json()
    assert "date" in data
    assert "weekday" in data
    assert "events" in data
    assert "stock_tasks" in data
    assert "flow_tasks" in data


@pytest.mark.asyncio
async def test_get_today_contains_mock_events(client):
    res = await client.get("/api/today")
    data = res.json()
    assert len(data["events"]) >= 1
    assert data["events"][0]["title"] == "テスト会議"


@pytest.mark.asyncio
async def test_get_today_contains_mock_tasks(client):
    res = await client.get("/api/today")
    data = res.json()
    assert len(data["stock_tasks"]) >= 1
    assert data["stock_tasks"][0]["title"] == "テストタスク"
    assert len(data["flow_tasks"]) >= 1
    assert data["flow_tasks"][0]["title"] == "テストフロー"
