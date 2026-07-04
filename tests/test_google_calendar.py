from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from app.services import google_calendar


def _make_service(calendar_items: list[dict]) -> MagicMock:
    """calendarList と events().list() を備えたモックサービスを作る"""
    service = MagicMock()
    service.calendarList().list().execute.return_value = {"items": calendar_items}
    # どのカレンダーでも空のイベントを返す
    service.events().list().execute.return_value = {"items": []}
    return service


def test_excluded_calendar_is_not_requested():
    """EXCLUDED_CALENDAR_IDS のカレンダーは events().list に渡されない"""
    calendars = [
        {"id": "primary@example.com"},
        {"id": "excluded@univ.example"},
    ]
    service = _make_service(calendars)

    with patch.object(google_calendar.settings, "excluded_calendar_ids", "excluded@univ.example"), \
         patch.object(google_calendar.settings, "family_calendar_id", ""), \
         patch.object(google_calendar, "build", return_value=service), \
         patch.object(google_calendar, "get_credentials", lambda name: object() if name == "husband" else None):
        google_calendar.fetch_today_events()

    requested_ids = {
        call.kwargs.get("calendarId")
        for call in service.events().list.call_args_list
        if call.kwargs.get("calendarId")
    }
    assert "excluded@univ.example" not in requested_ids
    assert "primary@example.com" in requested_ids


def test_family_calendar_added_for_husband_when_configured():
    """family_calendar_id が設定されていれば husband 側に追加取得される"""
    service = _make_service([{"id": "primary@example.com"}])

    with patch.object(google_calendar.settings, "excluded_calendar_ids", ""), \
         patch.object(google_calendar.settings, "family_calendar_id", "fam@group.calendar.google.com"), \
         patch.object(google_calendar, "build", return_value=service), \
         patch.object(google_calendar, "get_credentials", lambda name: object() if name == "husband" else None):
        google_calendar.fetch_today_events()

    requested_ids = {
        call.kwargs.get("calendarId")
        for call in service.events().list.call_args_list
        if call.kwargs.get("calendarId")
    }
    assert "fam@group.calendar.google.com" in requested_ids


def test_duplicate_event_across_calendars_is_deduped():
    """複数カレンダーに同一IDのイベントが出ても1件に重複排除される"""
    service = MagicMock()
    service.calendarList().list().execute.return_value = {"items": [{"id": "primary@example.com"}]}
    # primary と family の両方で同じイベントIDを返す
    service.events().list().execute.return_value = {
        "items": [{
            "id": "dup-event",
            "summary": "共有予定",
            "start": {"dateTime": "2026-06-14T10:00:00+09:00"},
            "end": {"dateTime": "2026-06-14T11:00:00+09:00"},
        }],
    }

    with patch.object(google_calendar.settings, "excluded_calendar_ids", ""), \
         patch.object(google_calendar.settings, "family_calendar_id", "fam@group.calendar.google.com"), \
         patch.object(google_calendar, "build", return_value=service), \
         patch.object(google_calendar, "get_credentials", lambda name: object() if name == "husband" else None):
        events = google_calendar.fetch_today_events()

    assert [e.id for e in events] == ["dup-event"]


def test_event_color_id_overrides_owner_color():
    """イベントに colorId があれば所有者色より優先される"""
    service = MagicMock()
    service.calendarList().list().execute.return_value = {"items": [{"id": "primary@example.com"}]}
    service.events().list().execute.return_value = {
        "items": [
            {  # colorId 指定あり → パレット色
                "id": "ev-colored",
                "summary": "色付き",
                "colorId": "11",  # Tomato
                "start": {"dateTime": "2026-06-14T10:00:00+09:00"},
                "end": {"dateTime": "2026-06-14T11:00:00+09:00"},
            },
            {  # colorId なし → 所有者(husband)色
                "id": "ev-plain",
                "summary": "色なし",
                "start": {"dateTime": "2026-06-14T12:00:00+09:00"},
                "end": {"dateTime": "2026-06-14T13:00:00+09:00"},
            },
        ],
    }

    with patch.object(google_calendar.settings, "excluded_calendar_ids", ""), \
         patch.object(google_calendar.settings, "family_calendar_id", ""), \
         patch.object(google_calendar, "build", return_value=service), \
         patch.object(google_calendar, "get_credentials", lambda name: object() if name == "husband" else None):
        events = google_calendar.fetch_today_events()

    colors = {e.id: e.color for e in events}
    assert colors["ev-colored"] == google_calendar.EVENT_COLOR_MAP["11"]
    assert colors["ev-plain"] == google_calendar.OWNER_COLORS["husband"]


