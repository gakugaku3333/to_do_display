import pytest


@pytest.mark.asyncio
async def test_health_check_returns_200(client):
    res = await client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "db" in data
    assert "google_calendar" in data
    assert "icloud" in data
    assert "last_refresh" in data
    assert "last_sync" in data
    assert "sse_clients" in data
    assert "warnings" in data


@pytest.mark.asyncio
async def test_health_check_db_ok(client):
    res = await client.get("/api/health")
    data = res.json()
    assert data["db"] is True
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_check_google_calendar_not_configured(client):
    """トークンファイルが無い環境では configured=False で警告も出ない。"""
    res = await client.get("/api/health")
    data = res.json()
    assert data["google_calendar"]["husband"]["configured"] is False
    assert data["google_calendar"]["wife"]["configured"] is False
    assert data["warnings"] == []


@pytest.mark.asyncio
async def test_health_check_last_sync_has_all_sources(client):
    res = await client.get("/api/health")
    data = res.json()
    assert set(data["last_sync"].keys()) == {"calendar", "reminders", "weather"}
