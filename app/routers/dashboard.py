import asyncio
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.auth import verify_token
from app.data_assembler import get_current_data, get_empty_data
from app.models import TodayData
from app.sse import sse_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/today", response_model=TodayData, dependencies=[Depends(verify_token)])
async def get_today():
    data = await get_current_data()
    if data is None:
        # キャッシュが未構築の場合は空データを返す（バックグラウンドで取得中）
        data = get_empty_data()
    return data


@router.get("/api/stream", dependencies=[Depends(verify_token)])
async def event_stream(request: Request):
    queue = sse_manager.connect()

    async def generate():
        try:
            # 初回接続時に現在データを即送信
            data = await get_current_data()
            if data is None:
                data = get_empty_data()
            yield f"data: {data.model_dump_json()}\n\n"

            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    # keepalive（プロキシ/ブラウザのタイムアウト防止）
                    yield ": keepalive\n\n"

                # クライアント切断チェック
                if await request.is_disconnected():
                    break
        finally:
            sse_manager.disconnect(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
