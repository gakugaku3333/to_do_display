from __future__ import annotations

from datetime import date

from app.database import get_completed_ids, get_pending_proposals
from app.models import EventProposal, TodayData, WEEKDAYS_JA


async def get_current_data() -> TodayData | None:
    """キャッシュデータに完了状態・提案をマージして返す"""
    from app.scheduler import get_cached_data

    data = get_cached_data()
    if data is None:
        return None

    completed_ids = await get_completed_ids()
    pending = await get_pending_proposals()

    # ダッシュボードでチェック済みのタスクはリストから除外（フェードアウト後に消える）
    updated_stock = [t for t in data.stock_tasks if t.id not in completed_ids]
    updated_flow = [t for t in data.flow_tasks if t.id not in completed_ids]

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


async def broadcast_current_data():
    """現在のデータをSSE経由で全クライアントに配信する"""
    from app.sse import sse_manager

    data = await get_current_data()
    if data:
        await sse_manager.broadcast(data.model_dump_json())
