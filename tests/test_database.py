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
