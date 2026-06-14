from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config import settings
from app.models import CalendarEvent

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]
TOKENS_DIR = "tokens"
CREDENTIALS_FILE = "credentials.json"

OWNER_COLORS = {
    "husband": "#4A90D9",
    "wife": "#E86A9A",
    "family": "#2ecc71",
}
DEFAULT_OWNER_COLOR = "#888888"

# Google Calendar の「イベントの色」パレット（colorId → 16進カラー）。
# イベント個別に色が設定されている場合は所有者色より優先する。
EVENT_COLOR_MAP = {
    "1": "#7986cb",   # Lavender
    "2": "#33b679",   # Sage
    "3": "#8e24aa",   # Grape
    "4": "#e67c73",   # Flamingo
    "5": "#f6bf26",   # Banana
    "6": "#f4511e",   # Tangerine
    "7": "#039be5",   # Peacock
    "8": "#616161",   # Graphite
    "9": "#3f51b5",   # Blueberry
    "10": "#0b8043",  # Basil
    "11": "#d50000",  # Tomato
}


def _event_color(event: dict, owner: str) -> str:
    """イベントに colorId 指定があればその色を、無ければ所有者色を返す。"""
    color_id = event.get("colorId")
    if color_id and color_id in EVENT_COLOR_MAP:
        return EVENT_COLOR_MAP[color_id]
    return OWNER_COLORS.get(owner, DEFAULT_OWNER_COLOR)


def get_credentials(account_name: str) -> Credentials | None:
    token_path = os.path.join(TOKENS_DIR, f"{account_name}.json")
    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        except Exception:
            logger.warning("%s のトークン更新に失敗しました", account_name, exc_info=True)
            creds = None

    return creds if (creds and creds.valid) else None


def setup_google_auth(account_name: str):
    """初回認証セットアップ用。Mac mini上でブラウザ認証を行う。"""
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"{CREDENTIALS_FILE} が見つかりません。"
            "Google Cloud Console からダウンロードしてプロジェクトルートに配置してください。"
        )
    os.makedirs(TOKENS_DIR, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    token_path = os.path.join(TOKENS_DIR, f"{account_name}.json")
    with open(token_path, "w") as f:
        f.write(creds.to_json())
    logger.info("認証完了: %s に保存しました", token_path)


def _parse_event(event: dict, owner: str, tz: ZoneInfo) -> CalendarEvent:
    title = event.get("summary", "(タイトルなし)")
    start = event.get("start", {})
    end = event.get("end", {})
    color = _event_color(event, owner)

    if "dateTime" in start:
        start_dt = datetime.fromisoformat(start["dateTime"]).astimezone(tz)
        end_dt = datetime.fromisoformat(end["dateTime"]).astimezone(tz)
        return CalendarEvent(
            id=event["id"],
            title=title,
            start_time=start_dt.strftime("%H:%M"),
            end_time=end_dt.strftime("%H:%M"),
            is_all_day=False,
            owner=owner,
            color=color,
        )
    else:
        return CalendarEvent(
            id=event["id"],
            title=title,
            start_time=None,
            end_time=None,
            is_all_day=True,
            owner=owner,
            color=color,
        )


def create_calendar_event(
    title: str,
    event_date: str,
    time_start: str | None,
    time_end: str | None,
    location: str | None,
    description: str | None,
    tz_name: str = "Asia/Tokyo",
) -> str:
    """Google Calendarにイベントを作成し、イベントIDを返す（夫アカウントのプライマリカレンダーに追加）"""
    creds = get_credentials("husband")
    if not creds:
        raise RuntimeError("husband のGoogle認証情報が取得できません")

    service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    if time_start:
        start = {"dateTime": f"{event_date}T{time_start}:00", "timeZone": tz_name}
        end_time = time_end or time_start
        end = {"dateTime": f"{event_date}T{end_time}:00", "timeZone": tz_name}
    else:
        start = {"date": event_date}
        end = {"date": event_date}

    body: dict = {"summary": title, "start": start, "end": end}
    if location:
        body["location"] = location
    if description:
        body["description"] = description

    result = service.events().insert(calendarId="primary", body=body).execute()
    return result["id"]


def _fetch_calendar_events(
    creds: Credentials, cal_id: str, owner: str,
    time_min: str, time_max: str, tz: ZoneInfo,
) -> list[CalendarEvent]:
    """単一カレンダーの当日イベントを取得する。ワーカースレッドから呼ばれる。

    httplib2 / service オブジェクトはスレッド安全ではないため、スレッドごとに
    新しい service を生成する（v2.x の静的 discovery によりネットワークは叩かない）。
    """
    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        result = service.events().list(
            calendarId=cal_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
    except Exception:
        logger.warning("カレンダー %s の取得をスキップ", cal_id, exc_info=True)
        return []

    return [_parse_event(event, owner, tz) for event in result.get("items", [])]


def _build_jobs() -> list[tuple[Credentials, str, str]]:
    """取得対象カレンダーを (creds, calendar_id, owner) のリストとして列挙する。

    夫→ファミリー→妻 の順を維持し、複数カレンダーに同一イベントが出たときの
    重複排除の優先順を固定する。今日／週間の両取得で共有する。
    """
    excluded_ids = settings.excluded_calendar_ids_set
    family_calendar_id = settings.family_calendar_id

    jobs: list[tuple[Credentials, str, str]] = []
    for account_name in ("husband", "wife"):
        creds = get_credentials(account_name)
        if not creds:
            continue
        try:
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            calendars = service.calendarList().list().execute().get("items", [])
        except Exception:
            logger.error("%s のカレンダー一覧取得に失敗しました", account_name, exc_info=True)
            continue

        for cal in calendars:
            if cal["id"] not in excluded_ids:
                jobs.append((creds, cal["id"], account_name))
        # calendarList に含まれていないファミリーカレンダーを明示的に追加
        if account_name == "husband" and family_calendar_id:
            jobs.append((creds, family_calendar_id, "family"))

    return jobs


def fetch_today_events(tz_name: str = "Asia/Tokyo") -> list[CalendarEvent]:
    tz = ZoneInfo(tz_name)
    today = date.today()
    time_min = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=tz).isoformat()
    time_max = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=tz).isoformat()

    jobs = _build_jobs()

    # 各カレンダーのイベント取得を並列実行（per-calendar の往復がボトルネックのため）。
    # futures を投入順に走査するので、重複排除の優先順は jobs の順どおり決定的。
    seen_ids: set[str] = set()
    all_events: list[CalendarEvent] = []
    if jobs:
        with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as executor:
            futures = [
                executor.submit(_fetch_calendar_events, creds, cal_id, owner, time_min, time_max, tz)
                for creds, cal_id, owner in jobs
            ]
            for future in futures:
                for event in future.result():
                    if event.id not in seen_ids:
                        seen_ids.add(event.id)
                        all_events.append(event)

    all_events.sort(key=lambda e: (e.start_time is None, e.start_time or ""))
    return all_events


