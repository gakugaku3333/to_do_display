import asyncio
import logging
import time
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response, StreamingResponse

from app.auth import verify_token
from app.daily_cache import DailyTTLCache
from app.data_assembler import get_current_data, get_empty_data, get_week_data
from app.models import TodayData, WeekData
from app.services import speaker
from app.services.briefing import build_briefing_text, get_briefing_audio
from app.sse import sse_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# 週間予定は Google Calendar をオンデマンド取得するため、短時間の連打で
# 同じ取得を繰り返さないよう TTL キャッシュする。日付が変わったら無効化する。
_week_cache: DailyTTLCache[WeekData] = DailyTTLCache(ttl_seconds=300)


async def _current_data_or_empty() -> TodayData:
    """キャッシュ未取得（起動直後）でも表示できるよう、空データで代替する。"""
    return await get_current_data() or get_empty_data()


async def _require_current_data() -> TodayData:
    """起動直後などデータ取得が未完了なら 503 を返す（空の読み上げを防ぐ）。"""
    data = await get_current_data()
    if data is None:
        raise HTTPException(status_code=503, detail="データ取得が未完了です")
    return data


@router.get("/api/week", dependencies=[Depends(verify_token)])
async def week_view() -> WeekData:
    today = date.today().isoformat()
    cached = _week_cache.get(today)
    if cached is not None:
        return cached

    started = time.monotonic()
    data = await get_week_data()
    _week_cache.set(today, data, saved_at=started)
    return data


@router.get("/api/briefing", dependencies=[Depends(verify_token)])
async def briefing() -> PlainTextResponse:
    """朝の音声ブリーフィング用の読み上げテキストを平文で返す。

    iOS ショートカット（個人用オートメーション）から毎朝呼び出し、
    「テキストを読み上げる」アクションで再生する想定。
    """
    data = await _current_data_or_empty()
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
    audio = await get_briefing_audio(await _require_current_data())
    return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "no-cache"})


@router.post("/api/briefing/speak", dependencies=[Depends(verify_token)])
async def briefing_speak() -> dict:
    """ブリーフィングを今すぐ Google Home で再生する（手動・ショートカット用）。"""
    await _require_current_data()
    try:
        await speak_briefing()
    except Exception as e:
        logger.error("Google Home での再生に失敗しました", exc_info=True)
        raise HTTPException(status_code=502, detail=str(e))
    return {"status": "ok"}


@router.get("/api/briefing/cast/{nonce}.mp3")
async def briefing_cast_audio(nonce: str) -> Response:
    """Google Home が取りに来る音声。

    Cast デバイスは認証ヘッダーを付けられないため、トークンの代わりに
    再生ごとに変わる推測不能な nonce を URL に含めて保護する。
    """
    audio = speaker.get_published_audio(nonce)
    if audio is None:
        raise HTTPException(status_code=404)
    return Response(content=audio, media_type="audio/mpeg")


async def speak_briefing() -> None:
    """最新データのブリーフィング音声を Google Home で再生する。"""
    data = await get_current_data()
    if data is None:
        raise RuntimeError("データ取得が未完了です")
    audio = await get_briefing_audio(data)
    await asyncio.to_thread(speaker.play, audio)


@router.get("/api/stream", dependencies=[Depends(verify_token)])
async def event_stream(request: Request):
    queue = sse_manager.connect()

    async def generate():
        try:
            # 初回接続時に現在データを即送信
            data = await _current_data_or_empty()
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
