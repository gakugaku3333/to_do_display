#!/bin/bash
# Mac mini でのデプロイ手順をコード化したスクリプト。
# 口伝だった「pull → pytest → launchctl kickstart -k → 動作確認」を1本化する。
#
# 使い方:
#   ./scripts/deploy.sh                 # 通常デプロイ
#   ./scripts/deploy.sh --clear-weather # 天気の表示書式変更時など、当日分weather_cacheも削除
#
# 前提: com.family.dashboard が launchd に登録済み（HANDOVER.md 5章参照）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

CLEAR_WEATHER=false
for arg in "$@"; do
  case "$arg" in
    --clear-weather) CLEAR_WEATHER=true ;;
    *) echo "不明なオプション: $arg" >&2; exit 1 ;;
  esac
done

PORT="${PORT:-8080}"
HEALTH_URL="http://localhost:${PORT}/api/health"

echo "==> 1. git pull"
git pull

echo "==> 2. 依存ライブラリの更新確認"
if ! git diff --quiet HEAD@{1} HEAD -- requirements.txt 2>/dev/null; then
  echo "    requirements.txt に変更があったため pip install を実行します"
  source .venv/bin/activate
  pip install -r requirements.txt
else
  echo "    requirements.txt に変更なし。スキップ"
fi

echo "==> 3. pytest 実行"
source .venv/bin/activate
if ! python -m pytest tests/ -q; then
  echo "!! テストが赤のためデプロイを中断しました。launchd の再起動は行っていません。" >&2
  exit 1
fi

if [ "$CLEAR_WEATHER" = true ]; then
  echo "==> 3.5 当日分の weather_cache を削除（--clear-weather）"
  today="$(date +%Y-%m-%d)"
  sqlite3 dashboard.db "DELETE FROM weather_cache WHERE date = '${today}';"
fi

echo "==> 4. launchd 再起動"
launchctl kickstart -k "gui/$(id -u)/com.family.dashboard"

echo "==> 5. 起動確認 (最大30秒待機)"
for i in $(seq 1 15); do
  sleep 2
  if response="$(curl -sf "$HEALTH_URL")"; then
    echo "    起動確認OK: $response"
    exit 0
  fi
done

echo "!! ${HEALTH_URL} が30秒待っても応答しません。logs/dashboard.log を確認してください。" >&2
exit 1
