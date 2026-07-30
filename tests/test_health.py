import pytest

from app.routers import health


@pytest.fixture(autouse=True)
def isolate_tokens(monkeypatch, tmp_path):
    """テストが本物の tokens/ を読んで Google に refresh を投げないようにする。

    /api/health は認証の実効性を確認するため get_credentials() を呼ぶので、
    隔離しないとテストがネットワーク依存になる（pre-commit の pytest が遅く・不安定になる）。
    """
    monkeypatch.setattr(health, "TOKENS_DIR", str(tmp_path))
    monkeypatch.setattr(health, "get_credentials", lambda account: None)


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


@pytest.mark.asyncio
async def test_health_reports_expired_google_token(client, monkeypatch, tmp_path):
    """トークンはあるのに refresh できない＝失効。needs_reauth に出て status は degraded。"""
    (tmp_path / "husband.json").write_text("{}")
    monkeypatch.setattr(health, "TOKENS_DIR", str(tmp_path))
    monkeypatch.setattr(health, "get_credentials", lambda account: None)

    data = (await client.get("/api/health")).json()
    assert data["google_calendar"]["husband"] is False
    assert data["google_calendar"]["detail"]["husband"]["state"] == "expired"
    assert data["google_calendar"]["needs_reauth"] == ["husband"]
    assert data["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_untokened_account_is_missing_not_expired(client, monkeypatch, tmp_path):
    """未認証アカウント（トークンなし）は再認証を促さない。"""
    monkeypatch.setattr(health, "TOKENS_DIR", str(tmp_path))
    monkeypatch.setattr(health, "get_credentials", lambda account: None)

    data = (await client.get("/api/health")).json()
    assert data["google_calendar"]["detail"]["wife"]["state"] == "missing"
    assert data["google_calendar"]["needs_reauth"] == []
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_valid_token_is_ok(client, monkeypatch, tmp_path):
    (tmp_path / "husband.json").write_text("{}")
    monkeypatch.setattr(health, "TOKENS_DIR", str(tmp_path))
    monkeypatch.setattr(health, "get_credentials", lambda account: object())

    data = (await client.get("/api/health")).json()
    assert data["google_calendar"]["husband"] is True
    assert data["google_calendar"]["needs_reauth"] == []
    assert data["status"] == "ok"
