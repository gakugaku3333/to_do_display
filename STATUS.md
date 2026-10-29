---
phase: 運用中
next: Google Homeの実再生を確認し、既存のGOOGLE_HOME_HOST変更を検証してコミットする
blocker:
updated: 2026-10-30
---

運用手順と終日予定の日付ずれの修正・検証結果は HANDOVER.md §5・§7 を参照。

次回の確認事項:
- 着手可能: GOOGLE_HOME_HOST の既存変更（speaker.py/config.py/.env.example）は今回の修正とは別に未コミットで保全。音声の事前生成は成功しているが実再生は未確認のため、確認後に履歴へ残す。
- 着手可能: タブレットで名前解決が失敗し、再起動後に IP も変更されたため、ルーターの DHCP 予約で接続先を安定させる（手順は HANDOVER.md §5）。
- 要調査: Matter 仮想スイッチのログに utun3 への送信エラーが反復。プロセス稼働は確認したが Google Home との連携成立は未確認。
- 候補: 投げっぱなしの asyncio.create_task（app/routers/tasks.py の Reminders 書き戻し、app/routers/reminders.py の refresh_data）は参照を保持しておらず GC で途中キャンセルされうる。app/main.py の _spawn_startup_task と同じ方式に寄せる。
