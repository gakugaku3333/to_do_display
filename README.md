# 家族スケジュールダッシュボード

M4 Mac mini 上で動作するFastAPIバックエンドと、ダイニングのAndroidタブレットで表示するWebダッシュボード。

## 主な機能

- 夫・妻・ファミリー共有カレンダーのイベント取得（色分け: 夫=青・妻=ピンク・ファミリー=緑）
- Apple Reminders から「ストック型」「フロー型」タスクを表示・タップ完了（Reminders.appに書き戻し）
- 曜日ごとの繰り返しタスク（ダッシュボード独自管理）
- **ゴミ出しの日表示**（曜日タスクを「ゴミ出し」指定すると、チェック不要の日付ヘッダーバッジとして表示。朝のブリーフィングにも読み上げ）
- 久留米市の天気予報（気象庁API・毎朝6:15更新）
- **日本の祝日・土曜日の色分け表示**（祝日名バッジ表示、jpholiday使用）
- 学校配布物スキャン → Gemini解析 → カレンダー自動登録
- **朝の音声ブリーフィング**（`/api/briefing` が日付・天気・予定・やる事の読み上げ用テキストを返す。iPhoneのショートカット個人用オートメーションで毎朝7時に読み上げ）
- SSEリアルタイム更新、5分ごと自動同期
- PWA対応（フルスクリーン・オフラインキャッシュ）
- **セルフ診断**（`/api/health`）: Google認証の失効・失効間近、各データソースの同期停止を検知し、画面上部に警告バナー表示
- `dashboard.db` の日次自動バックアップ（7世代ローテーション）
- `scripts/deploy.sh` によるデプロイ自動化（pytest通過確認 → launchd再起動 → 起動確認）

## セットアップ手順

### 1. 依存ライブラリのインストール

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

git のコミット前テスト実行フックを有効化（クローンごとに一度だけ）:

```bash
git config core.hooksPath .githooks
```

`.githooks/pre-commit` がコミット前に `pytest` を実行し、テストが赤いコミットを防ぎます。

### 2. 環境変数の設定

```bash
cp .env.example .env
# .env を編集して認証情報を入力
```

### 3. Google Calendar OAuth2 認証

1. [Google Cloud Console](https://console.cloud.google.com/) で新しいプロジェクトを作成
2. Google Calendar API を有効化
3. OAuth 2.0 クライアント ID を作成（デスクトップアプリ）
4. `credentials.json` をダウンロードしてプロジェクトルートに配置
5. 夫・妻それぞれのアカウントで認証を実行:

```bash
python setup_google_auth.py husband
python setup_google_auth.py wife
```

ブラウザが開いてGoogleアカウントへのログインが求められます。  
**注意:** トークンは約6ヶ月で失効します（`feedback_google_oauth_expiry.md` 参照）。

### 4. Apple Reminders の設定

1. iPhoneのリマインダーアプリで「ストック」「フロー」リストを作成（名前は `.env` の `STOCK_LIST_NAME` / `FLOW_LIST_NAME` と一致させる）
2. Mac mini 上で Reminders.app が iCloud と同期していることを確認
3. 夫婦間でリストを共有
4. 追加の認証設定は不要（macOS の AppleScript 経由でアクセス）

### 5. サーバー起動

```bash
# 手動起動
./start.sh

# または直接
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

タブレットのブラウザから `http://[Mac miniのIPアドレス]:8080` にアクセス。

### 6. Mac mini 自動起動設定（launchd）

```bash
cp setup/com.family.dashboard.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.family.dashboard.plist
```

### 7. コード更新時のデプロイ

手動手順ではなく `scripts/deploy.sh` を使う（pull → pytest → launchd再起動 → 起動確認を自動化）。

```bash
./scripts/deploy.sh
```

## タスクの使い方

| タスク種別 | Reminders リスト | 動作 |
|-----------|----------------|------|
| ストック型 | ストック | 期限付き・未完了なら期日超過後も表示（赤色）|
| フロー型   | フロー   | 当日のみ表示・期日翌日に自動リセット |
| 曜日タスク | ダッシュボードDB | 指定曜日にフローへ合流表示 |

## ディレクトリ構成

```
to_do_display/
├── app/
│   ├── routers/          # APIエンドポイント（dashboard/tasks/weekly_tasks等）
│   ├── services/         # 外部サービス連携（google_calendar/icloud_reminders/weather/gemini）
│   ├── models.py         # Pydanticモデル（TodayData等）
│   ├── scheduler.py      # APScheduler（5分データ更新・6:15天気更新・3:00DBバックアップ）
│   └── data_assembler.py # キャッシュ＋DB完了状態マージ
├── static/               # フロントエンド (HTML/CSS/JS/SW)
├── scripts/              # AppleScriptファイル・deploy.sh
├── setup/                # Mac mini launchd設定ファイル
├── tokens/               # Google OAuth2トークン（git管理外）
├── backups/              # dashboard.db 日次バックアップ（git管理外・7世代）
├── samples/              # 学校配布物スキャン機能のテスト用サンプル画像（git管理外）
├── .env                  # 認証情報（git管理外）
├── .env.example          # 環境変数テンプレート
├── setup_google_auth.py  # Google OAuth2初回認証スクリプト
├── start.sh              # サーバー起動スクリプト
└── requirements.txt
```

## 詳細ドキュメント

詳しい設計・トラブルシューティングは `HANDOVER.md` を参照。
