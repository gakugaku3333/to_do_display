import asyncio
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.models import TodayData, CalendarEvent, Task
from app.services import google_calendar, icloud_reminders

_cache: dict = {"data": None}
_scheduler = AsyncIOScheduler()

WEEKDAYS_JA = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]


async def refresh_data():
    from app.database import cleanup_old_flow_completions
    today = date.today()
    today_str = today.isoformat()
    weekday_ja = WEEKDAYS_JA[today.weekday()]

    await cleanup_old_flow_completions(today_str)

    events: list[CalendarEvent] = []
    try:
        events = await asyncio.to_thread(google_calendar.fetch_today_events)
    except Exception as e:
        print(f"[Scheduler] Google Calendar エラー: {e}")

    stock_tasks: list[Task] = []
    flow_tasks: list[Task] = []
    try:
        stock_tasks, flow_tasks = await asyncio.to_thread(icloud_reminders.fetch_tasks)
    except Exception as e:
        print(f"[Scheduler] iCloud Reminders エラー: {e}")

    _cache["data"] = TodayData(
        date=today_str,
        weekday=weekday_ja,
        events=events,
        stock_tasks=stock_tasks,
        flow_tasks=flow_tasks,
    )
    print(f"[Scheduler] データ更新完了: {today_str} {weekday_ja}")


def get_cached_data() -> TodayData | None:
    return _cache.get("data")


def start_scheduler():
    _scheduler.add_job(refresh_data, "interval", minutes=5, id="refresh_data")
    _scheduler.start()


def stop_scheduler():
    _scheduler.shutdown()
