from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import verify_token
from app.data_assembler import get_current_data
from app.database import mark_complete, mark_incomplete
from app.sse import sse_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class CompleteRequest(BaseModel):
    task_type: str  # "stock" or "flow"
    due_date: str | None = None


@router.post("/api/tasks/{task_id}/complete", dependencies=[Depends(verify_token)])
async def complete_task(task_id: str, body: CompleteRequest):
    if body.task_type not in ("stock", "flow"):
        raise HTTPException(status_code=400, detail="task_type は 'stock' または 'flow' を指定してください")
    await mark_complete(task_id, body.task_type, body.due_date)

    # SSEブロードキャスト
    data = await get_current_data()
    if data:
        await sse_manager.broadcast(data.model_dump_json())

    return {"status": "ok", "task_id": task_id}


@router.post("/api/tasks/{task_id}/uncomplete", dependencies=[Depends(verify_token)])
async def uncomplete_task(task_id: str):
    await mark_incomplete(task_id)

    # SSEブロードキャスト
    data = await get_current_data()
    if data:
        await sse_manager.broadcast(data.model_dump_json())

    return {"status": "ok", "task_id": task_id}
