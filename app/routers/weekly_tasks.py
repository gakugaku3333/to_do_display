from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import verify_token
from app.data_assembler import broadcast_current_data
from app.database import (
    create_weekly_task,
    delete_weekly_task,
    get_all_weekly_tasks,
    update_weekly_task,
)

logger = logging.getLogger(__name__)
router = APIRouter()

WEEKDAY_RANGE = set(range(7))  # 0=月 〜 6=日


class WeeklyTaskBody(BaseModel):
    title: str
    weekdays: list[int]  # 0=月, 1=火, 2=水, 3=木, 4=金, 5=土, 6=日


def _validate(body: WeeklyTaskBody) -> None:
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="タイトルは必須です")
    if not body.weekdays:
        raise HTTPException(status_code=400, detail="曜日を1つ以上選択してください")
    if not set(body.weekdays).issubset(WEEKDAY_RANGE):
        raise HTTPException(status_code=400, detail="曜日の値は0〜6で指定してください")


@router.get("/api/weekly-tasks", dependencies=[Depends(verify_token)])
async def list_weekly_tasks():
    """全曜日タスクを返す（管理UI用）"""
    return await get_all_weekly_tasks()


@router.post("/api/weekly-tasks", dependencies=[Depends(verify_token)])
async def create_task(body: WeeklyTaskBody):
    _validate(body)
    task_id = await create_weekly_task(body.title.strip(), body.weekdays)
    await broadcast_current_data()
    logger.info("曜日タスク作成: %s %s", body.title, body.weekdays)
    return {"id": task_id}


@router.put("/api/weekly-tasks/{task_id}", dependencies=[Depends(verify_token)])
async def update_task(task_id: str, body: WeeklyTaskBody):
    _validate(body)
    ok = await update_weekly_task(task_id, body.title.strip(), body.weekdays)
    if not ok:
        raise HTTPException(status_code=404, detail="タスクが見つかりません")
    await broadcast_current_data()
    logger.info("曜日タスク更新: %s", task_id)
    return {"status": "ok"}


@router.delete("/api/weekly-tasks/{task_id}", dependencies=[Depends(verify_token)])
async def delete_task(task_id: str):
    ok = await delete_weekly_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="タスクが見つかりません")
    await broadcast_current_data()
    logger.info("曜日タスク削除: %s", task_id)
    return {"status": "ok"}
