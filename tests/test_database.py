import os
import tempfile

import pytest
import pytest_asyncio

import app.database as db_module


@pytest_asyncio.fixture
async def test_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_module._connection = None
    db_module.DB_PATH = tmp.name
    await db_module.init_db()
    yield
    await db_module.close_connection()
    os.unlink(tmp.name)


@pytest.mark.asyncio
async def test_mark_complete_and_get_completed_ids(test_db):
    await db_module.mark_complete("task-1", "stock", "2026-03-21")
    ids = await db_module.get_completed_ids()
    assert "task-1" in ids


@pytest.mark.asyncio
async def test_mark_incomplete_removes_entry(test_db):
    await db_module.mark_complete("task-1", "stock", "2026-03-21")
    await db_module.mark_incomplete("task-1")
    ids = await db_module.get_completed_ids()
    assert "task-1" not in ids


@pytest.mark.asyncio
async def test_create_weekly_task_defaults_to_task_category(test_db):
    task_id = await db_module.create_weekly_task("燃えるゴミ", [0, 3])
    tasks = await db_module.get_all_weekly_tasks()
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["category"] == "task"


@pytest.mark.asyncio
async def test_create_weekly_task_with_trash_category(test_db):
    task_id = await db_module.create_weekly_task("燃えるゴミ", [0, 3], category="trash")
    tasks = await db_module.get_all_weekly_tasks()
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["category"] == "trash"
    assert task["weekdays"] == [0, 3]


@pytest.mark.asyncio
async def test_update_weekly_task_changes_category(test_db):
    task_id = await db_module.create_weekly_task("燃えるゴミ", [0])
    await db_module.update_weekly_task(task_id, "燃えるゴミ", [0], category="trash")
    tasks = await db_module.get_all_weekly_tasks()
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["category"] == "trash"


@pytest.mark.asyncio
async def test_migration_adds_category_column_to_existing_table(test_db):
    """category列が無い旧スキーマのDBでもinit_dbが安全にマイグレーションできる"""
    db = await db_module.get_connection()
    await db.execute("DROP TABLE weekly_tasks")
    await db.execute("""
        CREATE TABLE weekly_tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            weekdays TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    await db.commit()

    await db_module.init_db()

    task_id = await db_module.create_weekly_task("燃えるゴミ", [0], category="trash")
    tasks = await db_module.get_all_weekly_tasks()
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["category"] == "trash"


@pytest.mark.asyncio
async def test_cleanup_old_flow_completions(test_db):
    await db_module.mark_complete("flow-1", "flow", "2026-03-20")
    await db_module.mark_complete("flow-2", "flow", "2026-03-21")
    await db_module.mark_complete("stock-1", "stock", "2026-03-20")

    await db_module.cleanup_old_flow_completions("2026-03-21")

    ids = await db_module.get_completed_ids()
    # flow-1 (古い日付) は削除される
    assert "flow-1" not in ids
    # flow-2 (今日の日付) は残る
    assert "flow-2" in ids
    # stock-1 (stockタイプ) は影響なし
    assert "stock-1" in ids
