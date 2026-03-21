from __future__ import annotations

import asyncio
import os
import tempfile
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.models import CalendarEvent, Task


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _mock_fetch_today_events(*args, **kwargs):
    return [
        CalendarEvent(
            id="event-1",
            title="テスト会議",
            start_time="10:00",
            end_time="11:00",
            is_all_day=False,
            owner="husband",
            color="#4A90D9",
        ),
    ]


def _mock_fetch_tasks(*args, **kwargs):
    from datetime import date
    today = date.today().isoformat()
    stock = [
        Task(id="stock-1", title="テストタスク", task_type="stock",
             due_date=today, is_overdue=False, is_completed=False),
    ]
    flow = [
        Task(id="flow-1", title="テストフロー", task_type="flow",
             due_date=today, is_overdue=False, is_completed=False),
    ]
    return stock, flow


@asynccontextmanager
async def _create_test_client(api_token: str = ""):
    """テストクライアント共通セットアップ"""
    import app.database as db_module
    import app.config as config_module

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    db_module._connection = None
    db_module.DB_PATH = tmp.name

    original_token = config_module.settings.api_token
    config_module.settings.api_token = api_token

    with patch("app.services.google_calendar.fetch_today_events", _mock_fetch_today_events), \
         patch("app.services.icloud_reminders.fetch_tasks", _mock_fetch_tasks):

        from app.main import app as fastapi_app

        await db_module.init_db()

        transport = ASGITransport(app=fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    config_module.settings.api_token = original_token
    await db_module.close_connection()
    os.unlink(tmp.name)


@pytest_asyncio.fixture
async def client():
    async with _create_test_client(api_token="") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client():
    """認証トークン付きクライアント"""
    async with _create_test_client(api_token="test-secret-token") as ac:
        yield ac
