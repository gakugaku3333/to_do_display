import logging
import os
import sys

from fastapi import APIRouter

from app.scheduler import get_last_refresh
from app.services.google_calendar import TOKENS_DIR
from app.sse import sse_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/health")
async def health_check():
    db_ok = False
    try:
        from app.database import get_connection
        db = await get_connection()
        await db.execute("SELECT 1")
        db_ok = True
    except Exception:
        logger.error("ヘルスチェック: DB接続失敗", exc_info=True)

    husband_token = os.path.exists(os.path.join(TOKENS_DIR, "husband.json"))
    wife_token = os.path.exists(os.path.join(TOKENS_DIR, "wife.json"))

    last = get_last_refresh()

    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "google_calendar": {
            "husband": husband_token,
            "wife": wife_token,
        },
        "icloud": {
            "configured": sys.platform == "darwin",
        },
        "last_refresh": last.isoformat() if last else None,
        "sse_clients": sse_manager.client_count,
    }
