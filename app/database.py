from __future__ import annotations

import logging
import uuid
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS event_proposals (
                id TEXT PRIMARY KEY,
                child_name TEXT NOT NULL,
                title TEXT NOT NULL,
                event_date TEXT NOT NULL,
                time_start TEXT,
                time_end TEXT,
                location TEXT,
                description TEXT,
                image_filename TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS weekly_tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                weekdays TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
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


async def save_proposals(proposals: list[dict]):
    try:
        now = datetime.now(timezone.utc).isoformat()
        db = await get_connection()
        for p in proposals:
            await db.execute(
                """INSERT OR IGNORE INTO event_proposals
                   (id, child_name, title, event_date, time_start, time_end,
                    location, description, image_filename, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
                (
                    p["id"], p["child_name"], p["title"], p["event_date"],
                    p.get("time_start"), p.get("time_end"), p.get("location"),
                    p.get("description"), p.get("image_filename", ""), now,
                ),
            )
        await db.commit()
    except Exception:
        logger.error("提案の保存に失敗しました", exc_info=True)
        raise


async def get_pending_proposals() -> list[dict]:
    try:
        db = await get_connection()
        async with db.execute(
            "SELECT * FROM event_proposals WHERE status = 'pending' ORDER BY event_date, time_start"
        ) as cursor:
            rows = await cursor.fetchall()
            cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in rows]
    except Exception:
        logger.error("承認待ち提案の取得に失敗しました", exc_info=True)
        return []


async def update_proposal_status(proposal_id: str, status: str):
    try:
        db = await get_connection()
        await db.execute(
            "UPDATE event_proposals SET status = ? WHERE id = ?",
            (status, proposal_id),
        )
        await db.commit()
    except Exception:
        logger.error("提案ステータス更新に失敗しました: %s", proposal_id, exc_info=True)
        raise


async def get_proposal_by_id(proposal_id: str) -> dict | None:
    try:
        db = await get_connection()
        async with db.execute(
            "SELECT * FROM event_proposals WHERE id = ?", (proposal_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))
    except Exception:
        logger.error("提案の取得に失敗しました: %s", proposal_id, exc_info=True)
        return None


async def cleanup_old_flow_completions(today_str: str):
    """フロー型・曜日型タスクの完了状態を、日付が変わったらリセットする"""
    try:
        db = await get_connection()
        await db.execute(
            "DELETE FROM task_completions WHERE task_type IN ('flow', 'weekly') AND due_date != ?",
            (today_str,),
        )
        await db.commit()
    except Exception:
        logger.error("フロー/曜日タスクのクリーンアップに失敗しました", exc_info=True)


# ===== 曜日タスク CRUD =====

def _parse_weekdays(weekdays_str: str) -> list[int]:
    if not weekdays_str:
        return []
    try:
        return [int(x) for x in weekdays_str.split(",") if x.strip()]
    except ValueError:
        return []


async def get_all_weekly_tasks() -> list[dict]:
    try:
        db = await get_connection()
        async with db.execute(
            "SELECT id, title, weekdays, sort_order FROM weekly_tasks ORDER BY sort_order, created_at"
        ) as cursor:
            rows = await cursor.fetchall()
            cols = [d[0] for d in cursor.description]
        return [
            {**dict(zip(cols, row)), "weekdays": _parse_weekdays(dict(zip(cols, row))["weekdays"])}
            for row in rows
        ]
    except Exception:
        logger.error("曜日タスクの取得に失敗しました", exc_info=True)
        return []


async def get_weekly_tasks_for_weekday(weekday: int) -> list[dict]:
    """今日の曜日（0=月〜6=日）に一致する曜日タスクを返す"""
    all_tasks = await get_all_weekly_tasks()
    return [t for t in all_tasks if weekday in t["weekdays"]]


async def create_weekly_task(title: str, weekdays: list[int]) -> str:
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    weekdays_str = ",".join(str(w) for w in sorted(weekdays))
    try:
        db = await get_connection()
        await db.execute(
            "INSERT INTO weekly_tasks (id, title, weekdays, sort_order, created_at) VALUES (?, ?, ?, 0, ?)",
            (task_id, title, weekdays_str, now),
        )
        await db.commit()
    except Exception:
        logger.error("曜日タスクの作成に失敗しました: %s", title, exc_info=True)
        raise
    return task_id


async def update_weekly_task(task_id: str, title: str, weekdays: list[int]) -> bool:
    weekdays_str = ",".join(str(w) for w in sorted(weekdays))
    try:
        db = await get_connection()
        await db.execute(
            "UPDATE weekly_tasks SET title = ?, weekdays = ? WHERE id = ?",
            (title, weekdays_str, task_id),
        )
        affected = db.total_changes
        await db.commit()
        return affected > 0
    except Exception:
        logger.error("曜日タスクの更新に失敗しました: %s", task_id, exc_info=True)
        raise


async def delete_weekly_task(task_id: str) -> bool:
    try:
        db = await get_connection()
        await db.execute("DELETE FROM weekly_tasks WHERE id = ?", (task_id,))
        affected = db.total_changes
        await db.commit()
        return affected > 0
    except Exception:
        logger.error("曜日タスクの削除に失敗しました: %s", task_id, exc_info=True)
        raise
