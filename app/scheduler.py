from __future__ import annotations

import asyncio
import glob
import logging
import os
import shutil
from datetime import date, datetime
from zoneinfo import ZoneInfo

import jpholiday
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.data_assembler import broadcast_current_data
from app.database import (
    DB_PATH,
    cleanup_old_flow_completions,
    get_prev_weather_temps,
    get_weather_cache,
    save_weather_cache,
)
from app.models import CalendarEvent, CountdownEvent, Task, TodayData, WeatherData, WEEKDAYS_JA
from app.services import google_calendar, icloud_reminders
from app.services import weather as weather_service

logger = logging.getLogger(__name__)

_cached_data: TodayData | None = None
_cached_weather: WeatherData | None = None
_last_refresh: datetime | None = None
_scheduler = AsyncIOScheduler()

# 各データソースの最終「成功」時刻・エラー有無（/api/health のセルフ診断用）。
# refresh_data/refresh_weather の内部で個別に更新する。
_last_sync: dict[str, dict] = {
    "calendar": {"success_at": None, "error": False},
    "reminders": {"success_at": None, "error": False},
    "weather": {"success_at": None, "error": False},
}

BACKUP_DIR = "backups"
BACKUP_KEEP = 7


def _mark_sync(source: str, ok: bool):
    now = datetime.now(ZoneInfo(settings.timezone))
    if ok:
        _last_sync[source] = {"success_at": now.isoformat(), "error": False}
    else:
        _last_sync[source] = {**_last_sync[source], "error": True}


def get_sync_status() -> dict:
    return _last_sync


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
                _mark_sync("weather", ok=True)
                return

        result = await asyncio.to_thread(weather_service.fetch_weather)
        if not result:
            _mark_sync("weather", ok=False)
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
        _mark_sync("weather", ok=True)
    except Exception:
        logger.error("天気情報の更新に失敗しました", exc_info=True)
        _mark_sync("weather", ok=False)


async def refresh_data():
    global _cached_data, _last_refresh
    today = date.today()
    today_str = today.isoformat()
    weekday_ja = WEEKDAYS_JA[today.weekday()]
    holiday_name: str | None = jpholiday.is_holiday_name(today) or None
    is_holiday = holiday_name is not None

    await cleanup_old_flow_completions(today_str)

    events: list[CalendarEvent] = []
    countdown_events: list[CountdownEvent] = []
    try:
        events = await asyncio.to_thread(google_calendar.fetch_today_events, settings.timezone)
        raw_countdowns = await asyncio.to_thread(google_calendar.fetch_countdown_events, settings.timezone)
        countdown_events = [CountdownEvent(**c) for c in raw_countdowns]
        _mark_sync("calendar", ok=True)
    except Exception:
        logger.error("Google Calendar の取得に失敗しました", exc_info=True)
        _mark_sync("calendar", ok=False)

    stock_tasks: list[Task] = []
    flow_tasks: list[Task] = []
    try:
        stock_tasks, flow_tasks = await asyncio.to_thread(icloud_reminders.fetch_tasks)
        _mark_sync("reminders", ok=True)
    except Exception:
        logger.error("iCloud Reminders の取得に失敗しました", exc_info=True)
        _mark_sync("reminders", ok=False)

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
        countdown_events=countdown_events,
    )
    _last_refresh = now_local
    logger.info("データ更新完了: %s %s", today_str, weekday_ja)

    await broadcast_current_data()


def get_cached_data() -> TodayData | None:
    return _cached_data


def get_last_refresh() -> datetime | None:
    return _last_refresh


def backup_database():
    """dashboard.db を backups/ に日次コピーし、古い世代を削除する（曜日タスク・配布物提案の保険）。"""
    if not os.path.exists(DB_PATH):
        return
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        today_str = date.today().isoformat()
        dest = os.path.join(BACKUP_DIR, f"dashboard-{today_str}.db")
        shutil.copyfile(DB_PATH, dest)

        backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "dashboard-*.db")))
        for old in backups[:-BACKUP_KEEP]:
            os.remove(old)
        logger.info("dashboard.db をバックアップしました: %s", dest)
    except Exception:
        logger.error("dashboard.db のバックアップに失敗しました", exc_info=True)


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
    # 毎日 3:00 に dashboard.db をバックアップ（7世代ローテーション）
    _scheduler.add_job(
        backup_database, "cron",
        hour=3, minute=0, timezone=settings.timezone,
        id="backup_database", max_instances=1, coalesce=True,
    )
    _scheduler.start()


def stop_scheduler():
    _scheduler.shutdown()
