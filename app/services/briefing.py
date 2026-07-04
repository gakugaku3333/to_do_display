from __future__ import annotations

"""朝の音声ブリーフィング用テキストを組み立てる。

iOS ショートカットの「テキストを読み上げる」アクションに渡す前提なので、
絵文字や記号は読み上げが不自然になるため使わず、自然な日本語の平文を返す。
"""

from datetime import date

from app.models import TodayData, WeatherData
from app.services.google_calendar import get_token_status


def _date_phrase(data: TodayData) -> str:
    """「6月16日、月曜日です」。祝日なら祝日名も添える。"""
    d = date.fromisoformat(data.date)
    base = f"今日は{d.month}月{d.day}日、{data.weekday}です。"
    if data.is_holiday and data.holiday_name:
        base += f"今日は{data.holiday_name}でお休みです。"
    return base


def _weather_phrase(w: WeatherData | None) -> str:
    if w is None:
        return "天気予報は取得できませんでした。"

    parts = [f"天気は{w.condition}。"]

    if w.temp_max is not None:
        s = f"最高気温は{w.temp_max}度"
        if w.temp_max_delta:
            direction = "高く" if w.temp_max_delta > 0 else "低く"
            s += f"、昨日より{abs(w.temp_max_delta)}度{direction}なります"
        parts.append(s + "。")
    if w.temp_min is not None:
        parts.append(f"最低気温は{w.temp_min}度です。")

    # 降水確率は最大値で「傘が要るか」を端的に伝える
    if w.hourly_precip:
        max_pop = max(h.precip_prob for h in w.hourly_precip)
        if max_pop >= 50:
            parts.append(f"降水確率は最大{max_pop}パーセント。傘を持って行きましょう。")
        elif max_pop >= 30:
            parts.append(f"降水確率は最大{max_pop}パーセントです。")

    return "".join(parts)


def _trash_phrase(data: TodayData) -> str | None:
    if not data.trash_labels:
        return None
    return f"今日のゴミ出しは、{'、'.join(data.trash_labels)}です。"


def _events_phrase(data: TodayData) -> str:
    events = data.events
    if not events:
        return "今日の予定はありません。"

    # 終日 → 時刻ありの順、時刻ありは時間順に並べる
    timed = sorted((e for e in events if not e.is_all_day and e.start_time),
                   key=lambda e: e.start_time or "")
    all_day = [e for e in events if e.is_all_day or not e.start_time]

    lines = [f"今日の予定は{len(events)}件です。"]
    for e in all_day:
        lines.append(f"終日、{e.title}。")
    for e in timed:
        h, m = e.start_time.split(":")
        when = f"{int(h)}時" + (f"{int(m)}分" if int(m) else "")
        lines.append(f"{when}、{e.title}。")
    return "".join(lines)


def _tasks_phrase(data: TodayData) -> str:
    # flow_tasks には曜日タスク（task_type=="weekly"）も合流済み。
    # 曜日ごとのタスクは別立てで読み上げる。
    weekday = [t.title for t in data.flow_tasks if t.task_type == "weekly"]
    todo = [t.title for t in data.flow_tasks if t.task_type != "weekly"]
    todo += [t.title for t in data.stock_tasks]

    if not weekday and not todo:
        return "今日のやることはありません。"

    parts: list[str] = []
    if todo:
        parts.append(f"今日のやることは、{'、'.join(todo)}、以上です。")
    if weekday:
        parts.append(f"曜日ごとのやることは、{'、'.join(weekday)}、以上です。")
    return "".join(parts)


def _auth_warning_phrase() -> str | None:
    """Googleカレンダーの再認証が必要な場合、読み上げ用の警告文を返す。"""
    labels = {"husband": "夫", "wife": "妻"}
    needs_reauth = [
        labels[account]
        for account in ("husband", "wife")
        if (status := get_token_status(account))["configured"] and status["error"]
    ]
    if not needs_reauth:
        return None
    return f"{'と'.join(needs_reauth)}のカレンダー連携の再認証が必要です。"


def build_briefing_text(data: TodayData) -> str:
    """TodayData から朝の読み上げ用テキストを組み立てる。"""
    parts = [
        "おはようございます。",
        _date_phrase(data),
        _weather_phrase(data.weather),
    ]
    trash = _trash_phrase(data)
    if trash:
        parts.append(trash)
    parts.append(_events_phrase(data))
    parts.append(_tasks_phrase(data))
    auth_warning = _auth_warning_phrase()
    if auth_warning:
        parts.append(auth_warning)
    parts.append("今日も良い一日を。")
    return "\n".join(parts)
