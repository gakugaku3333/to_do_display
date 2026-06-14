import asyncio
import logging
import time
from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.auth import verify_token
from app.data_assembler import get_current_data, get_empty_data, get_week_data
from app.models import WeekData
from app.sse import sse_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# 週間予定は Google Calendar をオンデマンド取得するため、短時間の連打で
# 同じ取得を繰り返さないよう TTL キャッシュする。日付が変わったら無効化する。
_WEEK_TTL_SECONDS = 300
_week_cache: tuple[float, str, WeekData] | None = None  # (取得時刻, 取得日, データ)


@router.get("/api/week", dependencies=[Depends(verify_token)])
async def week_view() -> WeekData:
    global _week_cache
    now = time.monotonic()
    today = date.today().isoformat()
    if _week_cache and _week_cache[1] == today and now - _week_cache[0] < _WEEK_TTL_SECONDS:
        return _week_cache[2]

    data = await get_week_data()
    _week_cache = (now, today, data)
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
