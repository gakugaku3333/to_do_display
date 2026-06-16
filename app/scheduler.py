from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

import jpholiday
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.data_assembler import broadcast_current_data
from app.database import (
    cleanup_old_flow_completions,
    get_prev_weather_temps,
    get_weather_cache,
    save_weather_cache,
)
from app.models import CalendarEvent, Task, TodayData, WeatherData, WEEKDAYS_JA
from app.services import google_calendar, icloud_reminders
from app.services import weather as weather_service

logger = logging.getLogger(__name__)

_cached_data: TodayData | None = None
_cached_weather: WeatherData | None = None
_last_refresh: datetime | None = None
_scheduler = AsyncIOScheduler()


def _delta(today_val: int | None, prev_val: int | None) -> int | None:
    if today_val is None or prev_val is None:
        return None
    return today_val - prev_val


async def _apply_weather(weather: WeatherData):
    """取得済みの天気をメモリに反映し、SSEで配信する。"""
    global _cached_weather, _cached_data
    _cached_weather = weather
    if _cached_data:
        _cached_data = _cached_data.model_copy(update={"weather": weather})
        await broadcast_current_data()


async def refresh_weather(force: bool = False):
    """気象庁から久留米市の天気を取得し、前日比つきでキャッシュ・配信する。

    取得は1日1回が原則。force=False（起動時のキャッチアップ）では、当日分が
    既にDBにあればAPIを叩かずDBから復元する。force=True（毎朝6時のcron）は
    その日の最新予報を必ず取り直す。前日比は weather_cache の前日分から算出する。
    """
    today_str = date.today().isoformat()
    try:
        if not force:
            cached = await get_weather_cache(today_str)
            if cached:
                # 当日分は取得済み → APIを叩かずに復元
                await _apply_weather(WeatherData.model_validate_json(cached["payload"]))
                logger.info("天気は当日分を取得済み（DBから復元）: %s", today_str)
                return

        result = await asyncio.to_thread(weather_service.fetch_weather)
        if not result:
            return

        prev = await get_prev_weather_temps(today_str)
        prev_max, prev_min = prev if prev else (None, None)
        weather = WeatherData(
            **result,
            temp_max_delta=_delta(result.get("temp_max"), prev_max),
            temp_min_delta=_delta(result.get("temp_min"), prev_min),
        )

        await save_weather_cache(
            today_str, result.get("temp_max"), result.get("temp_min"),
            weather.model_dump_json(),
        )
        await _apply_weather(weather)
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
    # 毎朝 6:00 にその日の最新予報を取得（force=True で必ず取り直す）
    _scheduler.add_job(
        refresh_weather, "cron",
        hour=6, minute=0, timezone=settings.timezone,
        kwargs={"force": True},
        id="refresh_weather", max_instances=1, coalesce=True,
    )
    _scheduler.start()


def stop_scheduler():
    _scheduler.shutdown()
