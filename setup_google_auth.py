"""
Google Calendar OAuth2 初回認証セットアップスクリプト

使い方:
  python setup_google_auth.py husband
  python setup_google_auth.py wife

事前に credentials.json を Google Cloud Console からダウンロードして
プロジェクトルートに配置してください。
"""
import sys
from app.services.google_calendar import setup_google_auth

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("husband", "wife"):
        print("使い方: python setup_google_auth.py [husband|wife]")
        sys.exit(1)
    setup_google_auth(sys.argv[1])
