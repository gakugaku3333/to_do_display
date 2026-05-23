# 家族スケジュールダッシュボード — 引き継ぎ資料

## 1. プロジェクト概要

家族（夫・妻）の **Googleカレンダー予定** と **Apple リマインダー（iCloud）** を1画面に集約表示するWebダッシュボード。Mac mini で常時起動し、ダイニングに置いたAndroidタブレットから閲覧する想定。

### 主な機能

- 夫婦のGoogleカレンダー予定を色分け表示（夫: 青、妻: ピンク）
- iCloudリマインダーを「ストック（期限ベース）」「フロー（当日のみ）」の2カテゴリで表示
- **タスクのタップ完了**（フェードアウトでリストから消え、Reminders.appにも同期）
- **久留米市の天気予報**（毎朝6:15取得、天気概況・最高最低気温・時間別降水確率）
- **SSE（Server-Sent Events）によるリアルタイム更新**
- **トークンベースのAPI認証**
- **PWA対応**（フルスクリーン、オフラインキャッシュ）
- **ヘルスチェックエンドポイント** (`/api/health`)
- 5分ごとの自動データ更新、画面のスリープ防止（Wake Lock）

---

## 2. アーキテクチャ

```
Android タブレット (ブラウザ / PWA)
        │  HTTP (port 8080)
        │
        ├── SSE: GET /api/stream    → リアルタイムデータ配信（初回データも即送信）
        ├── REST: POST /api/tasks/{id}/complete|uncomplete
        ├── REST: GET /api/health   → ヘルスチェック（認証不要）
        ▼
Mac mini (FastAPI + uvicorn)
        │
        ├── SSEManager              → 接続中クライアントへブロードキャスト
        ├── APScheduler             → 5分ごとにデータ取得 / 毎朝6:15に天気取得
        ├── Google Calendar API     → OAuth2（夫・妻各アカウント）
        ├── Apple Reminders         → AppleScript (osascript) 経由
        ├── Open-Meteo API          → 久留米市の天気予報（APIキー不要）
        └── SQLite (dashboard.db)   → タスク完了状態の永続化（WALモード）
```

### データフロー

1. **APScheduler** が5分ごとに Google Calendar / iCloud からデータ取得 → メモリキャッシュに保存
2. **毎朝6:15 JST** に Open-Meteo から天気を取得 → `_cached_weather` に保存（起動時も即取得）
3. データ更新完了時に **SSE** で全接続クライアントにプッシュ配信
4. タスク完了操作は即座に SQLite に書き込み → SSEで全クライアントに反映（完了タスクはリストから除外）
5. Reminders.app への完了書き戻しは非同期（AppleScript）
6. フロータスクの完了状態は日付変更時に自動リセット
7. フロントエンドはSSE接続のみ（初回データもSSE経由で即配信）

---

## 3. ディレクトリ構成

```
to_do_display/
├── app/
│   ├── main.py                  # FastAPI エントリポイント（lifespan管理）
│   ├── config.py                # pydantic-settings による設定読み込み
│   ├── models.py                # データモデル（CalendarEvent, Task, TodayData）
│   ├── database.py              # SQLite操作（接続一元管理、WALモード）
│   ├── scheduler.py             # APScheduler（5分間隔 + 毎朝6:15天気更新）
│   ├── sse.py                   # SSEManager（クライアント接続管理、ブロードキャスト）
│   ├── data_assembler.py        # キャッシュ + 完了状態フィルタリングの共通ロジック
│   ├── auth.py                  # トークン認証（Bearer / query param）
│   ├── logging_config.py        # ロギング設定（RotatingFileHandler）
│   ├── routers/
│   │   ├── dashboard.py         # GET /api/today, GET /api/stream (SSE)
│   │   ├── tasks.py             # POST /api/tasks/*/complete|uncomplete
│   │   └── health.py            # GET /api/health
│   └── services/
│       ├── google_calendar.py   # Google Calendar API クライアント
│       ├── icloud_reminders.py  # Apple Reminders (AppleScript経由)
│       └── weather.py           # Open-Meteo 天気予報（APIキー不要）
├── static/
│   ├── index.html               # メイン画面（PWA対応）
│   ├── style.css                # ダークテーマCSS
│   ├── app.js                   # SSEクライアント、認証、エラーUI
│   ├── manifest.json            # PWAマニフェスト
│   └── sw.js                    # Service Worker（オフラインキャッシュ）
├── tests/
│   ├── conftest.py              # テスト基盤（モック、フィクスチャ）
│   ├── test_auth.py             # 認証テスト
│   ├── test_dashboard.py        # ダッシュボードAPIテスト
│   ├── test_tasks.py            # タスク操作テスト
│   ├── test_database.py         # DB操作テスト
│   ├── test_health.py           # ヘルスチェックテスト
│   └── test_sse.py              # SSEテスト
├── scripts/
│   ├── fetch_reminders.applescript    # Reminders取得（バッチ一括取得で高速化）
│   ├── complete_reminder.applescript  # タスク完了状態の書き戻し
│   └── create_reminder.applescript    # 新規リマインダー作成
├── setup/
│   └── com.family.dashboard.plist  # macOS 自動起動設定
├── tokens/                      # Google OAuth トークン（git管理外）
├── logs/                        # ログファイル（git管理外、自動生成）
├── credentials.json             # Google OAuth クライアント情報（git管理外）
├── .env                         # 環境変数（git管理外）
├── .env.example                 # .env のテンプレート
├── start.sh                     # Keychain連携の起動スクリプト
├── setup_google_auth.py         # Google OAuth 初回認証スクリプト
├── requirements.txt             # Python依存パッケージ（本番）
├── requirements-dev.txt         # テスト用依存パッケージ
└── dashboard.db                 # SQLite DB（git管理外、自動生成）
```

