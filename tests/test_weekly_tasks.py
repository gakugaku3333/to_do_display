from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_create_weekly_task_defaults_to_task_category(client):
    res = await client.post("/api/weekly-tasks", json={"title": "洗濯物を畳む", "weekdays": [0, 2]})
    assert res.status_code == 200
    task_id = res.json()["id"]

    tasks = (await client.get("/api/weekly-tasks")).json()
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["category"] == "task"


@pytest.mark.asyncio
async def test_create_weekly_task_with_trash_category(client):
    res = await client.post(
        "/api/weekly-tasks",
        json={"title": "燃えるゴミ", "weekdays": [0, 3], "category": "trash"},
    )
    assert res.status_code == 200
    task_id = res.json()["id"]

    tasks = (await client.get("/api/weekly-tasks")).json()
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["category"] == "trash"


@pytest.mark.asyncio
async def test_create_weekly_task_rejects_invalid_category(client):
    res = await client.post(
        "/api/weekly-tasks",
        json={"title": "不正なタスク", "weekdays": [0], "category": "invalid"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_update_weekly_task_changes_category(client):
    create_res = await client.post("/api/weekly-tasks", json={"title": "資源ゴミ", "weekdays": [1]})
    task_id = create_res.json()["id"]

    update_res = await client.put(
        f"/api/weekly-tasks/{task_id}",
        json={"title": "資源ゴミ", "weekdays": [1], "category": "trash"},
    )
    assert update_res.status_code == 200

    tasks = (await client.get("/api/weekly-tasks")).json()
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["category"] == "trash"


@pytest.mark.asyncio
async def test_trash_category_task_appears_in_trash_labels_not_flow(client):
    from datetime import date

    from app.data_assembler import get_current_data
    from app.scheduler import refresh_data

    today_weekday = date.today().weekday()  # 0=月〜6=日
    await client.post(
        "/api/weekly-tasks",
        json={"title": "燃えるゴミ", "weekdays": [today_weekday], "category": "trash"},
    )
    await refresh_data()

    data = await get_current_data()

    assert data is not None
    assert "燃えるゴミ" in data.trash_labels
    assert all(t.title != "燃えるゴミ" for t in data.flow_tasks)


@pytest.mark.asyncio
async def test_weekly_progress_excludes_trash_and_counts_completion(client):
    from datetime import date

    from app.data_assembler import get_current_data
    from app.scheduler import refresh_data

    today_weekday = date.today().weekday()

    # ゴミ出しは完了率の対象外
    await client.post(
        "/api/weekly-tasks",
        json={"title": "燃えるゴミ", "weekdays": [today_weekday], "category": "trash"},
    )
    # 通常の曜日タスクを2件登録
    task1 = (await client.post(
        "/api/weekly-tasks",
        json={"title": "洗濯物を畳む", "weekdays": [today_weekday]},
    )).json()["id"]
    await client.post(
        "/api/weekly-tasks",
        json={"title": "お風呂掃除", "weekdays": [today_weekday]},
    )
    await refresh_data()

    data = await get_current_data()
    assert data.weekly_total == 2
    assert data.weekly_completed == 0

    await client.post(
        "/api/tasks/complete",
        json={"task_id": f"weekly_{task1}", "task_type": "weekly", "due_date": None},
    )

    data = await get_current_data()
    assert data.weekly_total == 2
    assert data.weekly_completed == 1
