from fastapi import HTTPException, Request, status

from app.config import settings


async def verify_token(request: Request):
    """API認証。api_tokenが空の場合は認証をスキップ（開発モード）。"""
    if not settings.api_token:
        return

    # Authorization: Bearer <token> ヘッダー
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and auth[7:] == settings.api_token:
        return

    # クエリパラメータ（SSE用: EventSourceはヘッダー設定不可）
    token = request.query_params.get("token", "")
    if token == settings.api_token:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証に失敗しました",
    )
