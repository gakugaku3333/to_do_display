#!/bin/bash
# Keychainから iCloud 認証情報を読み込んで起動

export ICLOUD_APPLE_ID=$(security find-generic-password -s "icloud-todo" -a "APPLE_ID" -w 2>/dev/null)
export ICLOUD_APP_PASSWORD=$(security find-generic-password -s "icloud-todo" -a "APP_PASSWORD" -w 2>/dev/null)

if [ -z "$ICLOUD_APPLE_ID" ] || [ -z "$ICLOUD_APP_PASSWORD" ]; then
    echo "Error: Keychainに iCloud 認証情報が見つかりません"
    echo "以下のコマンドで登録してください:"
    echo '  security add-generic-password -s "icloud-todo" -a "APPLE_ID" -w "your@icloud.com"'
    echo '  security add-generic-password -s "icloud-todo" -a "APP_PASSWORD" -w "xxxx-xxxx-xxxx-xxxx"'
    exit 1
fi

source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8080 "$@"