---

## 4. セットアップ手順

### 4.1 基本環境

```bash
git clone https://github.com/gakugaku3333/to_do_display.git
cd to_do_display

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 4.2 Google Calendar 認証

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成
2. 「APIとサービス」→「ライブラリ」→ **Google Calendar API** を有効化
3. 「OAuth 同意画面」→ 外部 → アプリ名等を入力 → テストユーザーに夫婦のGmailを追加
4. 「認証情報」→「OAuth クライアント ID」→ **デスクトップアプリ** で作成
5. JSONダウンロード → `credentials.json` としてプロジェクトルートに配置
6. 初回認証（ブラウザが開く）:

```bash
python setup_google_auth.py husband
python setup_google_auth.py wife
```

`tokens/husband.json`, `tokens/wife.json` が生成されれば成功。

### 4.3 Apple リマインダー設定

iCloud CalDAV は iOS 13+ で非対応のため、**macOS ネイティブの AppleScript** 経由でアクセスします。

1. iPhoneのリマインダーアプリで「**ストック**」「**フロー**」リストを作成（カタカナ表記）
2. Mac mini 上で Reminders.app が iCloud と同期していることを確認
3. 追加の認証設定は不要（osascript が macOS の EventKit 経由でアクセス）

> **注意:**
> - 初回起動時や Reminders.app が長時間停止していた場合、iCloud 同期に1〜5分かかります
> - Mac mini で常時運用する場合、Reminders.app は常駐するため問題ありません

### 4.4 API認証の設定（任意）

`.env` に `API_TOKEN` を設定すると全APIエンドポイントが認証必須になります。

```bash
# .env
API_TOKEN=your_secret_token_here
```

空のままにすると認証は無効です（開発モード）。

### 4.5 起動

```bash
# 開発時
./start.sh --reload

# 本番
./start.sh
```

ブラウザで `http://localhost:8080` を開いて確認。

---

## 5. Mac mini 本番運用（自動起動）

### launchd 設定

```bash
# plist を編集（YOUR_USERNAME とパスを実環境に合わせる）
vi setup/com.family.dashboard.plist

# 配置 & 有効化
cp setup/com.family.dashboard.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.family.dashboard.plist
```

### plist 編集が必要な箇所

| 項目 | 変更内容 |
|------|----------|
| `ProgramArguments[0]` | `.venv/bin/uvicorn` の絶対パスに変更 |
| `WorkingDirectory` | 実際のプロジェクトパスに変更 |
| `PATH` | `.venv/bin` を含めるよう変更 |

### 運用コマンド

```bash
# 状態確認
launchctl list | grep family

# 停止
launchctl unload ~/Library/LaunchAgents/com.family.dashboard.plist

# 再起動
launchctl unload ~/Library/LaunchAgents/com.family.dashboard.plist
launchctl load ~/Library/LaunchAgents/com.family.dashboard.plist

# ログ確認（アプリケーションログ）
tail -f logs/dashboard.log

# ログ確認（システムログ）
tail -f /var/log/family-dashboard.log
tail -f /var/log/family-dashboard.error.log
```

---

## 6. 認証情報の管理

### git管理外のファイル一覧（.gitignore）

| ファイル | 内容 | 再取得方法 |
|----------|------|-----------|
| `.env` | 環境変数 | `.env.example` からコピーして編集 |
| `credentials.json` | Google OAuthクライアント情報 | Google Cloud Console から再ダウンロード |
| `tokens/*.json` | Google OAuthアクセストークン | `setup_google_auth.py` を再実行 |
| `dashboard.db` | タスク完了状態DB | 自動生成（データは失われる） |
| `logs/` | アプリケーションログ | 自動生成 |

### Keychain に保存される情報

> CalDAV 方式から AppleScript 方式に移行したため、Keychain への iCloud 認証情報の登録は不要になりました。
> 既に登録済みの場合もそのまま残して問題ありません（使用されません）。

---

## 7. 技術的な補足

### DB スキーマ（SQLite: dashboard.db）

```sql
CREATE TABLE IF NOT EXISTS task_completions (
    task_id    TEXT PRIMARY KEY,
    task_type  TEXT NOT NULL,   -- "stock" | "flow"
    completed_at TEXT,          -- ISO 8601
    due_date   TEXT             -- YYYY-MM-DD
);
```

