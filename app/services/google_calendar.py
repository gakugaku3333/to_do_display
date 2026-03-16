import os
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.models import CalendarEvent

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKENS_DIR = "tokens"
CREDENTIALS_FILE = "credentials.json"

OWNER_COLORS = {
    "husband": "#4A90D9",
    "wife": "#E86A9A",
}

WEEKDAYS_JA = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]


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
    print(f"認証完了: {token_path} に保存しました。")


def _parse_event(event: dict, owner: str, tz: ZoneInfo) -> CalendarEvent:
    title = event.get("summary", "(タイトルなし)")
    start = event.get("start", {})
    end = event.get("end", {})

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
            color=OWNER_COLORS.get(owner, "#888888"),
        )
    else:
        return CalendarEvent(
            id=event["id"],
            title=title,
            start_time=None,
            end_time=None,
            is_all_day=True,
            owner=owner,
            color=OWNER_COLORS.get(owner, "#888888"),
        )


def fetch_today_events(tz_name: str = "Asia/Tokyo") -> list[CalendarEvent]:
    tz = ZoneInfo(tz_name)
    today = date.today()
    time_min = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=tz).isoformat()
    time_max = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=tz).isoformat()

    all_events: list[CalendarEvent] = []
    seen_ids: set[str] = set()

    for account_name in ("husband", "wife"):
        creds = get_credentials(account_name)
        if not creds:
            continue

        try:
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            calendars = service.calendarList().list().execute().get("items", [])

            for cal in calendars:
                cal_id = cal["id"]
                result = service.events().list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                ).execute()

                for event in result.get("items", []):
                    event_id = event["id"]
                    if event_id not in seen_ids:
                        seen_ids.add(event_id)
                        all_events.append(_parse_event(event, account_name, tz))
        except Exception as e:
            print(f"[Google Calendar] {account_name} の取得エラー: {e}")

    all_events.sort(key=lambda e: (e.start_time is None, e.start_time or ""))
    return all_events
