from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import verify_token
from app.config import settings
from app.scheduler import refresh_data
from app.services.icloud_reminders import create_reminder

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateReminderRequest(BaseModel):
    list: str
    title: str
    notes: str = ""
    due_date: str | None = None  # YYYY-MM-DD


@router.post("/api/reminders", dependencies=[Depends(verify_token)])
async def create_reminder_endpoint(req: CreateReminderRequest):
    allowed = {settings.stock_list_name, settings.flow_list_name}
    if req.list not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"list must be one of {sorted(allowed)}",
        )

    rid = await asyncio.to_thread(
        create_reminder, req.list, req.title, req.notes, req.due_date
    )
    if rid is None:
        raise HTTPException(status_code=500, detail="Reminders作成に失敗しました")

    logger.info("Reminder作成: list=%s title=%s id=%s", req.list, req.title, rid)
    # 新規Reminderはキャッシュに無いのでフル再取得してSSE配信
    asyncio.create_task(refresh_data())
    return {"id": rid}
