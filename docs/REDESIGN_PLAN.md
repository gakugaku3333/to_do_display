# 家族ダッシュボード v2 指示書 — 「今ゼロから作るなら」再設計プラン

作成日: 2026-07-04
対象: 別セッションでの実装作業のための指示書。このドキュメント自体が成果物であり、本セッションでは実装しない。

---

## 0. 基本方針（最重要）

**フルリライトはしない。** 現行アーキテクチャ（FastAPI + APScheduler + SSE + SQLite + キオスクPWA）は、この用途（Mac mini常駐 + 古いAndroidタブレット表示）に対してほぼ正解であり、ゼロから作り直しても同じ骨格に戻る。問題は骨格ではなく以下の3点に集中している:

1. **フロントエンドが単一765行の app.js + innerHTML 手書きレンダリング** — 状態管理がなく、DOM破壊による silent fail が過去に実際に起きている（feedback_js_innerhtml_silent_fail）
2. **運用の壊れやすさが暗黙知に依存** — OAuthトークン6ヶ月失効、DHCP IP変更、デプロイ時の再起動忘れ・weather_cache消し忘れ。全部「知っていれば防げる」事故
3. **魅力（家族が毎日見たくなる理由）への投資不足** — 機能は揃ったが「情報掲示板」止まり

よって v2 は「**フロントエンドの作り直し + 運用の自動化 + 家族体験の強化**」の3本柱。バックエンドは整理に留める。

### 引き継ぎ必須の教訓（違反するとv1で踏んだ地雷を再度踏む）

実装セッションは着手前に必ずこのリストを読むこと:

- iCloud Reminders は CalDAV 不可。AppleScript (osascript) 経由のみ。バッチ一括取得 + ThreadPoolExecutor 必須。初回は1〜5分かかるので起動をブロックしない
- `task_id` は `x-apple-reminder://UUID` 形式で `/` を含む。**URLパスに入れず必ずリクエストボディで送る**
- complete_reminder.applescript は**対象リスト名を引数指定**（全リスト総当たりは30秒タイムアウト）
- Service Worker: sw.js / app.js / style.css / index.html は `Cache-Control: no-cache` の専用ルートで配信し、`app.mount("/static")` より**前**に定義。SW install は `cache: 'reload'`
- Pythonコード変更後は `launchctl kickstart -k gui/$(id -u)/com.family.dashboard` 必須。天気の表示書式変更は当日分 weather_cache 削除も必要
- リスト名は**カタカナ**で「ストック」「フロー」
- pre-commit で pytest 必須（`git config core.hooksPath .githooks` 済み）。API契約変更時にテストを腐らせない
- 対象タブレットは TAB-A05-BA1（Android 9 / SDK28、Brave v1.80.126 が最終）。**モダンすぎるJS/CSS機能は使用前に互換性確認**

---

## 1. フェーズ構成

| フェーズ | 内容 | 価値 | リスク |
|---|---|---|---|
| Phase 0 | 運用の自己防衛（半日〜1日） | 事故ゼロ化 | 低 |
| Phase 1 | フロントエンド再構築（2〜3日） | 保守性・拡張の土台 | 中 |
| Phase 2 | 「見たくなる」体験機能（1機能ずつ） | 家族の満足度 | 低 |
| Phase 3 | バックエンド整理（任意・随時） | コード品質 | 低 |

各フェーズは独立してマージ可能。Phase 1 完了までは Phase 2 の新UI機能に着手しない。

---

## Phase 0: 運用の自己防衛（最初にやる。効果対コスト最大）

### 0-1. デプロイスクリプト `scripts/deploy.sh`
手順の暗黙知をコード化する。内容:
```
1. git pull（または対象ブランチのチェックアウト）
2. pip install -r requirements.txt（requirements差分があった場合）
3. pytest 実行 → 赤なら中断
4. 引数 --clear-weather 指定時は当日分 weather_cache を削除
5. launchctl kickstart -k gui/$(id -u)/com.family.dashboard
6. /api/health をポーリングして起動確認、結果を表示
```

### 0-2. `/api/health` の拡張とダッシュボード上のセルフ診断
health レスポンスに追加:
- `google_token_status`: 各トークンの最終リフレッシュ成功時刻と `invalid_grant` 検出フラグ
- `last_sync`: calendar / reminders / weather それぞれの最終成功時刻
- `token_age_days`: トークン発行からの経過日数

フロント側: 同期が2時間以上止まっている・`invalid_grant` 検出時に、画面上部に黄色の警告バナーを常時表示（「予定が急に消えた」を家族が気づく前に検知する）。朝のブリーフィングにも「カレンダー連携の再認証が必要です」を含める。

### 0-3. mDNS でIP依存を排除
キオスクのURLを `http://<IP>:8080` から `http://<mac-hostname>.local:8080` に変更（macOSはBonjour標準対応、Android 9 のmDNS解決可否は**実機で要検証**。不可なら Mac 側でDHCP固定IP予約をルーター設定し、reference_kiosk_tablet.md の手順を更新）。feedback_mac_ip_dhcp の再発防止。

### 0-4. dashboard.db の日次バックアップ
launchd または APScheduler で `dashboard.db` を日次で `backups/` にコピー（7世代ローテーション）。曜日タスクと配布物提案はここにしか無いデータ。

---

## Phase 1: フロントエンド再構築

