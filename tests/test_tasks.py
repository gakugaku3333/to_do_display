import pytest


@pytest.mark.asyncio
async def test_complete_task(client):
    res = await client.post(
        "/api/tasks/stock-1/complete",
        json={"task_type": "stock", "due_date": "2026-03-21"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_uncomplete_task(client):
    # まず完了にしてから取消
    await client.post(
        "/api/tasks/stock-1/complete",
        json={"task_type": "stock", "due_date": "2026-03-21"},
    )
    res = await client.post("/api/tasks/stock-1/uncomplete")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_complete_invalid_task_type(client):
    res = await client.post(
        "/api/tasks/stock-1/complete",
        json={"task_type": "invalid"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_completed_task_reflected_in_today(client):
    await client.post(
        "/api/tasks/stock-1/complete",
        json={"task_type": "stock", "due_date": "2026-03-21"},
    )
    res = await client.get("/api/today")
    data = res.json()
    stock = [t for t in data["stock_tasks"] if t["id"] == "stock-1"]
    assert len(stock) == 1
    assert stock[0]["is_completed"] is True
