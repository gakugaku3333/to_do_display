# 家族スケジュールダッシュボード

M4 Mac mini 上で動作するFastAPIバックエンドと、ダイニングのAndroidタブレットで表示するWebダッシュボード。

## セットアップ手順

### 1. 依存ライブラリのインストール

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

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

### 4. Apple Reminders の設定

1. iPhoneの「設定」→ Apple ID → 「iCloud」→「リマインダー」をオン
2. [appleid.apple.com](https://appleid.apple.com) にログイン
3. 「アプリ用パスワード」を生成
4. `.env` の `ICLOUD_APP_PASSWORD` に設定
5. Apple Reminders アプリで「ストック」「フロー」リストを作成（名前は `.env` の `STOCK_LIST_NAME` / `FLOW_LIST_NAME` と一致させる）
6. 夫婦間でリストを共有

### 5. サーバー起動

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

タブレットのブラウザから `http://[Mac miniのIPアドレス]:8080` にアクセス。

### 6. Mac mini 自動起動設定

```bash
# setup/com.family.dashboard.plist の WorkingDirectory と ProgramArguments を編集
# YOUR_USERNAME を実際のユーザー名に変更

cp setup/com.family.dashboard.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.family.dashboard.plist
```

## タスクの使い方

| タスク種別 | Reminders リスト | 動作 |
|-----------|----------------|------|
| ストック型 | ストック | 期限付き・未完了なら期日超過後も表示（赤色）|
| フロー型   | フロー   | 当日のみ表示・期日翌日に自動リセット |

## ディレクトリ構成

```
to_do_display/
├── app/              # FastAPI バックエンド
├── static/           # フロントエンド (HTML/CSS/JS)
├── tokens/           # Google OAuth2 トークン (git管理外)
├── setup/            # Mac mini launchd 設定
├── .env              # 認証情報 (git管理外)
└── requirements.txt
```
