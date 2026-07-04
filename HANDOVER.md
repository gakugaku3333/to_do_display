# 家族スケジュールダッシュボード — 引き継ぎ資料

最終更新: 2026-05-25

## 1. プロジェクト概要

家族（夫・妻）の **Googleカレンダー予定** と **Apple リマインダー（iCloud）** を1画面に集約表示するWebダッシュボード。Mac mini で常時起動し、ダイニングに置いたAndroidタブレットから閲覧する想定。

### 主な機能

- 夫婦のGoogleカレンダー予定を色分け表示（夫: 青、妻: ピンク、ファミリー: 緑）
- iCloudリマインダーを「ストック（期限ベース）」「フロー（当日のみ）」の2カテゴリで表示
- **ダッシュボード専用の曜日タスク**（曜日指定の繰り返しタスク、フローに合流表示）
- **ゴミ出しの日表示**（曜日タスクの `category="trash"` 指定。フローには合流させず、日付ヘッダーに
  🗑️バッジ表示 + 朝のブリーフィングで読み上げ）
- **イベントカウントダウン**（Googleカレンダーのタイトルに「★」を付けると「あと◯日」を
  ヘッダー直下に大きく表示。設定UIは無く命名規約で実現。例: `★運動会`）
- **曜日タスク完了演出**（紙吹雪 + 効果音。効果音は🔊ボタンでON/OFF、localStorageに保存）
- **曜日タスクの完了率を★で表示**（「今日のやる事リスト」ヘッダーに `weekly_completed/weekly_total` を反映。
  ゴミ出し(category="trash")は完了率の対象外）
- **タスクのタップ完了**（フェードアウトでリストから消え、Reminders.appにも同期）
- **久留米市の天気予報**（毎朝6:15取得、気象庁API）
- **祝日・土曜日の日付カラー表示**（祝日/日曜→赤、土曜→青）
- **学校配布物スキャン → Gemini解析 → カレンダー自動登録**
- **SSE（Server-Sent Events）によるリアルタイム更新**
- **トークンベースのAPI認証**
- **PWA対応**（フルスクリーン、オフラインキャッシュ）
- 5分ごとの自動データ更新、画面のスリープ防止（Wake Lock）

---

## 2. アーキテクチャ

```
Android タブレット (ブラウザ / PWA)
        │  HTTP (port 8080)
        │
        ├── SSE:  GET  /api/stream              → リアルタイムデータ配信
        ├── REST: GET  /api/briefing            → 朝の音声ブリーフィング読み上げテキスト（平文）
        ├── REST: POST /api/tasks/complete       → タスク完了（IDはボディで送る）
        ├── REST: POST /api/tasks/uncomplete     → 完了取消
        ├── REST: GET  /api/weekly-tasks         → 曜日タスク一覧
        ├── REST: POST /api/weekly-tasks         → 曜日タスク作成
        ├── REST: PUT  /api/weekly-tasks/{id}    → 曜日タスク更新
        ├── REST: DELETE /api/weekly-tasks/{id}  → 曜日タスク削除
        ├── REST: POST /api/school-docs/scan     → 学校配布物スキャン
        └── REST: GET  /api/health              → ヘルスチェック（認証不要）
        ▼
Mac mini (FastAPI + uvicorn)
        │
        ├── SSEManager              → 接続中クライアントへブロードキャスト
        ├── APScheduler             → 5分ごとにデータ取得 / 毎朝6:15に天気取得
        ├── Google Calendar API     → OAuth2（夫・妻各アカウント + ファミリーカレンダー）
        ├── Apple Reminders         → AppleScript (osascript) 経由
        ├── 気象庁 API              → 久留米市の天気予報（APIキー不要）
        ├── Gemini API              → 学校配布物画像の解析
        └── SQLite (dashboard.db)  → タスク完了状態・曜日タスク・配布物提案の永続化
```

### データフロー

