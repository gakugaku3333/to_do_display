from __future__ import annotations

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
