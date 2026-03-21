import logging
import os

from fastapi import APIRouter

from app.config import settings
from app.scheduler import get_last_refresh
from app.sse import sse_manager

logger = logging.getLogger(__name__)

router = APIRouter()

TOKENS_DIR = "tokens"


@router.get("/api/health")
async def health_check():
    # DB接続チェック
    db_ok = False
    try:
        from app.database import get_connection
        db = await get_connection()
        await db.execute("SELECT 1")
        db_ok = True
    except Exception:
        logger.error("ヘルスチェック: DB接続失敗", exc_info=True)

    # Google Calendar トークン存在チェック
    husband_token = os.path.exists(os.path.join(TOKENS_DIR, "husband.json"))
    wife_token = os.path.exists(os.path.join(TOKENS_DIR, "wife.json"))

    # Reminders (AppleScript) チェック — macOS で動作中なら有効
    import sys
    icloud_configured = sys.platform == "darwin"

    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "google_calendar": {
            "husband": husband_token,
            "wife": wife_token,
        },
        "icloud": {
            "configured": icloud_configured,
        },
        "last_refresh": get_last_refresh(),
        "sse_clients": sse_manager.client_count,
    }