- WALモード有効（読み書き並行性向上）
- 接続は一元管理（`get_connection()` で遅延初期化）
- **ストックタスク**: 完了状態は永続（明示的に取消すまで残る）
- **フロータスク**: 日付変更時に `cleanup_old_flow_completions()` で自動削除

### SSE (Server-Sent Events)

- `GET /api/stream` でクライアントが接続
- 接続時に現在データを即送信、以降はデータ変更時にプッシュ
- 30秒ごとにkeepaliveコメント送信（プロキシタイムアウト防止）
- クライアントのキュー満杯時（maxsize=10）は自動切断
- EventSourceはブラウザ側で自動再接続

### API認証

- `API_TOKEN` が空の場合、認証は完全に無効（開発モード）
- 設定時: `Authorization: Bearer <token>` ヘッダーまたは `?token=<token>` クエリパラメータ
- SSEはクエリパラメータ認証（EventSourceはヘッダー設定不可のため）
- `/api/health` は認証不要（監視用）

### PWA

- `manifest.json` でフルスクリーン表示
- Service Worker (`sw.js`) によるオフライン対応とキャッシュ管理
- オフライン時は最後に取得したデータを表示

#### Service Worker キャッシュ戦略

| リソース | 戦略 | 理由 |
|---------|------|------|
| `/`（ナビゲーション） | **network-first** | HTML/トークン変更を即反映 |
| `/static/app.js` | **network-first** | JS 修正を即反映（cache-first だと更新が伝わらない） |
| `/static/*.css`, manifest 等 | stale-while-revalidate | 表示を犠牲にせず裏で更新 |
| `/api/*` | network-first | 常に最新データ |
| `/api/stream` (SSE) | SW を通さない | ストリームを途切れさせない |

**重要**: `sw.js` と `index.html` は FastAPI の専用ルートで `Cache-Control: no-cache` で配信。
これによりブラウザが必ず再検証し、SW の更新を確実に検知する。

新しい SW がデプロイされると、既存タブで `controllerchange` イベントが発火し自動リロードされる。

---

## 8. テスト

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

21テスト: 認証(5), ダッシュボード(3), タスク操作(4), DB(3), ヘルスチェック(2), SSE(4)

---

## 9. トラブルシューティング

| 症状 | 原因と対処 |
|------|-----------|
| 予定が急に表示されなくなった | Google OAuth トークン期限切れ（約6ヶ月）。`logs/dashboard.log` で `invalid_grant` 確認。`python setup_google_auth.py husband` で再認証 |
| 天気が表示されない / 古い | `python3 -c "from app.services.weather import fetch_weather; print(fetch_weather())"` で単体確認。ネットワーク問題ならサーバー再起動で再取得 |
| 完了済みタスクがリストに残る | `data_assembler.py` が `filter out` でなく `mark only` になっていないか確認 |
| リマインダーが表示されない | 起動後1〜5分待つ（iCloud同期中）。`logs/dashboard.log` で "Reminders 取得完了" を確認 |
| リマインダーがタイムアウトし続ける | Reminders.app が固まっている。`killall Reminders && open -a Reminders` で再起動 |
| コード修正しても画面が変わらない | Service Worker キャッシュ。**2回リロード**（1回目:新SW起動、2回目:新JS反映）。確実には Safari > 開発 > キャッシュを空にする |
| flow-title が「本日の曜日タスク」のまま | JS が途中でクラッシュしているサイン。`updateDateDisplay` の innerHTML 問題が再発していないか確認 |
| Google認証でブラウザが開かない | `credentials.json` が配置されているか確認 |
| タスク完了が反映されない | `dashboard.db` の権限確認。削除すれば再生成される |
| Mac再起動後にサービスが起動しない | `launchctl list \| grep family` で確認 |
| タブレットからアクセスできない | Mac mini のIPアドレス確認 + ファイアウォールでport 8080を許可 |
| SSEが接続できない | ステータスバナーに「接続が切れました」表示 → サーバー再起動を確認 |
| 401エラー | `.env` の `API_TOKEN` を確認。空にすると認証無効 |
| ヘルスチェックでdegraded | `curl /api/health` でどのサービスが失敗しているか確認 |

---

## 10. 主要ライブラリ

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| FastAPI | 0.115.0 | Webフレームワーク |
| uvicorn | 0.30.6 | ASGIサーバー |
| pydantic-settings | 2.4.0 | 設定管理（.env読み込み） |
| aiosqlite | 0.20.0 | 非同期SQLite |
| APScheduler | 3.10.4 | 定期実行スケジューラ |
| google-api-python-client | 2.145.0 | Google Calendar API |
| google-auth-oauthlib | 1.2.1 | Google OAuth2 認証 |
| (osascript) | macOS標準 | Apple Reminders アクセス（AppleScript） |
| pytest | 8.3.3 | テストフレームワーク（dev） |
| httpx | 0.27.2 | テスト用HTTPクライアント（dev） |
