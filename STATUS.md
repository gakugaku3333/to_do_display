---
phase: 運用中
next: 10/1朝7:00のGoogle Home読み上げ(GOOGLE_HOME_HOST・未コミットで本番稼働中)を確認し、問題なければspeaker.py/config.py/.env.exampleをコミット
blocker:
updated: 2026-09-30
---

補足: 投げっぱなしの asyncio.create_task（app/routers/tasks.py の Reminders 書き戻し、app/routers/reminders.py の refresh_data）は参照を保持しておらず GC で途中キャンセルされうる。app/main.py の _spawn_startup_task と同じ方式に寄せるのが次候補。
