from __future__ import annotations

"""朝の音声ブリーフィング用テキストを組み立てる。

iOS ショートカットの「テキストを読み上げる」アクションに渡す前提なので、
絵文字や記号は読み上げが不自然になるため使わず、自然な日本語の平文を返す。
"""

from datetime import date

from app.models import TodayData, WeatherData


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
    weekday = [t.title for t in data.flow_tasks if t.task_type == "weekly"]

    if not weekday:
        return "今日のやることはありません。"

    return f"今日のやることは、{'、'.join(weekday)}、以上です。"


def build_briefing_text(data: TodayData) -> str:
    """TodayData から朝の読み上げ用テキストを組み立てる。"""
    parts = [
        "おはようございます。",
        _date_phrase(data),
        _weather_phrase(data.weather),
        _events_phrase(data),
        _tasks_phrase(data),
        "今日も良い一日を。",
    ]
    return "\n".join(parts)
