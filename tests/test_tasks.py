import pytest


@pytest.mark.asyncio
async def test_complete_task(client):
    res = await client.post(
        "/api/tasks/complete",
        json={"task_id": "stock-1", "task_type": "stock", "due_date": "2026-03-21"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_uncomplete_task(client):
    # まず完了にしてから取消
    await client.post(
        "/api/tasks/complete",
        json={"task_id": "stock-1", "task_type": "stock", "due_date": "2026-03-21"},
    )
    res = await client.post("/api/tasks/uncomplete", json={"task_id": "stock-1"})
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_complete_invalid_task_type(client):
    res = await client.post(
        "/api/tasks/complete",
        json={"task_id": "stock-1", "task_type": "invalid"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_completed_task_reflected_in_today(client):
    from app.data_assembler import get_current_data
    from app.scheduler import refresh_data

    await refresh_data()
    await client.post(
        "/api/tasks/complete",
        json={"task_id": "stock-1", "task_type": "stock", "due_date": "2026-03-21"},
    )
    # 完了済みタスクはダッシュボード表示リストから除外される（フェードアウト後に消える）
    data = await get_current_data()
    assert data is not None
    stock = [t for t in data.stock_tasks if t.id == "stock-1"]
    assert stock == []
