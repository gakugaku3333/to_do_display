from __future__ import annotations

import logging
from datetime import datetime, timezone

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = "dashboard.db"
_connection: aiosqlite.Connection | None = None


async def get_connection() -> aiosqlite.Connection:
    global _connection
    if _connection is None:
        _connection = await aiosqlite.connect(DB_PATH)
        await _connection.execute("PRAGMA journal_mode=WAL")
        logger.info("データベース接続を確立しました (WALモード)")
    return _connection


async def close_connection():
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
        logger.info("データベース接続を閉じました")


async def init_db():
    try:
        db = await get_connection()
        await db.execute("""
            CREATE TABLE IF NOT EXISTS task_completions (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                completed_at TEXT,
                due_date TEXT
            )
        """)
        await db.commit()
        logger.info("データベース初期化完了")
    except Exception:
        logger.error("データベース初期化に失敗しました", exc_info=True)
        raise


async def get_completed_ids() -> set[str]:
    try:
        db = await get_connection()
        async with db.execute("SELECT task_id FROM task_completions") as cursor:
            rows = await cursor.fetchall()
        return {row[0] for row in rows}
    except Exception:
        logger.error("完了タスクIDの取得に失敗しました", exc_info=True)
        return set()


async def mark_complete(task_id: str, task_type: str, due_date: str | None):
    try:
        now = datetime.now(timezone.utc).isoformat()
        db = await get_connection()
        await db.execute(
            "INSERT OR REPLACE INTO task_completions (task_id, task_type, completed_at, due_date) VALUES (?, ?, ?, ?)",
            (task_id, task_type, now, due_date),
        )
        await db.commit()
    except Exception:
        logger.error("タスク完了の記録に失敗しました: %s", task_id, exc_info=True)
        raise


async def mark_incomplete(task_id: str):
    try:
        db = await get_connection()
        await db.execute("DELETE FROM task_completions WHERE task_id = ?", (task_id,))
        await db.commit()
    except Exception:
        logger.error("タスク未完了の記録に失敗しました: %s", task_id, exc_info=True)
        raise


async def cleanup_old_flow_completions(today_str: str):
    """フロー型タスクの消込を、期日が変わったらリセットする"""
    try:
        db = await get_connection()
        await db.execute(
            "DELETE FROM task_completions WHERE task_type = 'flow' AND due_date != ?",
            (today_str,),
        )
        await db.commit()
    except Exception:
        logger.error("フロータスクのクリーンアップに失敗しました", exc_info=True)