### 方針
- **ビルドステップは導入しない**（Vite等は不採用）。Mac mini 上の運用で `npm build` を挟むとデプロイ事故の温床になる。ES Modules の素の import で分割する（Brave 1.80 = Chromium系で対応済み。着手時に実機で `<script type="module">` 動作確認を最初に行うこと）
- **フレームワークも入れない**。代わりに「**render関数は常に全再構築、ただしルートコンテナのみ差し替え**」の規約で統一し、innerHTML による子要素破壊バグのクラスを設計で潰す

### 構成
```
static/
├── index.html
├── style.css        → base.css / components.css / theme.css に分割
├── sw.js            （キャッシュ戦略は現行を維持）
└── js/
    ├── main.js          # 起動・SSE接続・グローバル状態
    ├── state.js         # 単一の状態オブジェクト + subscribe/notify（数十行の自作でよい）
    ├── api.js           # fetch ラッパー（authHeaders 集約、エラーは必ずバナー表示）
    ├── components/
    │   ├── clock.js / dateHeader.js / weather.js
    │   ├── events.js / tasks.js / weeklyTasks.js
    │   ├── proposals.js / weekModal.js / statusBanner.js
    │   └── …
    └── utils.js         # escapeHtml, 日付整形など
```

### 設計規約（実装セッションはこれをコードレビュー基準にする）
1. 各コンポーネントは `render(container, state)` を公開し、**自分のコンテナ内しか触らない**
2. state.js の状態変更は必ず `setState()` 経由 → 購読コンポーネントが再render。SSE受信も setState に流すだけ
3. try/catch で握りつぶさない。すべてのエラーは statusBanner に到達させる
4. `escapeHtml` を通さない文字列補間の innerHTML は禁止

### 検証
- 移行は**コンポーネント単位で段階的に**行い、各段階で実機タブレット確認
- 完了条件: 既存機能の全動作（タスク完了・曜日タスクCRUD・配布物承認・週間モーダル・Wake Lock）が実機で確認できること
- 余力があれば Playwright の smoke テスト（ページ表示→タスク一覧が描画される→タップで完了が飛ぶ）を1本追加し pre-commit ではなく手動/CI 用に置く

---

## Phase 2: 「見たくなる」体験機能

優先度順。**1機能=1ブランチ=1マージ**で小さく回す。各機能とも Phase 1 のコンポーネント規約に従う。

### 2-1. ゴミ出しの日表示 ⭐最優先
曜日タスクの仕組みに「ゴミ種別」フィールドを足すだけで実現可能。日付ヘッダー横に「🗑️ 燃えるゴミ」バッジ。朝のブリーフィングにも含める。**実装コストが最小で毎日確実に役立つ**。

### 2-2. イベントカウントダウン
Google カレンダーの予定にタイトル接頭辞（例: `★運動会`）を付けたものを「あと◯日」として大きく表示。子どもが楽しみにする掲示物になる。設定UIは作らず命名規約で実現（設定画面はメンテコストになる）。

### 2-3. 子ども向けタスク完了演出
weekly タスク完了時に紙吹雪アニメーション + 効果音（音はタブレット設定でON/OFF可）。週の完了率をヘッダーに星で表示（`weekly_tasks` 完了履歴は既にDBにある）。**ゲーミフィケーションは深追いしない**（ポイント制などは運用が続かない）。

### 2-4. アイドル時フォトフレームモード
一定時間（夜間など shouldScreenBeOff に準ずる時間帯の手前）に、指定フォルダの家族写真をスライドショー表示。タップで即ダッシュボードに復帰。Mac mini 上のフォルダを `/api/photos` で配信する薄い実装でよい。**ダッシュボードが「消えている時間」を価値に変える**。

### 2-5. 夜のブリーフィング
`/api/briefing?mode=evening`: 明日の予定・明日のゴミ出し・明日の天気・未完了ストックタスク。iOS ショートカットを夜21時にもう1本追加。

### 2-6. 献立・買い物メモ（検討のみ・要相談）
Reminders に「買い物」リストを足して表示するだけなら安い。献立管理まで踏み込むと運用負荷が高いので、**実装前に家族の要望を確認してから**着手。

---

## Phase 3: バックエンド整理（随時・機能追加のついでに）

1. **`FAMILY_CALENDAR_ID` を .env に移動**（現在 google_calendar.py にハードコード）
2. **services を Protocol で統一**: `DataSource` プロトコル（`fetch() -> T`, `source_name`, `last_success`）を定義し、calendar / reminders / weather を揃える。0-2 の last_sync 実装が自然に載る
3. **キャッシュに鮮度メタデータ**: `TodayData` に各ソースの `fetched_at` を含め、フロントで「⚠︎ 予定は45分前の情報です」と表示できるようにする
4. **routers の認可・エラー処理の共通化**（現状の重複を Depends に寄せる）
5. Python 3.13 前提の型記法（`X | None` 等）への統一 — 触ったファイルから順次でよい

やらないこと: DBのORM化（SQLite直書きで十分）、非同期AppleScript化のこれ以上の抽象化、マイクロサービス分割。

---

## 4. 実装セッションへの進め方指示

1. まず Phase 0 を1PRで完了させる（deploy.sh → health拡張 → mDNS検証 → バックアップの順）
2. Phase 1 は「js分割の骨組み + clock/weather移行」を最初のPRにし、実機確認してから残りを移行
3. 各PRのマージ前に: pytest 緑 + 実機タブレットでの表示確認 + HANDOVER.md の該当箇所更新
4. デプロイは必ず 0-1 で作る deploy.sh を使う（手順の口伝を今後禁止する）
5. 判断に迷う点（mDNS不可時の代替、2-6の着手可否）はユーザーに確認する
