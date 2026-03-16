from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import mark_complete, mark_incomplete

router = APIRouter()


class CompleteRequest(BaseModel):
    task_type: str  # "stock" or "flow"
    due_date: str | None = None


@router.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str, body: CompleteRequest):
    if body.task_type not in ("stock", "flow"):
        raise HTTPException(status_code=400, detail="task_type は 'stock' または 'flow' を指定してください")
    await mark_complete(task_id, body.task_type, body.due_date)
    return {"status": "ok", "task_id": task_id}


@router.post("/api/tasks/{task_id}/uncomplete")
async def uncomplete_task(task_id: str):
    await mark_incomplete(task_id)
    return {"status": "ok", "task_id": task_id}
