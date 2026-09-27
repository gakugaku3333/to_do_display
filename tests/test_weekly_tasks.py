import pytest


@pytest.mark.asyncio
async def test_missing_weekly_task_returns_404_after_create(client):
    created = await client.post(
        "/api/weekly-tasks",
        json={"title": "掃除", "weekdays": [1]},
    )
    assert created.status_code == 200

    updated = await client.put(
        "/api/weekly-tasks/missing",
        json={"title": "片付け", "weekdays": [2]},
    )
    deleted = await client.delete("/api/weekly-tasks/missing")

    assert updated.status_code == 404
    assert updated.json() == {"detail": "タスクが見つかりません"}
    assert deleted.status_code == 404
    assert deleted.json() == {"detail": "タスクが見つかりません"}
