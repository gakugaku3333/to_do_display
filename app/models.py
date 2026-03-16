from pydantic import BaseModel


class CalendarEvent(BaseModel):
    id: str
    title: str
    start_time: str | None = None  # HH:MM 形式、終日イベントの場合はNone
    end_time: str | None = None
    is_all_day: bool = False
    owner: str  # "husband" or "wife"
    color: str  # CSS カラーコード


class Task(BaseModel):
    id: str
    title: str
    task_type: str  # "stock" or "flow"
    due_date: str | None = None  # YYYY-MM-DD
    is_overdue: bool = False
    is_completed: bool = False
    owner: str = "shared"  # "husband", "wife", or "shared"


class TodayData(BaseModel):
    date: str       # YYYY-MM-DD
    weekday: str    # 日本語曜日 (月曜日, 火曜日, ...)
    events: list[CalendarEvent]
    stock_tasks: list[Task]
    flow_tasks: list[Task]
