import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import close_connection, init_db
from app.logging_config import setup_logging
from app.routers import dashboard, health, reminders, school_docs, tasks, weekly_tasks
from app.scheduler import refresh_data, refresh_weather, start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)

# create_task の戻り値を保持しないと GC で途中キャンセルされうるため参照を持つ
_startup_tasks: set[asyncio.Task] = set()


def _spawn_startup_task(coro) -> None:
    task = asyncio.create_task(coro)
    _startup_tasks.add(task)
    task.add_done_callback(_startup_tasks.discard)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    logger.info("ダッシュボード起動中...")
    await init_db()
    start_scheduler()
    # 初回データ取得はバックグラウンドで実行（Reminders 同期に数分かかる場合がある）
    _spawn_startup_task(refresh_weather())
    _spawn_startup_task(refresh_data())
    logger.info("ダッシュボード起動完了（データ取得はバックグラウンドで実行中）")
    yield
    stop_scheduler()
    await close_connection()
    logger.info("ダッシュボードを停止しました")


app = FastAPI(title="Family Dashboard", lifespan=lifespan)

app.include_router(dashboard.router)
app.include_router(tasks.router)
app.include_router(weekly_tasks.router)
app.include_router(health.router)
app.include_router(school_docs.router)
app.include_router(reminders.router)

# コード系ファイルは常に再検証させる（StaticFiles は no-cache ヘッダーを付けないため専用ルートで配信）。
# Safari の HTTP キャッシュに古いバージョンが残っていると SW の precache も汚染されるため、
# sw.js / app.js / style.css すべてに no-cache を付与する。
_NO_CACHE = {"Cache-Control": "no-cache"}

@app.get("/static/sw.js")
async def service_worker():
    return FileResponse("static/sw.js", media_type="application/javascript", headers=_NO_CACHE)

@app.get("/static/js/{filepath:path}")
async def js_modules(filepath: str):
    return FileResponse(f"static/js/{filepath}", media_type="application/javascript", headers=_NO_CACHE)

@app.get("/static/style.css")
async def style_css():
    return FileResponse("static/style.css", media_type="text/css", headers=_NO_CACHE)


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    html = Path("static/index.html").read_text(encoding="utf-8")
    html = html.replace("__API_TOKEN__", settings.api_token)
    # index.html は常に最新を配信（SW 登録スクリプトやアセット参照の更新を反映）
    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})
