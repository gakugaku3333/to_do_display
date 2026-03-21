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
    assert "sse_clients" in data


@pytest.mark.asyncio
async def test_health_check_db_ok(client):
    res = await client.get("/api/health")
    data = res.json()
    assert data["db"] is True
    assert data["status"] == "ok"
