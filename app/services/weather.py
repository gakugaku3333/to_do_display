from __future__ import annotations

import json
import logging
from urllib.request import urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)

_KURUME_LAT = 33.3194
_KURUME_LON = 130.5081
_API_TIMEOUT = 10

# WMO 天気コード → (絵文字, 日本語)
_WMO_MAP: dict[int, tuple[str, str]] = {
    0:  ("☀",  "快晴"),
    1:  ("🌤", "晴れ"),
    2:  ("⛅", "晴れのちくもり"),
    3:  ("☁",  "くもり"),
    45: ("🌫", "霧"),
    48: ("🌫", "氷霧"),
    51: ("🌦", "小雨"),
    53: ("🌦", "霧雨"),
    55: ("🌧", "雨"),
    61: ("🌧", "雨"),
    63: ("🌧", "雨"),
    65: ("🌧", "大雨"),
    71: ("❄",  "雪"),
    73: ("❄",  "雪"),
    75: ("❄",  "大雪"),
    77: ("❄",  "あられ"),
    80: ("🌦", "にわか雨"),
    81: ("🌦", "にわか雨"),
    82: ("🌧", "強いにわか雨"),
    85: ("❄",  "にわか雪"),
    86: ("❄",  "にわか雪"),
    95: ("⛈", "雷雨"),
    96: ("⛈", "雷雨"),
    99: ("⛈", "激しい雷雨"),
}

# ダッシュボードで表示する時刻（時間ごとの降水確率）
_SHOW_HOURS = [6, 9, 12, 15, 18, 21]


def fetch_weather() -> dict | None:
    """Open-Meteo API で久留米市の今日の天気予報を取得する"""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={_KURUME_LAT}&longitude={_KURUME_LON}"
        f"&daily=weathercode,temperature_2m_max,temperature_2m_min"
        f"&hourly=precipitation_probability"
        f"&timezone=Asia%2FTokyo&forecast_days=1"
    )
    try:
        with urlopen(url, timeout=_API_TIMEOUT) as resp:
            data = json.loads(resp.read())

        wmo = data["daily"]["weathercode"][0]
        emoji, condition = _WMO_MAP.get(wmo, ("🌡", "不明"))
        temp_max = round(data["daily"]["temperature_2m_max"][0])
        temp_min = round(data["daily"]["temperature_2m_min"][0])

        hourly_times = data["hourly"]["time"]
        hourly_precip = data["hourly"]["precipitation_probability"]

        time_to_prob: dict[int, int] = {}
        for i, t in enumerate(hourly_times):
            hour = int(t.split("T")[1].split(":")[0])
            time_to_prob[hour] = hourly_precip[i]

        hourly = [
            {"hour": h, "precip_prob": time_to_prob.get(h, 0)}
            for h in _SHOW_HOURS
        ]

        logger.info("天気取得完了: %s %d°/%d°", condition, temp_max, temp_min)
        return {
            "condition": condition,
            "condition_emoji": emoji,
            "temp_max": temp_max,
            "temp_min": temp_min,
            "hourly_precip": hourly,
        }

    except (URLError, KeyError, IndexError, json.JSONDecodeError):
        logger.error("天気情報の取得に失敗しました", exc_info=True)
        return None
