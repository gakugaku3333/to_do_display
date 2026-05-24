from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import verify_token
from app.data_assembler import broadcast_current_data
from app.database import mark_complete, mark_incomplete
from app.services.icloud_reminders import set_reminder_completed

logger = logging.getLogger(__name__)

router = APIRouter()


class CompleteRequest(BaseModel):
    task_type: str  # "stock", "flow", "weekly"
    due_date: str | None = None


@router.post("/api/tasks/{task_id}/complete", dependencies=[Depends(verify_token)])
async def complete_task(task_id: str, body: CompleteRequest):
    if body.task_type not in ("stock", "flow", "weekly"):
        raise HTTPException(status_code=400, detail="task_type は 'stock', 'flow', 'weekly' を指定してください")

    # 曜日タスクは due_date をサーバー側で今日に設定（日次リセットのため）
    from datetime import date as _date
    effective_due_date = body.due_date
    if body.task_type == "weekly":
        effective_due_date = _date.today().isoformat()

    await mark_complete(task_id, body.task_type, effective_due_date)
    await broadcast_current_data()

    # Reminders 書き戻しは Reminders 由来タスクのみ（weekly は不要）
    if body.task_type in ("stock", "flow"):
        asyncio.create_task(asyncio.to_thread(set_reminder_completed, task_id, True))

    return {"status": "ok", "task_id": task_id}


@router.post("/api/tasks/{task_id}/uncomplete", dependencies=[Depends(verify_token)])
async def uncomplete_task(task_id: str):
    await mark_incomplete(task_id)
    await broadcast_current_data()
    # weekly タスクは Reminders に存在しないので書き戻し不要
    # (task_type を保持していないため stock/flow 判定は省略し常に試みる)
    asyncio.create_task(asyncio.to_thread(set_reminder_completed, task_id, False))
    return {"status": "ok", "task_id": task_id}
