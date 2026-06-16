from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import verify_token
from app.config import settings
from app.data_assembler import broadcast_current_data
from app.database import mark_complete, mark_incomplete
from app.services.icloud_reminders import set_reminder_completed

logger = logging.getLogger(__name__)

router = APIRouter()


def _reminder_list_names() -> list[str]:
    """Reminders 由来タスクが属しうるリスト名（書き戻し時の検索範囲）。"""
    return [settings.stock_list_name, settings.flow_list_name]


# task_id は Reminders 由来だと "x-apple-reminder://UUID" の形式でスラッシュを含むため、
# URL パスパラメータには載せられない（FastAPI のパス変換でマッチせず 404 になる）。
# 必ずリクエストボディで受け取ること。
class CompleteRequest(BaseModel):
    task_id: str
    task_type: str  # "stock", "flow", "weekly"
    due_date: str | None = None


class UncompleteRequest(BaseModel):
    task_id: str


@router.post("/api/tasks/complete", dependencies=[Depends(verify_token)])
async def complete_task(body: CompleteRequest):
    if body.task_type not in ("stock", "flow", "weekly"):
        raise HTTPException(status_code=400, detail="task_type は 'stock', 'flow', 'weekly' を指定してください")

    # 曜日タスクは due_date をサーバー側で今日に設定（日次リセットのため）
    from datetime import date as _date
    effective_due_date = body.due_date
    if body.task_type == "weekly":
        effective_due_date = _date.today().isoformat()

    await mark_complete(body.task_id, body.task_type, effective_due_date)
    await broadcast_current_data()

    # Reminders 書き戻しは Reminders 由来タスクのみ（weekly は不要）
    if body.task_type in ("stock", "flow"):
        list_name = settings.stock_list_name if body.task_type == "stock" else settings.flow_list_name
        asyncio.create_task(asyncio.to_thread(set_reminder_completed, body.task_id, True, [list_name]))

    return {"status": "ok", "task_id": body.task_id}


@router.post("/api/tasks/uncomplete", dependencies=[Depends(verify_token)])
async def uncomplete_task(body: UncompleteRequest):
    await mark_incomplete(body.task_id)
    await broadcast_current_data()
    # weekly タスクは Reminders に存在しないので書き戻し不要。
    # それ以外は stock/flow どちらか不明なため両リストを候補に書き戻す。
    if not body.task_id.startswith("weekly_"):
        asyncio.create_task(
            asyncio.to_thread(set_reminder_completed, body.task_id, False, _reminder_list_names())
        )
    return {"status": "ok", "task_id": body.task_id}
