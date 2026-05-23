from __future__ import annotations

import json
import logging
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

from app.config import settings
from app.models import Task

logger = logging.getLogger(__name__)

# macOS の osascript (AppleScript) 経由で Reminders.app にアクセスする。
# CalDAV は iOS 13+ / macOS Catalina 以降、Apple Reminders に非対応のため使用不可。

_SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "fetch_reminders.applescript"
_COMPLETE_SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "complete_reminder.applescript"
_CREATE_SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "create_reminder.applescript"

# 初回実行は iCloud 同期で時間がかかることがある
_OSASCRIPT_TIMEOUT = 120


def _fetch_reminders_from_list(list_name: str) -> list[dict]:
    """osascript 経由で指定リストのリマインダーを取得する"""
    try:
        result = subprocess.run(
            ["osascript", str(_SCRIPT_PATH), list_name],
            capture_output=True,
            text=True,
            timeout=_OSASCRIPT_TIMEOUT,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "Can't get list" in stderr:
                logger.warning("リスト '%s' が見つかりません", list_name)
            else:
                logger.error("osascript エラー (list=%s): %s", list_name, stderr)
            return []

        output = result.stdout.strip()
        if not output or output == "[]":
            return []

        return json.loads(output)

    except subprocess.TimeoutExpired:
        logger.error("osascript タイムアウト %d秒 (list=%s)", _OSASCRIPT_TIMEOUT, list_name)
        return []
    except json.JSONDecodeError:
        logger.error("JSON パースエラー (list=%s)", list_name, exc_info=True)
        return []
    except Exception:
        logger.error("リマインダー取得に失敗 (list=%s)", list_name, exc_info=True)
        return []


def _parse_reminder(rem: dict, task_type: str, today: date) -> Task | None:
    """取得したリマインダー dict を Task モデルに変換する"""
    try:
        uid = rem.get("id", "")
        title = rem.get("name", "(タイトルなし)")
        completed = rem.get("completed", False)
        due_str = rem.get("dueDate")

        due_date: date | None = None
        due_date_str: str | None = None
        if due_str:
            due_date = date.fromisoformat(due_str)
            due_date_str = due_date.isoformat()

        if task_type == "stock":
            # ストック: 期限が今日以前のタスク（期限なしも含む）
            if due_date and due_date > today:
                return None
            is_overdue = bool(due_date and due_date < today)
            return Task(
                id=uid,
                title=title,
                task_type="stock",
                due_date=due_date_str,
                is_overdue=is_overdue,
                is_completed=completed,
                owner="shared",
            )

        elif task_type == "flow":
            # フロー: 期限が今日のタスク、または期限なしのタスクを表示
            if due_date and due_date != today:
                return None
            return Task(
                id=uid,
                title=title,
                task_type="flow",
                due_date=due_date_str,
                is_overdue=False,
                is_completed=completed,
                owner="shared",
            )

    except Exception:
        logger.warning("リマインダーのパースに失敗: %s", rem, exc_info=True)
    return None


def fetch_tasks() -> tuple[list[Task], list[Task]]:
    """ストック・フロー両リストからタスクを並列取得する"""
    today = date.today()

    if sys.platform != "darwin":
        logger.warning("macOS 以外では Reminders にアクセスできません。ダミーデータを返します")
        return _dummy_tasks(today)

    with ThreadPoolExecutor(max_workers=2) as executor:
        stock_future = executor.submit(_fetch_reminders_from_list, settings.stock_list_name)
        flow_future = executor.submit(_fetch_reminders_from_list, settings.flow_list_name)
        stock_rems = stock_future.result()
        flow_rems = flow_future.result()

    stock_tasks: list[Task] = []
    flow_tasks: list[Task] = []

    for rem in stock_rems:
        task = _parse_reminder(rem, "stock", today)
        if task:
            stock_tasks.append(task)

    for rem in flow_rems:
        task = _parse_reminder(rem, "flow", today)
        if task:
            flow_tasks.append(task)

    logger.info(
        "Reminders 取得完了: ストック=%d件, フロー=%d件",
        len(stock_tasks),
        len(flow_tasks),
    )
    return stock_tasks, flow_tasks


def set_reminder_completed(task_id: str, completed: bool) -> bool:
    """Reminders.app のタスク完了状態を更新する。成功時 True を返す。"""
    if sys.platform != "darwin":
        return False
    try:
        result = subprocess.run(
            ["osascript", str(_COMPLETE_SCRIPT_PATH), task_id, str(completed).lower()],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("complete_reminder.applescript エラー (id=%s): %s", task_id, result.stderr.strip())
            return False
        output = result.stdout.strip()
        if output == "not_found":
            logger.warning("Reminders でタスクが見つかりません (id=%s)", task_id)
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.error("complete_reminder.applescript タイムアウト (id=%s)", task_id)
        return False
    except Exception:
        logger.error("Reminders 完了状態の更新に失敗 (id=%s)", task_id, exc_info=True)
        return False


def create_reminder(
    list_name: str,
    title: str,
    body: str = "",
    due_date: str | None = None,
) -> str | None:
    """Reminders.app に新規リマインダーを作成する。成功時は新ID、失敗時は None。"""
    if sys.platform != "darwin":
        logger.warning("macOS 以外では Reminders を作成できません")
        return None
    due_arg = due_date if due_date else "null"
    try:
        result = subprocess.run(
            ["osascript", str(_CREATE_SCRIPT_PATH), list_name, title, body, due_arg],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error(
                "create_reminder.applescript エラー (list=%s, title=%s): %s",
                list_name, title, result.stderr.strip(),
            )
            return None
        output = result.stdout.strip()
        if output.startswith("error:"):
            logger.error("Reminders作成エラー: %s", output)
            return None
        return output
    except subprocess.TimeoutExpired:
        logger.error("create_reminder.applescript タイムアウト (title=%s)", title)
        return None
    except Exception:
        logger.error("Reminders作成に失敗 (title=%s)", title, exc_info=True)
        return None


def _dummy_tasks(today: date) -> tuple[list[Task], list[Task]]:
    """macOS 以外・開発用のダミーデータ"""
    yesterday = (today - timedelta(days=1)).isoformat()
    stock = [
        Task(
            id="demo-stock-1",
            title="市役所に書類を提出する",
            task_type="stock",
            due_date=yesterday,
            is_overdue=True,
            is_completed=False,
        ),
        Task(
            id="demo-stock-2",
            title="保険の更新手続き",
            task_type="stock",
            due_date=today.isoformat(),
            is_overdue=False,
            is_completed=False,
        ),
    ]
    flow = [
        Task(
            id="demo-flow-1",
            title="ゴミ出し (燃えるゴミ)",
            task_type="flow",
            due_date=today.isoformat(),
            is_overdue=False,
            is_completed=False,
        ),
        Task(
            id="demo-flow-2",
            title="お風呂掃除",
            task_type="flow",
            due_date=today.isoformat(),
            is_overdue=False,
            is_completed=False,
        ),
    ]
    return stock, flow