1. **APScheduler** が5分ごとに Google Calendar / iCloud からデータ取得 → メモリキャッシュに保存
2. **毎朝6:15 JST** に気象庁から天気を取得 → `_cached_weather` に保存（起動時も即取得）
3. データ更新完了時に **SSE** で全接続クライアントにプッシュ配信
4. タスク完了操作 → SQLite に即記録 → SSEで全クライアントに反映（完了タスクはリストから除外）
5. Reminders.app への完了書き戻しは非同期（AppleScript、対象リストを指定して高速化）
6. フロータスクの完了状態は日付変更時に自動リセット
7. 曜日タスクはその曜日に一致する日だけフローに合流して表示

---

## 3. ディレクトリ構成

```
to_do_display/
├── app/
│   ├── main.py                  # FastAPI エントリポイント（lifespan管理）
│   ├── config.py                # pydantic-settings による設定読み込み
│   ├── models.py                # データモデル（CalendarEvent, Task, TodayData等）
│   ├── database.py              # SQLite操作（接続一元管理、WALモード）
│   ├── scheduler.py             # APScheduler（5分間隔 + 毎朝6:15天気更新）
│   ├── sse.py                   # SSEManager（クライアント接続管理、ブロードキャスト）
│   ├── data_assembler.py        # キャッシュ + 完了状態フィルタリングの共通ロジック
│   ├── auth.py                  # トークン認証（Bearer / query param）
│   ├── logging_config.py        # ロギング設定（RotatingFileHandler）
│   ├── routers/
│   │   ├── dashboard.py         # GET /api/stream (SSE)
│   │   ├── tasks.py             # POST /api/tasks/complete|uncomplete
│   │   ├── weekly_tasks.py      # CRUD /api/weekly-tasks
│   │   ├── school_docs.py       # POST /api/school-docs/scan
│   │   ├── reminders.py         # POST /api/reminders（外部からリマインダー作成）
│   │   └── health.py            # GET /api/health
│   └── services/
│       ├── google_calendar.py   # Google Calendar API クライアント
│       ├── icloud_reminders.py  # Apple Reminders (AppleScript経由)
│       └── weather.py           # 気象庁API 天気予報
├── static/
│   ├── index.html               # メイン画面（PWA対応）
│   ├── style.css                # ダークテーマCSS（祝日カラー含む）
│   ├── js/                      # ESモジュール一式（Phase 1 で app.js から分割）
│   │   ├── main.js              # エントリポイント。SSE接続・WakeLock・初期化
│   │   ├── state.js             # 単一の状態オブジェクト + subscribe/setState
│   │   ├── api.js               # fetchラッパー（authHeaders集約、エラーは必ずstatusBannerへ）
│   │   ├── utils.js             # escapeHtml・日付整形など
│   │   └── components/          # clock/dateHeader/weather/events/tasks/proposals/
│   │                            # weeklyTasks/weekModal/statusBanner/healthBanner/countdown/
│   │                            # weeklyProgress/celebrate
│   ├── manifest.json            # PWAマニフェスト
│   └── sw.js                    # Service Worker（オフラインキャッシュ）
├── tests/                       # pytest テストスイート
├── scripts/
│   ├── fetch_reminders.applescript    # Reminders取得（バッチ一括取得で高速化）
│   ├── complete_reminder.applescript  # タスク完了状態の書き戻し（対象リスト指定）
│   └── create_reminder.applescript    # 新規リマインダー作成
├── setup/
│   └── com.family.dashboard.plist  # macOS 自動起動設定（launchd）
├── tokens/                      # Google OAuth トークン（git管理外）
├── logs/                        # ログファイル（git管理外、自動生成）
├── credentials.json             # Google OAuth クライアント情報（git管理外）
├── .env                         # 環境変数（git管理外）
├── .env.example                 # .env のテンプレート
├── start.sh                     # 起動スクリプト（venv activate + uvicorn）
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

> **注意:** トークンは約6ヶ月で失効。症状は「予定が急に消える」。`logs/dashboard.log` で `invalid_grant` を確認して再実行。
> `/api/health` がトークンの残り健全性を自己診断しており（失効・期限接近を検知）、
> 失効時はダッシュボード画面上部に警告バナーが常時表示され、朝のブリーフィングにも再認証を促す文言が入る。

#### ファミリーカレンダー

`app/services/google_calendar.py` の `FAMILY_CALENDAR_ID` に共有カレンダーのIDを設定。
夫アカウントの calendarList に含まれていない場合でも自動で取得される。

### 4.3 Apple リマインダー設定

iCloud CalDAV は iOS 13+ で非対応のため、**macOS ネイティブの AppleScript** 経由でアクセスします。

1. iPhoneのリマインダーアプリで「**ストック**」「**フロー**」リストを作成（カタカナ表記）
2. Mac mini 上で Reminders.app が iCloud と同期していることを確認
3. 追加の認証設定は不要（osascript が macOS の EventKit 経由でアクセス）

> **注意:**
> - 初回起動時や Reminders.app が長時間停止していた場合、iCloud 同期に1〜5分かかります
> - リスト名は必ず**カタカナ**で「ストック」「フロー」（`.env` の `STOCK_LIST_NAME`, `FLOW_LIST_NAME`）

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

# 本番（通常は launchd が管理するため手動不要）
./start.sh
```