def test_week_events_grouped_by_date():
    """週間取得は各日付キーを持ち、時刻付きイベントが開始日に振り分けられる"""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    service = MagicMock()
    service.calendarList().list().execute.return_value = {"items": [{"id": "primary@example.com"}]}
    service.events().list().execute.return_value = {
        "items": [{
            "id": "ev-tomorrow",
            "summary": "明日の会議",
            "start": {"dateTime": f"{tomorrow.isoformat()}T09:00:00+09:00"},
            "end": {"dateTime": f"{tomorrow.isoformat()}T10:00:00+09:00"},
        }],
    }

    with patch.object(google_calendar.settings, "excluded_calendar_ids", ""), \
         patch.object(google_calendar.settings, "family_calendar_id", ""), \
         patch.object(google_calendar, "build", return_value=service), \
         patch.object(google_calendar, "get_credentials", lambda name: object() if name == "husband" else None):
        grouped = google_calendar.fetch_week_events(days=7)

    # 7日分すべてのキーが存在する
    assert len(grouped) == 7
    assert today.isoformat() in grouped
    # 明日のイベントは明日のキーにのみ入る
    assert [e.title for e in grouped[tomorrow.isoformat()]] == ["明日の会議"]
    assert grouped[today.isoformat()] == []


def test_week_all_day_event_spans_multiple_days():
    """終日の複数日イベントは各日に複製される（end.date は排他的）"""
    today = date.today()
    end_exclusive = today + timedelta(days=3)  # 今日〜2日後の3日間
    service = MagicMock()
    service.calendarList().list().execute.return_value = {"items": [{"id": "primary@example.com"}]}
    service.events().list().execute.return_value = {
        "items": [{
            "id": "ev-trip",
            "summary": "旅行",
            "start": {"date": today.isoformat()},
            "end": {"date": end_exclusive.isoformat()},
        }],
    }

    with patch.object(google_calendar.settings, "excluded_calendar_ids", ""), \
         patch.object(google_calendar.settings, "family_calendar_id", ""), \
         patch.object(google_calendar, "build", return_value=service), \
         patch.object(google_calendar, "get_credentials", lambda name: object() if name == "husband" else None):
        grouped = google_calendar.fetch_week_events(days=7)

    for offset in range(3):
        ds = (today + timedelta(days=offset)).isoformat()
        assert [e.title for e in grouped[ds]] == ["旅行"]
        assert grouped[ds][0].is_all_day is True
    # 4日目には含まれない
    assert grouped[(today + timedelta(days=3)).isoformat()] == []


def test_week_duplicate_event_deduped_per_day():
    """複数カレンダーに同一IDが出ても、同一日では1件に重複排除される"""
    today = date.today()
    service = MagicMock()
    service.calendarList().list().execute.return_value = {"items": [{"id": "primary@example.com"}]}
    service.events().list().execute.return_value = {
        "items": [{
            "id": "dup",
            "summary": "共有予定",
            "start": {"dateTime": f"{today.isoformat()}T08:00:00+09:00"},
            "end": {"dateTime": f"{today.isoformat()}T09:00:00+09:00"},
        }],
    }

    with patch.object(google_calendar.settings, "excluded_calendar_ids", ""), \
         patch.object(google_calendar.settings, "family_calendar_id", "fam@group.calendar.google.com"), \
         patch.object(google_calendar, "build", return_value=service), \
         patch.object(google_calendar, "get_credentials", lambda name: object() if name == "husband" else None):
        grouped = google_calendar.fetch_week_events(days=7)

    assert [e.id for e in grouped[today.isoformat()]] == ["dup"]


