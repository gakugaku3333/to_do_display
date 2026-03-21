import pytest


@pytest.mark.asyncio
async def test_no_token_returns_401(auth_client):
    res = await auth_client.get("/api/today")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_valid_bearer_token_returns_200(auth_client):
    res = await auth_client.get(
        "/api/today",
        headers={"Authorization": "Bearer test-secret-token"},
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_invalid_token_returns_401(auth_client):
    res = await auth_client.get(
        "/api/today",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_query_param_token_returns_200(auth_client):
    res = await auth_client.get("/api/today?token=test-secret-token")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_health_check_no_auth_required(auth_client):
    """ヘルスチェックは認証不要"""
    res = await auth_client.get("/api/health")
    assert res.status_code == 200