ブラウザで `http://localhost:8080` を開いて確認。

---

## 5. Mac mini 本番運用（自動起動）

### launchd 管理（推奨）

本番環境では launchd の `com.family.dashboard` が KeepAlive でプロセスを管理しています。
**手動で kill すると自動再起動**されるため、コード更新時は `launchctl kickstart -k` を使います。

```bash
# 再起動（コード更新反映）
launchctl kickstart -k gui/$(id -u)/com.family.dashboard

# 状態確認
launchctl list | grep family

# ログ確認
tail -f logs/dashboard.log
```

### plist 配置（新規セットアップ時）

```bash
cp setup/com.family.dashboard.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.family.dashboard.plist
```

### plist 編集が必要な箇所

| 項目 | 変更内容 |
|------|----------|
| `ProgramArguments[0]` | `.venv/bin/uvicorn` の絶対パスに変更 |
| `WorkingDirectory` | 実際のプロジェクトパスに変更 |

### デプロイスクリプト（`scripts/deploy.sh`）

コード更新の口伝手順（pull → pytest → launchd再起動 → 起動確認）をスクリプト化したもの。
**今後のコード更新は手作業ではなくこのスクリプトを使う。**

```bash
./scripts/deploy.sh                 # 通常デプロイ
./scripts/deploy.sh --clear-weather # 天気の表示書式を変えた時など、当日分weather_cacheも削除
```

pytest が赤の場合は launchd の再起動を行わずに中断する。起動後は `/api/health` を
最大30秒ポーリングして疎通確認する。

### dashboard.db の日次バックアップ

`app/scheduler.py` の `backup_database` を毎日 3:00 に実行し、`backups/dashboard-YYYY-MM-DD.db`
として保存（直近7世代のみ保持）。曜日タスク・学校配布物提案は dashboard.db にしか無いデータなので、
誤操作やディスク障害時の保険になる。`backups/` は git 管理外。

### mDNS でのIP依存排除（要検証）

キオスクのURLを `http://<IPアドレス>:8080` にしていると、DHCPでMacのIPが変わるたびに
キオスク側の設定変更が必要になる（`feedback_mac_ip_dhcp` 参照）。macOSは標準でBonjour(mDNS)に
対応しているため、`http://<Macのホスト名>.local:8080` でアクセスできないか確認する。

```bash
# Macのホスト名を確認
scutil --get LocalHostName
```

**注意:** タブレット（TAB-A05-BA1 / Android 9）がmDNS解決に対応しているかは実機での確認が必要。
非対応の場合はルーター側でMacのMACアドレスにDHCP固定IPを予約する方式にフォールバックすること。

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

---

