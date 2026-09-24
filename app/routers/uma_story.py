from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter()

# 競走馬物語プロジェクト側の承認ステータス置き場（読み取り専用連携。keibaAI-v3は一切触らない）
APPROVALS_DIR = Path.home() / "Projects" / "keiba-projects" / "競走馬物語" / "data" / "approvals"


class UmaStoryDecisionRequest(BaseModel):
    race_id: str
    action: str  # "approve" または "reject"


@router.post("/api/uma-story/decision", dependencies=[Depends(verify_token)])
async def uma_story_decision(req: UmaStoryDecisionRequest):
    APPROVALS_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "race_id": req.race_id,
        "action": req.action,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }
    path = APPROVALS_DIR / f"{req.race_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("競走馬物語 承認判定: race_id=%s action=%s", req.race_id, req.action)
    return {"status": "ok", **record}
