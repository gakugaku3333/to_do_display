from __future__ import annotations

import asyncio
import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.models import TodayData, CalendarEvent, Task
from app.services import google_calendar, icloud_reminders

logger = logging.getLogger(__name__)

_cache: dict = {"data": None}
_last_refresh: str | None = None
_scheduler = AsyncIOScheduler()

WEEKDAYS_JA = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]


async def refresh_data():
    global _last_refresh
    from app.database import cleanup_old_flow_completions
    today = date.today()
    today_str = today.isoformat()
    weekday_ja = WEEKDAYS_JA[today.weekday()]

    await cleanup_old_flow_completions(today_str)

    events: list[CalendarEvent] = []
    try:
        events = await asyncio.to_thread(google_calendar.fetch_today_events)
    except Exception:
        logger.error("Google Calendar の取得に失敗しました", exc_info=True)

    stock_tasks: list[Task] = []
    flow_tasks: list[Task] = []
    try:
        stock_tasks, flow_tasks = await asyncio.to_thread(icloud_reminders.fetch_tasks)
    except Exception:
        logger.error("iCloud Reminders の取得に失敗しました", exc_info=True)

    _cache["data"] = TodayData(
        date=today_str,
        weekday=weekday_ja,
        events=events,
        stock_tasks=stock_tasks,
        flow_tasks=flow_tasks,
    )
    _last_refresh = today_str
    logger.info("データ更新完了: %s %s", today_str, weekday_ja)

    # SSEブロードキャスト（Phase 2で有効化）
    try:
        from app.sse import sse_manager
        from app.data_assembler import get_current_data
        data = await get_current_data()
        if data:
            await sse_manager.broadcast(data.model_dump_json())
    except ImportError:
        pass


def get_cached_data() -> TodayData | None:
    return _cache.get("data")


def get_last_refresh() -> str | None:
    return _last_refresh


def start_scheduler():
    _scheduler.add_job(refresh_data, "interval", minutes=5, id="refresh_data")
    _scheduler.start()


def stop_scheduler():
    _scheduler.shutdown()
