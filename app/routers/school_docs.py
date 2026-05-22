from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.auth import verify_token
from app.config import settings
from app.data_assembler import broadcast_current_data
from app.database import get_proposal_by_id, save_proposals, update_proposal_status
from app.services.google_calendar import create_calendar_event

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/heic", "image/webp"}


async def _analyze_and_save(child_name: str, image_bytes: bytes, mime_type: str, filename: str):
    """Gemini解析 → DB保存 → SSE配信（バックグラウンドタスク）"""
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY が設定されていません")
        return

    from app.services.gemini_analysis import analyze_image

    try:
        events = await asyncio.to_thread(
            analyze_image, image_bytes, mime_type, settings.gemini_api_key
        )
    except Exception:
        logger.error("Gemini 解析に失敗しました: %s", filename, exc_info=True)
        return

    if not events:
        logger.info("予定が見つかりませんでした: %s", filename)
        return

    proposals = [
        {
            "id": str(uuid.uuid4()),
            "child_name": child_name,
            "title": ev.get("title", "(タイトルなし)"),
            "event_date": ev.get("date", date.today().isoformat()),
            "time_start": ev.get("time_start"),
            "time_end": ev.get("time_end"),
            "location": ev.get("location"),
            "description": ev.get("description"),
            "image_filename": filename,
        }
        for ev in events
    ]

    await save_proposals(proposals)
    await broadcast_current_data()
    logger.info("%s の配布物から %d 件の提案を保存しました", child_name, len(proposals))


@router.post("/api/school-docs/upload", dependencies=[Depends(verify_token)])
async def upload_school_doc(
    child_name: str = Form(...),
    file: UploadFile = File(...),
):
    if child_name not in settings.children_list:
        raise HTTPException(
            status_code=400,
            detail=f"child_name は {settings.children_list} のいずれかを指定してください",
        )

    mime_type = file.content_type or "image/jpeg"
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="JPEG / PNG / HEIC / WebP のみ対応しています")

    image_bytes = await file.read()
    filename = file.filename or "upload.jpg"

    # Gemini解析はバックグラウンドで実行（レスポンスをブロックしない）
    asyncio.create_task(_analyze_and_save(child_name, image_bytes, mime_type, filename))

    return {"status": "processing", "child_name": child_name, "filename": filename}


@router.post("/api/proposals/{proposal_id}/approve", dependencies=[Depends(verify_token)])
async def approve_proposal(proposal_id: str):
    proposal = await get_proposal_by_id(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="提案が見つかりません")
    if proposal["status"] != "pending":
        raise HTTPException(status_code=400, detail="この提案はすでに処理済みです")

    try:
        event_id = create_calendar_event(
            title=f"[{proposal['child_name']}] {proposal['title']}",
            event_date=proposal["event_date"],
            time_start=proposal.get("time_start"),
            time_end=proposal.get("time_end"),
            location=proposal.get("location"),
            description=proposal.get("description"),
        )
        logger.info("カレンダーイベント作成: %s (%s)", proposal["title"], event_id)
    except Exception:
        logger.error("カレンダーイベント作成に失敗しました", exc_info=True)
        raise HTTPException(status_code=500, detail="カレンダーへの登録に失敗しました")

    await update_proposal_status(proposal_id, "approved")
    await broadcast_current_data()
    return {"status": "ok", "proposal_id": proposal_id}


@router.post("/api/proposals/{proposal_id}/reject", dependencies=[Depends(verify_token)])
async def reject_proposal(proposal_id: str):
    proposal = await get_proposal_by_id(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="提案が見つかりません")
    if proposal["status"] != "pending":
        raise HTTPException(status_code=400, detail="この提案はすでに処理済みです")

    await update_proposal_status(proposal_id, "rejected")
    await broadcast_current_data()
    return {"status": "ok", "proposal_id": proposal_id}
