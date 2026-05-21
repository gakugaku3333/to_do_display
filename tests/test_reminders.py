from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_create_reminder_success(client):
    with patch(
        "app.routers.reminders.create_reminder", return_value="x-apple-id-123"
    ), patch("app.routers.reminders.refresh_data", return_value=None):
        res = await client.post(
            "/api/reminders",
            json={
                "list": "ストック",
                "title": "プリント返却",
                "notes": "📋 算数プリント",
                "due_date": "2026-05-25",
            },
        )
    assert res.status_code == 200
    assert res.json() == {"id": "x-apple-id-123"}


@pytest.mark.asyncio
async def test_create_reminder_invalid_list(client):
    res = await client.post(
        "/api/reminders",
        json={"list": "存在しないリスト", "title": "test", "notes": "", "due_date": None},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_create_reminder_applescript_failure(client):
    with patch("app.routers.reminders.create_reminder", return_value=None):
        res = await client.post(
            "/api/reminders",
            json={"list": "ストック", "title": "fail", "notes": "", "due_date": None},
        )
    assert res.status_code == 500


@pytest.mark.asyncio
async def test_create_reminder_requires_auth(auth_client):
    res = await auth_client.post(
        "/api/reminders",
        json={"list": "ストック", "title": "test", "notes": "", "due_date": None},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_create_reminder_with_valid_auth(auth_client):
    with patch(
        "app.routers.reminders.create_reminder", return_value="x-apple-id-456"
    ), patch("app.routers.reminders.refresh_data", return_value=None):
        res = await auth_client.post(
            "/api/reminders",
            headers={"Authorization": "Bearer test-secret-token"},
            json={"list": "フロー", "title": "test", "notes": "", "due_date": None},
        )
    assert res.status_code == 200
    assert res.json()["id"] == "x-apple-id-456"
