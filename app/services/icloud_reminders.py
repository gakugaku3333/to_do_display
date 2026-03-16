from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import caldav
from caldav.elements import dav

from app.config import settings
from app.models import Task


def _get_client() -> caldav.DAVClient:
    return caldav.DAVClient(
        url="https://caldav.icloud.com",
        username=settings.icloud_apple_id,
        password=settings.icloud_app_password,
    )


def _find_reminder_list(principal: caldav.Principal, list_name: str) -> caldav.Calendar | None:
    try:
        calendars = principal.calendars()
        for cal in calendars:
            props = cal.get_properties([dav.DisplayName()])
            name = props.get("{DAV:}displayname", "")
            if name == list_name:
                return cal
    except Exception as e:
        print(f"[iCloud] リスト検索エラー: {e}")
    return None


def _parse_vtodo(todo_component, task_type: str, today: date) -> Task | None:
    try:
        uid = str(todo_component.get("uid", ""))
        title = str(todo_component.get("summary", "(タイトルなし)"))
        status = str(todo_component.get("status", "")).upper()
        due = todo_component.get("due")

        due_date_str: str | None = None
        if due:
            due_val = due.dt
            if isinstance(due_val, datetime):
                due_date = due_val.date()
            else:
                due_date = due_val
            due_date_str = due_date.isoformat()
        else:
            due_date = None
            due_date_str = None

        if task_type == "stock":
            if due_date and due_date > today:
                return None
            is_overdue = bool(due_date and due_date < today)
            return Task(
                id=uid,
                title=title,
                task_type="stock",
                due_date=due_date_str,
                is_overdue=is_overdue,
                is_completed=(status == "COMPLETED"),
                owner="shared",
            )

        elif task_type == "flow":
            if due_date != today:
                return None
            return Task(
                id=uid,
                title=title,
                task_type="flow",
                due_date=due_date_str,
                is_overdue=False,
                is_completed=(status == "COMPLETED"),
                owner="shared",
            )

    except Exception as e:
        print(f"[iCloud] VTODO パースエラー: {e}")
    return None


def fetch_tasks(tz_name: str = "Asia/Tokyo") -> tuple[list[Task], list[Task]]:
    today = date.today()
    stock_tasks: list[Task] = []
    flow_tasks: list[Task] = []

    if not settings.icloud_apple_id or not settings.icloud_app_password:
        print("[iCloud] 認証情報が設定されていません。ダミーデータを返します。")
        return _dummy_tasks(today)

    try:
        client = _get_client()
        principal = client.principal()

        for list_name, task_type, target_list in [
            (settings.stock_list_name, "stock", stock_tasks),
            (settings.flow_list_name, "flow", flow_tasks),
        ]:
            cal = _find_reminder_list(principal, list_name)
            if not cal:
                print(f"[iCloud] リスト '{list_name}' が見つかりませんでした。")
                continue

            todos = cal.todos()
            for todo in todos:
                for component in todo.vobject_instance.components():
                    if component.name == "VTODO":
                        task = _parse_vtodo(component, task_type, today)
                        if task:
                            target_list.append(task)

    except Exception as e:
        print(f"[iCloud] 取得エラー: {e}")

    return stock_tasks, flow_tasks


def _dummy_tasks(today: date) -> tuple[list[Task], list[Task]]:
    """認証情報未設定時のダミーデータ (開発・デモ用)"""
    from datetime import timedelta
    yesterday = (today - timedelta(days=1)).isoformat()
    stock = [
        Task(id="demo-stock-1", title="市役所に書類を提出する", task_type="stock",
             due_date=yesterday, is_overdue=True, is_completed=False),
        Task(id="demo-stock-2", title="保険の更新手続き", task_type="stock",
             due_date=today.isoformat(), is_overdue=False, is_completed=False),
    ]
    flow = [
        Task(id="demo-flow-1", title="ゴミ出し (燃えるゴミ)", task_type="flow",
             due_date=today.isoformat(), is_overdue=False, is_completed=False),
        Task(id="demo-flow-2", title="お風呂掃除", task_type="flow",
             due_date=today.isoformat(), is_overdue=False, is_completed=False),
    ]
    return stock, flow