## 7. 技術的な補足

### DB スキーマ（SQLite: dashboard.db）

```sql
-- タスク完了状態
CREATE TABLE IF NOT EXISTS task_completions (
    task_id      TEXT PRIMARY KEY,
    task_type    TEXT NOT NULL,  -- "stock" | "flow" | "weekly"
    completed_at TEXT,           -- ISO 8601
    due_date     TEXT            -- YYYY-MM-DD
);

-- 学校配布物イベント提案
CREATE TABLE IF NOT EXISTS event_proposals (
    id           TEXT PRIMARY KEY,
    child_name   TEXT NOT NULL,
    title        TEXT NOT NULL,
    event_date   TEXT NOT NULL,
    time_start   TEXT,
    time_end     TEXT,
    location     TEXT,
    description  TEXT,
    image_filename TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'pending',
    created_at   TEXT NOT NULL
);

-- ダッシュボード専用の曜日タスク
CREATE TABLE IF NOT EXISTS weekly_tasks (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    weekdays   TEXT NOT NULL DEFAULT '',  -- JSON配列: [0,1,4] (0=月〜6=日)
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    category   TEXT NOT NULL DEFAULT 'task'  -- "task"(通常) or "trash"(ゴミ出し)
);
```

- WALモード有効（読み書き並行性向上）
- **ストックタスク**: 完了状態は永続
- **フロータスク**: 日付変更時に `cleanup_old_flow_completions()` で自動削除
- **曜日タスク**: 当日日付を `due_date` として記録、翌日リセット
- **`category` 列は init_db() 内で既存DBにも自動マイグレーション**（`PRAGMA table_info` で存在確認後
  `ALTER TABLE` を実行。`CREATE TABLE IF NOT EXISTS` だけでは既存テーブルに列は追加されないため）

### タスク完了APIの重要な設計

```
❌ 旧: POST /api/tasks/{task_id}/complete   ← task_id に "://" があると FastAPI が 404
✅ 現: POST /api/tasks/complete              ← task_id は必ずリクエストボディで送る
```

Reminders 由来の `task_id` は `x-apple-reminder://UUID` という形式でスラッシュを含む。
FastAPI のパスパラメータは `/` にマッチしないため、必ずボディで送ること（URLエンコードでも解決しない）。

### complete_reminder.applescript の注意

全リスト総当たり検索（`every list` ループ + `whose id is`）は iCloud 往復が重なり30秒タイムアウトする。
呼び出し時は**対象リスト名を引数で渡す**こと：

```python
# 正しい呼び出し（app/routers/tasks.py）
set_reminder_completed(task_id, True, [settings.stock_list_name])  # or flow_list_name
```

### SSE (Server-Sent Events)

- `GET /api/stream` でクライアントが接続
- 接続時に現在データを即送信、以降はデータ変更時にプッシュ
- 30秒ごとにkeepaliveコメント送信（プロキシタイムアウト防止）
- EventSourceはブラウザ側で自動再接続

### PWA / Service Worker キャッシュ戦略

| リソース | 戦略 | 理由 |
|---------|------|------|
| `/`（ナビゲーション） | **network-first** | HTML/トークン変更を即反映 |
| `/static/js/*`（ESモジュール一式） | **network-first** | JS 修正を即反映 |
| `/static/*.css`, manifest 等 | stale-while-revalidate | 表示を犠牲にせず裏で更新 |
| `/api/*` | network-first | 常に最新データ |
| `/api/stream` (SSE) | SW を通さない | ストリームを途切れさせない |

**重要**: `sw.js` / `static/js/**`（全ESモジュール） / `style.css` / `index.html` は FastAPI の専用ルートで
`Cache-Control: no-cache` 配信。専用ルートは `app.mount("/static", ...)` より**前**に定義すること
（後だと StaticFiles に飲み込まれる）。`/static/js/{filepath:path}` の1ルートで配下の全モジュールをカバーする
ため、新しいコンポーネントファイルを追加してもルート追加は不要。

