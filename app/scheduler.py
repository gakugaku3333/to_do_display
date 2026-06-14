from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

import jpholiday
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.data_assembler import broadcast_current_data
from app.database import cleanup_old_flow_completions
from app.models import CalendarEvent, Task, TodayData, WeatherData, WEEKDAYS_JA
from app.services import google_calendar, icloud_reminders
from app.services import weather as weather_service

logger = logging.getLogger(__name__)

_cached_data: TodayData | None = None
_cached_weather: WeatherData | None = None
_last_refresh: datetime | None = None
_scheduler = AsyncIOScheduler()


async def refresh_weather():
    """Open-Meteo から久留米市の天気を取得してキャッシュを更新する"""
    global _cached_weather, _cached_data
    try:
        result = await asyncio.to_thread(weather_service.fetch_weather)
        if result:
            _cached_weather = WeatherData(**result)
            if _cached_data:
                _cached_data = _cached_data.model_copy(update={"weather": _cached_weather})
                await broadcast_current_data()
    except Exception:
        logger.error("天気情報の更新に失敗しました", exc_info=True)


async def refresh_data():
    global _cached_data, _last_refresh
    today = date.today()
    today_str = today.isoformat()
    weekday_ja = WEEKDAYS_JA[today.weekday()]
    holiday_name: str | None = jpholiday.is_holiday_name(today) or None
    is_holiday = holiday_name is not None

    await cleanup_old_flow_completions(today_str)

    events: list[CalendarEvent] = []
    try:
        events = await asyncio.to_thread(google_calendar.fetch_today_events, settings.timezone)
    except Exception:
        logger.error("Google Calendar の取得に失敗しました", exc_info=True)

    stock_tasks: list[Task] = []
    flow_tasks: list[Task] = []
    try:
        stock_tasks, flow_tasks = await asyncio.to_thread(icloud_reminders.fetch_tasks)
    except Exception:
        logger.error("iCloud Reminders の取得に失敗しました", exc_info=True)

    now_local = datetime.now(ZoneInfo(settings.timezone))
    _cached_data = TodayData(
        date=today_str,
        weekday=weekday_ja,
        events=events,
        stock_tasks=stock_tasks,
        flow_tasks=flow_tasks,
        last_refresh=now_local.strftime("%H:%M"),
        weather=_cached_weather,
        is_holiday=is_holiday,
        holiday_name=holiday_name,
    )
    _last_refresh = now_local
    logger.info("データ更新完了: %s %s", today_str, weekday_ja)

    await broadcast_current_data()


def get_cached_data() -> TodayData | None:
    return _cached_data


def get_last_refresh() -> datetime | None:
    return _last_refresh


def start_scheduler():
    _scheduler.add_job(
        refresh_data, "interval", minutes=5,
        id="refresh_data", max_instances=1, coalesce=True,
    )
    # 毎朝 6:15 に天気予報を更新
    _scheduler.add_job(
        refresh_weather, "cron",
        hour=6, minute=15, timezone=settings.timezone,
        id="refresh_weather", max_instances=1, coalesce=True,
    )
    _scheduler.start()


def stop_scheduler():
    _scheduler.shutdown()