def _fetch_calendar_raw(
    creds: Credentials, cal_id: str, time_min: str, time_max: str,
) -> list[dict]:
    """単一カレンダーの生イベント(dict)を取得する。週間取得用（日付ごとの振り分けは呼び出し側）。"""
    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        result = service.events().list(
            calendarId=cal_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
    except Exception:
        logger.warning("カレンダー %s の取得をスキップ", cal_id, exc_info=True)
        return []
    return result.get("items", [])


def _event_window_dates(
    event: dict, tz: ZoneInfo, window_start: date, window_end: date,
) -> list[date]:
    """イベントが占有する日付のうち、ウィンドウ [window_start, window_end] 内のものを返す。

    時刻付きイベントは開始日のみ。終日イベントは複数日にまたがり得る
    （Google の end.date は排他的なので 1 日引いて最終日を求める）。
    """
    start = event.get("start", {})
    if "dateTime" in start:
        d = datetime.fromisoformat(start["dateTime"]).astimezone(tz).date()
        return [d] if window_start <= d <= window_end else []

    start_date_str = start.get("date")
    if not start_date_str:
        return []
    s = date.fromisoformat(start_date_str)
    end_date_str = event.get("end", {}).get("date")
    last = (date.fromisoformat(end_date_str) - timedelta(days=1)) if end_date_str else s

    cur = max(s, window_start)
    stop = min(last, window_end)
    out: list[date] = []
    while cur <= stop:
        out.append(cur)
        cur += timedelta(days=1)
    return out


def fetch_week_events(tz_name: str = "Asia/Tokyo", days: int = 7) -> dict[str, list[CalendarEvent]]:
    """今日から days 日間のイベントを日付(YYYY-MM-DD)ごとにまとめて返す。

    終日イベントはまたがる各日に複製される。重複排除は (日付, イベントID) 単位で行うため、
    複数日イベントが各日に1回ずつ残りつつ、同一日に同一イベントが二重表示されることはない。
    """
    tz = ZoneInfo(tz_name)
    today = date.today()
    window_start = today
    window_end = today + timedelta(days=days - 1)
    time_min = datetime(window_start.year, window_start.month, window_start.day, 0, 0, 0, tzinfo=tz).isoformat()
    time_max = datetime(window_end.year, window_end.month, window_end.day, 23, 59, 59, tzinfo=tz).isoformat()

    jobs = _build_jobs()
    grouped: dict[str, list[CalendarEvent]] = {
        (window_start + timedelta(days=i)).isoformat(): [] for i in range(days)
    }
    seen: set[tuple[str, str]] = set()  # (日付, イベントID)

    if jobs:
        with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as executor:
            futures = [
                executor.submit(_fetch_calendar_raw, creds, cal_id, time_min, time_max)
                for creds, cal_id, _ in jobs
            ]
            for (creds, cal_id, owner), future in zip(jobs, futures):
                for raw in future.result():
                    parsed = _parse_event(raw, owner, tz)
                    for d in _event_window_dates(raw, tz, window_start, window_end):
                        key = (d.isoformat(), parsed.id)
                        if key in seen:
                            continue
                        seen.add(key)
                        grouped[d.isoformat()].append(parsed)

    for events in grouped.values():
        events.sort(key=lambda e: (e.start_time is None, e.start_time or ""))
    return grouped
