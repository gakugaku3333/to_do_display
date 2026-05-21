import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import close_connection, init_db
from app.logging_config import setup_logging
from app.routers import dashboard, health, reminders, tasks
from app.scheduler import refresh_data, start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    logger.info("ダッシュボード起動中...")
    await init_db()
    start_scheduler()
    # 初回データ取得はバックグラウンドで実行（Reminders 同期に数分かかる場合がある）
    asyncio.create_task(refresh_data())
    logger.info("ダッシュボード起動完了（データ取得はバックグラウンドで実行中）")
    yield
    stop_scheduler()
    await close_connection()
    logger.info("ダッシュボードを停止しました")


app = FastAPI(title="Family Dashboard", lifespan=lifespan)

app.include_router(dashboard.router)
app.include_router(tasks.router)
app.include_router(health.router)
app.include_router(reminders.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    html = Path("static/index.html").read_text(encoding="utf-8")
    html = html.replace("__API_TOKEN__", settings.api_token)
    return HTMLResponse(html)
