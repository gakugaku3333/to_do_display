import logging
import sys
from datetime import datetime

from fastapi import APIRouter

from app.config import settings
from app.scheduler import get_last_refresh, get_sync_status
from app.services.google_calendar import get_token_status
from app.sse import sse_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# トークンは約6ヶ月(≒183日)で失効する。余裕を持って早めに警告する。
TOKEN_WARN_AGE_DAYS = 150
# このソースの最終成功から何時間経っても更新が無ければ「止まっている」とみなす。
STALE_SYNC_HOURS = 2


def _sync_is_stale(sync: dict) -> bool:
    # 起動直後などまだ一度も成功していない状態は「止まった」ではなく「これから」なので警告しない
    if sync["success_at"] is None:
        return False
    last = datetime.fromisoformat(sync["success_at"])
    now = datetime.now(last.tzinfo)
    return (now - last).total_seconds() > STALE_SYNC_HOURS * 3600


def _build_warnings(google_calendar_status: dict, sync_status: dict) -> list[str]:
    warnings: list[str] = []

    for account, label in (("husband", "夫"), ("wife", "妻")):
        status = google_calendar_status[account]
        if not status["configured"]:
            continue
        if status["error"] == "invalid_grant":
            warnings.append(f"Googleカレンダー（{label}）の認証が失効しています。再認証が必要です。")
        elif status["error"]:
            warnings.append(f"Googleカレンダー（{label}）のトークン更新でエラーが発生しています。")
        elif status["age_days"] is not None and status["age_days"] >= TOKEN_WARN_AGE_DAYS:
            warnings.append(
                f"Googleカレンダー（{label}）のトークンが発行から{int(status['age_days'])}日経過しています。"
                "まもなく失効する可能性があります。"
            )

    source_labels = {"calendar": "カレンダー", "reminders": "リマインダー", "weather": "天気"}
    for source, sync in sync_status.items():
        if sync["error"] or _sync_is_stale(sync):
            warnings.append(f"{source_labels[source]}の更新が{STALE_SYNC_HOURS}時間以上止まっています。")

    return warnings


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

    google_calendar_status = {
        "husband": get_token_status("husband"),
        "wife": get_token_status("wife"),
    }
    sync_status = get_sync_status()
    warnings = _build_warnings(google_calendar_status, sync_status)

    last = get_last_refresh()

    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "google_calendar": google_calendar_status,
        "icloud": {
            "configured": sys.platform == "darwin",
        },
        "last_refresh": last.isoformat() if last else None,
        "last_sync": sync_status,
        "sse_clients": sse_manager.client_count,
        "warnings": warnings,
    }
