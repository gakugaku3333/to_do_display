from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.data_assembler import broadcast_current_data
from app.database import cleanup_old_flow_completions
from app.models import CalendarEvent, Task, TodayData, WEEKDAYS_JA
from app.services import google_calendar, icloud_reminders

logger = logging.getLogger(__name__)

_cached_data: TodayData | None = None
_last_refresh: datetime | None = None
_scheduler = AsyncIOScheduler()


async def refresh_data():
    global _cached_data, _last_refresh
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

    now_jst = datetime.now(ZoneInfo("Asia/Tokyo"))
    _cached_data = TodayData(
        date=today_str,
        weekday=weekday_ja,
        events=events,
        stock_tasks=stock_tasks,
        flow_tasks=flow_tasks,
        last_refresh=now_jst.strftime("%H:%M"),
    )
    _last_refresh = now_jst
    logger.info("データ更新完了: %s %s", today_str, weekday_ja)

    await broadcast_current_data()


def get_cached_data() -> TodayData | None:
    return _cached_data


def get_last_refresh() -> datetime | None:
    return _last_refresh


def start_scheduler():
    _scheduler.add_job(refresh_data, "interval", minutes=5, id="refresh_data")
    _scheduler.start()


def stop_scheduler():
    _scheduler.shutdown()
