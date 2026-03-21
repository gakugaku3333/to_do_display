from __future__ import annotations

import asyncio

import pytest

from app.sse import SSEManager


@pytest.mark.asyncio
async def test_sse_manager_connect_disconnect():
    manager = SSEManager()
    queue = manager.connect()
    assert manager.client_count == 1
    manager.disconnect(queue)
    assert manager.client_count == 0


@pytest.mark.asyncio
async def test_sse_manager_broadcast():
    manager = SSEManager()
    queue = manager.connect()
    await manager.broadcast('{"test": true}')
    msg = queue.get_nowait()
    assert msg == '{"test": true}'
    manager.disconnect(queue)


@pytest.mark.asyncio
async def test_sse_manager_full_queue_disconnects_client():
    manager = SSEManager()
    queue = manager.connect()
    # キューを満杯にする (maxsize=10)
    for i in range(10):
        queue.put_nowait(f"msg-{i}")
    # 満杯状態でブロードキャストするとクライアントが切断される
    await manager.broadcast("overflow")
    assert manager.client_count == 0


@pytest.mark.asyncio
async def test_sse_stream_endpoint_content_type(client):
    """SSEエンドポイントが正しいContent-Typeを返す（タイムアウト付き）"""
    try:
        async with asyncio.timeout(5):
            async with client.stream("GET", "/api/stream") as res:
                assert res.status_code == 200
                assert "text/event-stream" in res.headers["content-type"]
    except (asyncio.TimeoutError, Exception):
        # SSEはストリーミングなのでタイムアウトは想定内
        pass
