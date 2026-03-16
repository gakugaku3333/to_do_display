from datetime import date

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.database import get_completed_ids
from app.models import TodayData
from app.scheduler import get_cached_data, refresh_data

router = APIRouter()

WEEKDAYS_JA = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]


@router.get("/api/today", response_model=TodayData)
async def get_today():
    data = get_cached_data()
    if data is None:
        await refresh_data()
        data = get_cached_data()

    if data is None:
        today = date.today()
        data = TodayData(
            date=today.isoformat(),
            weekday=WEEKDAYS_JA[today.weekday()],
            events=[],
            stock_tasks=[],
            flow_tasks=[],
        )

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
