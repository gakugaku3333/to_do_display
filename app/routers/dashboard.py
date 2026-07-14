import asyncio
import logging
import time
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response, StreamingResponse

from app.auth import verify_token
from app.data_assembler import get_current_data, get_empty_data, get_week_data
from app.models import WeekData
from app.services.briefing import build_briefing_text, get_briefing_audio
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


@router.get("/api/briefing", dependencies=[Depends(verify_token)])
async def briefing() -> PlainTextResponse:
    """朝の音声ブリーフィング用の読み上げテキストを平文で返す。

    iOS ショートカット（個人用オートメーション）から毎朝呼び出し、
    「テキストを読み上げる」アクションで再生する想定。
    """
    data = await get_current_data()
    if data is None:
        data = get_empty_data()
    return PlainTextResponse(build_briefing_text(data), headers={"Cache-Control": "no-cache"})


@router.get("/api/briefing/audio", dependencies=[Depends(verify_token)])
async def briefing_audio() -> Response:
    """朝の音声ブリーフィングをmp3で返す。

    タブレットにはTTSエンジンが無いため、サーバー（Mac）側のsayコマンドで
    音声合成した結果を配信し、ブラウザは<audio>で再生するだけにする。
    合成には数秒かかるため当日分は1時間キャッシュする（毎朝6:30の事前生成ジョブ
    でウォームアップ済みなら、ボタンを押した瞬間にキャッシュ済み音声が返る）。

    起動直後などバックグラウンドのデータ取得が未完了（get_current_dataがNone）の
    場合は、空のブリーフィングを読み上げてしまわないよう503を返す。
    """
    data = await get_current_data()
    if data is None:
        raise HTTPException(status_code=503, detail="データ取得が未完了です")
    audio = await get_briefing_audio(data)
    return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "no-cache"})


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
