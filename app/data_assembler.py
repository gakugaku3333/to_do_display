from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import jpholiday

from app.config import settings
from app.database import get_completed_ids, get_pending_proposals, get_weekly_tasks_for_weekday
from app.models import EventProposal, Task, TodayData, WeekData, WeekDay, WEEKDAYS_JA
from app.services import google_calendar


async def get_current_data() -> TodayData | None:
    """キャッシュデータに完了状態・曜日タスク・提案をマージして返す"""
    from app.scheduler import get_cached_data

    data = get_cached_data()
    if data is None:
        return None

    today_weekday = date.fromisoformat(data.date).weekday()  # 0=月〜6=日
    completed_ids = await get_completed_ids()
    pending = await get_pending_proposals()
    weekly_raw = await get_weekly_tasks_for_weekday(today_weekday)

    # ダッシュボードでチェック済みのタスクはリストから除外（フェードアウト後に消える）
    updated_stock = [t for t in data.stock_tasks if t.id not in completed_ids]
    updated_flow = [t for t in data.flow_tasks if t.id not in completed_ids]

    # 曜日タスクをフローに合流（完了済みは除外）
    for wt in weekly_raw:
        task_id = f"weekly_{wt['id']}"
        if task_id not in completed_ids:
            updated_flow.append(Task(
                id=task_id,
                title=wt["title"],
                task_type="weekly",
                is_completed=False,
                owner="shared",
            ))

    proposals = [EventProposal(**p) for p in pending]

    return TodayData(
        date=data.date,
        weekday=data.weekday,
        events=data.events,
        stock_tasks=updated_stock,
        flow_tasks=updated_flow,
        last_refresh=data.last_refresh,
        proposals=proposals,
        weather=data.weather,
        is_holiday=data.is_holiday,
        holiday_name=data.holiday_name,
    )


def get_empty_data() -> TodayData:
    """空のTodayDataを返す（キャッシュが存在しない場合のフォールバック）"""
    today = date.today()
    return TodayData(
        date=today.isoformat(),
        weekday=WEEKDAYS_JA[today.weekday()],
        events=[],
        stock_tasks=[],
        flow_tasks=[],
    )


async def get_week_data(days: int = 7) -> WeekData:
    """今日から days 日間の予定を曜日・祝日情報つきで組み立てて返す。

    Google Calendar をオンデマンドで取得する（ボタン押下時のみ）。SSE で常時配信する
    当日データとは別系統で、キャッシュ更新は呼び出し側（ルーター）の TTL に委ねる。
    """
    grouped = await asyncio.to_thread(google_calendar.fetch_week_events, settings.timezone, days)

    tz = ZoneInfo(settings.timezone)
    today = date.today()
    week_days: list[WeekDay] = []
    for i in range(days):
        d = today + timedelta(days=i)
        ds = d.isoformat()
        holiday_name: str | None = jpholiday.is_holiday_name(d) or None
        week_days.append(WeekDay(
            date=ds,
            weekday=WEEKDAYS_JA[d.weekday()],
            is_today=(i == 0),
            is_holiday=holiday_name is not None,
            holiday_name=holiday_name,
            events=grouped.get(ds, []),
        ))

    return WeekData(days=week_days, last_refresh=datetime.now(tz).strftime("%H:%M"))


async def broadcast_current_data():
    """現在のデータをSSE経由で全クライアントに配信する"""
    from app.sse import sse_manager

    data = await get_current_data()
    if data:
        await sse_manager.broadcast(data.model_dump_json())