SW の `install` では `cache.add(new Request(url, { cache: 'reload' }))` を使いHTTPキャッシュを迂回する。

### フロントエンドのアーキテクチャ（Phase 1で刷新）

`static/app.js`（765行の単一ファイル・innerHTML手書き）は `static/js/` 配下のESモジュールに分割した
（ビルドステップ・フレームワークは導入せず、ブラウザネイティブの `<script type="module">` + 素の `import`）。

- **状態は `state.js` に一本化**: SSE受信は `setState({ data, proposals })` を呼ぶだけ。各コンポーネントは
  `subscribe()` されたrender関数で自分の担当DOM要素だけを再描画する
- **各コンポーネントは自分のコンテナ外を触らない**（`components/*.js` の `render(state)`）。
  過去に発生した「innerHTML上書きで無関係の子要素を破壊し、null参照からのTypeErrorがSSEのtry/catchで
  silent failする」バグ（`feedback_js_innerhtml_silent_fail`）の再発を設計で防ぐ
- **エラーは握りつぶさない**: `api.js` の `apiFetch()` が通信失敗・非2xxを検知すると必ず `statusBanner` に
  到達させてから呼び出し元に返す/再スローする
- 新しいUI機能を追加する際は `static/js/components/` に1ファイル追加し、`main.js` で `subscribe` に
  登録する形式を踏襲すること

---

## 8. テスト

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

---

## 9. トラブルシューティング

| 症状 | 原因と対処 |
|------|-----------|
| 画面上部に黄色の警告バナーが出る | `/api/health` の `warnings` を確認（`curl localhost:8080/api/health \| jq .warnings`）。トークン失効/期限接近、または各データソースの同期停止を検知している |
| 予定が急に表示されなくなった | Google OAuth トークン期限切れ（約6ヶ月）。`logs/dashboard.log` で `invalid_grant` 確認 → `python setup_google_auth.py husband` 等で再認証 |
| 天気が表示されない / 古い | `python3 -c "from app.services.weather import fetch_weather; print(fetch_weather())"` で単体確認。ネットワーク問題ならサーバー再起動で再取得 |
| チェックしてもタスクが消えない | `POST /api/tasks/complete` が 404 になっていないかブラウザDevToolsで確認。正常なら200でSSE再配信後に消える |
| リマインダーに完了が反映されない | `logs/dashboard.log` で `complete_reminder.applescript タイムアウト` を確認。対象リスト名引数が渡されているか確認 |
| 完了済みタスクがリストに残る | `data_assembler.py` が `filter out` でなく `mark only` になっていないか確認 |
| リマインダーが表示されない | 起動後1〜5分待つ（iCloud同期中）。`logs/dashboard.log` で "Reminders 取得完了" を確認 |
| リマインダーがタイムアウトし続ける | Reminders.app が固まっている。`killall Reminders && open -a Reminders` で再起動 |
| コード修正しても画面が変わらない | Service Worker キャッシュ。**2回リロード**（1回目:新SW起動、2回目:新JS反映）。確実には Safari > 開発 > キャッシュを空にする |
| Mac再起動後にサービスが起動しない | `launchctl list \| grep family` で確認。plist が `~/Library/LaunchAgents/` にあるか確認 |
| タブレットからアクセスできない | MacのIPアドレス確認（`ipconfig getifaddr en0`）+ ファイアウォールでport 8080を許可 |

---

## 10. 主要ライブラリ

| パッケージ | 用途 |
|-----------|------|
| FastAPI | Webフレームワーク |
| uvicorn | ASGIサーバー |
| pydantic-settings | 設定管理（.env読み込み） |
| aiosqlite | 非同期SQLite |
| APScheduler | 定期実行スケジューラ |
| google-api-python-client | Google Calendar API |
| google-auth-oauthlib | Google OAuth2 認証 |
| jpholiday | 日本の祝日判定 |
| (osascript) | Apple Reminders アクセス（AppleScript） |
