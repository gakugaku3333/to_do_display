import aiosqlite

DB_PATH = "dashboard.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS task_completions (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                completed_at TEXT,
                due_date TEXT
            )
        """)
        await db.commit()


async def get_completed_ids() -> set[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT task_id FROM task_completions") as cursor:
            rows = await cursor.fetchall()
    return {row[0] for row in rows}


async def mark_complete(task_id: str, task_type: str, due_date: str | None):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO task_completions (task_id, task_type, completed_at, due_date) VALUES (?, ?, ?, ?)",
            (task_id, task_type, now, due_date),
        )
        await db.commit()


async def mark_incomplete(task_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM task_completions WHERE task_id = ?", (task_id,))
        await db.commit()


async def cleanup_old_flow_completions(today_str: str):
    """フロー型タスクの消込を、期日が変わったらリセットする"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM task_completions WHERE task_type = 'flow' AND due_date != ?",
            (today_str,),
        )
        await db.commit()
