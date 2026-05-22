from __future__ import annotations

from pydantic import BaseModel

WEEKDAYS_JA = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]


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


class EventProposal(BaseModel):
    id: str
    child_name: str       # 紗奈 / 和花 / 舞
    title: str
    event_date: str       # YYYY-MM-DD
    time_start: str | None = None   # HH:MM
    time_end: str | None = None     # HH:MM
    location: str | None = None
    description: str | None = None
    image_filename: str = ""
    status: str = "pending"  # pending / approved / rejected


class TodayData(BaseModel):
    date: str       # YYYY-MM-DD
    weekday: str    # 日本語曜日 (月曜日, 火曜日, ...)
    events: list[CalendarEvent]
    stock_tasks: list[Task]
    flow_tasks: list[Task]
    last_refresh: str | None = None  # HH:MM (Asia/Tokyo)
    proposals: list[EventProposal] = []  # 承認待ちの学校行事提案
