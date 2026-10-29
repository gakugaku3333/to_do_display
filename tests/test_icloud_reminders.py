import subprocess
import sys
from datetime import date
from unittest.mock import patch

import pytest

from app.services import icloud_reminders

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="Reminders 連携は macOS のみ")


def _done(stdout: str = "", returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


def test_set_reminder_completed_passes_args_and_timeout():
    with patch("subprocess.run", return_value=_done("ok")) as run:
        assert icloud_reminders.set_reminder_completed("x-apple-reminder://A", True, ["ストック"])
    args, kwargs = run.call_args
    assert args[0] == [
        "osascript", str(icloud_reminders._COMPLETE_SCRIPT_PATH),
        "x-apple-reminder://A", "true", "ストック",
    ]
    assert kwargs["timeout"] == 60


def test_set_reminder_completed_not_found():
    with patch("subprocess.run", return_value=_done("not_found")):
        assert icloud_reminders.set_reminder_completed("id", False) is False


def test_create_reminder_null_due_and_error_output():
    with patch("subprocess.run", return_value=_done("new-id")) as run:
        assert icloud_reminders.create_reminder("フロー", "t") == "new-id"
    assert run.call_args.args[0][-1] == "null"
    assert run.call_args.kwargs["timeout"] == 30

    with patch("subprocess.run", return_value=_done("error: boom")):
        assert icloud_reminders.create_reminder("フロー", "t") is None


def test_fetch_tasks_parses_and_filters(monkeypatch):
    today = date.today().isoformat()
    payload = f'[{{"id":"a","name":"今日","dueDate":"{today}","completed":false}},' \
              '{"id":"b","name":"完了","completed":true}]'
    with patch("subprocess.run", return_value=_done(payload)) as run:
        stock, flow = icloud_reminders.fetch_tasks()
    assert [t.id for t in stock] == ["a"]
    assert [t.id for t in flow] == ["a"]
    assert run.call_args.kwargs["timeout"] == icloud_reminders._OSASCRIPT_TIMEOUT


def test_fetch_timeout_returns_empty():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("osascript", 120)):
        assert icloud_reminders._fetch_reminders_from_list("ストック") == []