def test_family_calendar_skipped_when_unset():
    """family_calendar_id が空ならファミリーカレンダーは追加されない"""
    service = _make_service([{"id": "primary@example.com"}])

    with patch.object(google_calendar.settings, "excluded_calendar_ids", ""), \
         patch.object(google_calendar.settings, "family_calendar_id", ""), \
         patch.object(google_calendar, "build", return_value=service), \
         patch.object(google_calendar, "get_credentials", lambda name: object() if name == "husband" else None):
        google_calendar.fetch_today_events()

    requested_ids = {
        call.kwargs.get("calendarId")
        for call in service.events().list.call_args_list
        if call.kwargs.get("calendarId")
    }
    assert requested_ids == {"primary@example.com"}


def test_get_token_status_not_configured():
    with patch.object(google_calendar, "TOKENS_DIR", "/nonexistent-tokens-dir"):
        status = google_calendar.get_token_status("husband")
    assert status == {"configured": False, "valid": False, "age_days": None, "error": None}


def test_get_token_status_valid_token(tmp_path):
    token_path = tmp_path / "husband.json"
    token_path.write_text('{"dummy": true}')

    fake_creds = MagicMock(expired=False, valid=True)
    with patch.object(google_calendar, "TOKENS_DIR", str(tmp_path)), \
         patch.object(google_calendar.Credentials, "from_authorized_user_file", return_value=fake_creds):
        status = google_calendar.get_token_status("husband")

    assert status["configured"] is True
    assert status["valid"] is True
    assert status["error"] is None
    assert status["age_days"] is not None


def test_get_token_status_invalid_grant(tmp_path):
    token_path = tmp_path / "husband.json"
    token_path.write_text('{"dummy": true}')

    fake_creds = MagicMock(expired=True, refresh_token="rt")
    fake_creds.refresh.side_effect = Exception("invalid_grant: Token has been expired or revoked.")
    with patch.object(google_calendar, "TOKENS_DIR", str(tmp_path)), \
         patch.object(google_calendar.Credentials, "from_authorized_user_file", return_value=fake_creds):
        status = google_calendar.get_token_status("husband")

    assert status["configured"] is True
    assert status["valid"] is False
    assert status["error"] == "invalid_grant"


def test_fetch_countdown_events_filters_by_prefix_and_sorts():
    today = date.today()
    soon = today + timedelta(days=5)
    far = today + timedelta(days=30)
    service = MagicMock()
    service.calendarList().list().execute.return_value = {"items": [{"id": "primary@example.com"}]}
    service.events().list().execute.return_value = {"items": [
        {"id": "no-prefix", "summary": "普通の予定", "start": {"date": soon.isoformat()}},
        {"id": "far-event", "summary": "★遠足", "start": {"date": far.isoformat()}},
        {"id": "soon-event", "summary": "★運動会", "start": {"date": soon.isoformat()}},
    ]}

    with patch.object(google_calendar.settings, "excluded_calendar_ids", ""), \
         patch.object(google_calendar.settings, "family_calendar_id", ""), \
         patch.object(google_calendar, "build", return_value=service), \
         patch.object(google_calendar, "get_credentials", lambda name: object() if name == "husband" else None):
        results = google_calendar.fetch_countdown_events()

    assert [r["title"] for r in results] == ["運動会", "遠足"]
    assert results[0]["event_date"] == soon.isoformat()
    assert results[0]["days_until"] == 5
    assert results[1]["days_until"] == 30


def test_fetch_countdown_events_excludes_past_events():
    today = date.today()
    past = today - timedelta(days=3)
    service = MagicMock()
    service.calendarList().list().execute.return_value = {"items": [{"id": "primary@example.com"}]}
    service.events().list().execute.return_value = {"items": [
        {"id": "past-event", "summary": "★過去の予定", "start": {"date": past.isoformat()}},
    ]}

    with patch.object(google_calendar.settings, "excluded_calendar_ids", ""), \
         patch.object(google_calendar.settings, "family_calendar_id", ""), \
         patch.object(google_calendar, "build", return_value=service), \
         patch.object(google_calendar, "get_credentials", lambda name: object() if name == "husband" else None):
        results = google_calendar.fetch_countdown_events()

    assert results == []
