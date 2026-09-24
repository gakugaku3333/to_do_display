import asyncio
import logging
import os
import sys

from fastapi import APIRouter

from app.scheduler import get_last_refresh
from app.services.google_calendar import TOKENS_DIR, get_credentials
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

    # トークンの「有無」ではなく実際に使えるか（refresh 可能か）まで確認する。
    # トークンがあるのに valid でなければ失効＝要再認証。
    calendar_status = {}
    for account in ("husband", "wife"):
        if not os.path.exists(os.path.join(TOKENS_DIR, f"{account}.json")):
            calendar_status[account] = {"token": False, "valid": False, "state": "missing"}
            continue
        try:
            creds = await asyncio.to_thread(get_credentials, account)
        except Exception:
            logger.error("ヘルスチェック: %s の認証確認に失敗", account, exc_info=True)
            creds = None
        calendar_status[account] = {
            "token": True,
            "valid": creds is not None,
            "state": "ok" if creds else "expired",
        }

    needs_reauth = [a for a, s in calendar_status.items() if s["state"] == "expired"]

    last = get_last_refresh()

    return {
        "status": "ok" if (db_ok and not needs_reauth) else "degraded",
        "db": db_ok,
        "google_calendar": {
            # 後方互換: husband / wife は「認証が有効か」を表す真偽値
            "husband": calendar_status["husband"]["valid"],
            "wife": calendar_status["wife"]["valid"],
            "detail": calendar_status,
            "needs_reauth": needs_reauth,
        },
        "icloud": {
            "configured": sys.platform == "darwin",
        },
        "last_refresh": last.isoformat() if last else None,
        "sse_clients": sse_manager.client_count,
    }
