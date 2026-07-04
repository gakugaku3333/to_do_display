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


class WeatherHour(BaseModel):
    label: str        # 例: "6時〜", "12時〜", "翌0時〜"
    precip_prob: int  # 0–100 (%)


class WeatherData(BaseModel):
    condition: str
    condition_emoji: str
    temp_max: int | None = None
    temp_min: int | None = None
    temp_max_delta: int | None = None  # 前日比（最高気温）。基準日が無ければ None
    temp_min_delta: int | None = None  # 前日比（最低気温）
    hourly_precip: list[WeatherHour]


class CountdownEvent(BaseModel):
    title: str        # "★"接頭辞を除いたタイトル
    event_date: str    # YYYY-MM-DD
    days_until: int    # 0=今日, 1=明日, ...


class WeekDay(BaseModel):
    date: str                       # YYYY-MM-DD
    weekday: str                    # 日本語曜日 (月曜日, ...)
    is_today: bool = False
    is_holiday: bool = False
    holiday_name: str | None = None
    events: list[CalendarEvent] = []


class WeekData(BaseModel):
    days: list[WeekDay]
    last_refresh: str | None = None  # HH:MM (Asia/Tokyo) 取得時刻


class TodayData(BaseModel):
    date: str       # YYYY-MM-DD
    weekday: str    # 日本語曜日 (月曜日, 火曜日, ...)
    events: list[CalendarEvent]
    stock_tasks: list[Task]
    flow_tasks: list[Task]
    last_refresh: str | None = None  # HH:MM (Asia/Tokyo)
    proposals: list[EventProposal] = []  # 承認待ちの学校行事提案
    weather: WeatherData | None = None
    is_holiday: bool = False        # 祝日・振替休日の場合 True
    holiday_name: str | None = None  # 祝日名（例: "元日", "春分の日"）
    trash_labels: list[str] = []    # 今日のゴミ出し種別（category="trash"の曜日タスク）
    countdown_events: list[CountdownEvent] = []  # "★"接頭辞イベントのカウントダウン（近い順）
