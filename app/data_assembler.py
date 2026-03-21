from __future__ import annotations

from datetime import date

from app.database import get_completed_ids
from app.models import TodayData
from app.scheduler import get_cached_data, WEEKDAYS_JA


async def get_current_data() -> TodayData | None:
    """キャッシュデータに完了状態をマージして返す"""
    data = get_cached_data()
    if data is None:
        return None

    completed_ids = await get_completed_ids()

    updated_stock = [
        t.model_copy(update={"is_completed": t.id in completed_ids})
        for t in data.stock_tasks
    ]
    updated_flow = [
        t.model_copy(update={"is_completed": t.id in completed_ids})
        for t in data.flow_tasks
    ]

    return TodayData(
        date=data.date,
        weekday=data.weekday,
        events=data.events,
        stock_tasks=updated_stock,
        flow_tasks=updated_flow,
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
