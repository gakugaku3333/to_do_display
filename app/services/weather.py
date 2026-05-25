from __future__ import annotations

import json
import logging
from datetime import date, datetime
from urllib.request import urlopen
from urllib.error import URLError
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_JST = ZoneInfo("Asia/Tokyo")
_API_TIMEOUT = 10

# 気象庁 API 設定（福岡県）
_PREF_CODE = "400000"
_AREA_WEATHER = "筑後地方"   # 久留米が含まれる地方（天気・降水確率）
_AREA_TEMP    = "久留米"      # 気温データの都市

# 気象庁天気コード → (絵文字, 日本語)
_JMA_CODE_MAP: dict[str, tuple[str, str]] = {
    "100": ("☀",  "晴れ"),
    "101": ("🌤", "晴れ時々くもり"),
    "102": ("🌦", "晴れ一時雨"),
    "103": ("🌦", "晴れ時々雨"),
    "104": ("🌨", "晴れ一時雪"),
    "105": ("🌨", "晴れ時々雪"),
    "110": ("🌤", "晴れのちくもり"),
    "111": ("🌦", "晴れのち雨"),
    "112": ("🌨", "晴れのち雪"),
    "200": ("☁",  "くもり"),
    "201": ("🌤", "くもり時々晴れ"),
    "202": ("🌧", "くもり一時雨"),
    "203": ("🌧", "くもり時々雨"),
    "204": ("🌨", "くもり一時雪"),
    "205": ("🌨", "くもり時々雪"),
    "206": ("🌧", "くもり一時雨か雪"),
    "207": ("🌦", "くもり時々雨か雪"),
    "210": ("🌤", "くもりのち晴れ"),
    "211": ("🌧", "くもりのち雨"),
    "212": ("🌨", "くもりのち雪"),
    "213": ("🌧", "くもりのち雨か雪"),
    "214": ("🌧", "くもりのち雨"),
    "218": ("🌧", "くもりのち雨か雪"),
    "270": ("🌧", "雪か雨"),
    "300": ("🌧", "雨"),
    "301": ("🌦", "雨時々晴れ"),
    "302": ("🌧", "雨一時雪"),
    "303": ("🌧", "雨時々雪"),
    "306": ("🌧", "大雨"),
    "308": ("⛈", "雷を伴う大雨"),
    "309": ("⛈", "雷雨"),
    "311": ("🌤", "雨のち晴れ"),
    "313": ("☁",  "雨のちくもり"),
    "314": ("🌨", "雨のち雪"),
    "400": ("❄",  "雪"),
    "401": ("🌨", "雪時々晴れ"),
    "402": ("🌧", "雪一時雨"),
    "403": ("🌧", "雪時々雨"),
    "406": ("❄",  "大雪"),
    "411": ("🌤", "雪のち晴れ"),
    "413": ("☁",  "雪のちくもり"),
    "414": ("🌧", "雪のち雨"),
    "500": ("⛈", "大雨"),
    "501": ("⛈", "大雨・雷雨"),
}


def fetch_weather() -> dict | None:
    """気象庁 API で久留米市（筑後地方）の今日の天気予報を取得する"""
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{_PREF_CODE}.json"
    try:
        with urlopen(url, timeout=_API_TIMEOUT) as resp:
            data = json.loads(resp.read())
    except (URLError, json.JSONDecodeError):
        logger.error("気象庁APIへの接続に失敗しました", exc_info=True)
        return None

    try:
        today = date.today()
        ts = data[0]["timeSeries"]

        # ── 天気コード (timeSeries[0]) ──────────────────────────────
        weather_ts = ts[0]
        area_w = next(
            (a for a in weather_ts["areas"] if a["area"]["name"] == _AREA_WEATHER),
            None,
        )
        if area_w is None:
            logger.error("筑後地方のデータが見つかりません")
            return None

        code = area_w["weatherCodes"][0]
        emoji, condition = _JMA_CODE_MAP.get(code, ("🌡", area_w["weathers"][0].replace("　", "")))

        # ── 降水確率 6時間ブロック (timeSeries[1]) ───────────────────
        pop_ts = ts[1]
        area_p = next(
            (a for a in pop_ts["areas"] if a["area"]["name"] == _AREA_WEATHER),
            None,
        )
        hourly_precip: list[dict] = []
        if area_p:
            tomorrow = date.fromordinal(today.toordinal() + 1)
            for time_str, pop_str in zip(pop_ts["timeDefines"], area_p.get("pops", [])):
                if not pop_str:
                    continue
                dt = datetime.fromisoformat(time_str).astimezone(_JST)
                if dt.date() == today:
                    label = f"〜{dt.hour}時"
                elif dt.date() == tomorrow and dt.hour == 0:
                    label = "〜翌0時"
                else:
                    continue  # 翌日以降のデータは不要
                hourly_precip.append({"label": label, "precip_prob": int(pop_str)})

        # ── 気温（timeSeries[2]）久留米 ───────────────────────────────
        temp_ts = ts[2]
        area_t = next(
            (a for a in temp_ts["areas"] if a["area"]["name"] == _AREA_TEMP),
            None,
        )
        temp_max = temp_min = None
        if area_t:
            for time_str, temp_str in zip(temp_ts["timeDefines"], area_t.get("temps", [])):
                if not temp_str:
                    continue
                dt = datetime.fromisoformat(time_str).astimezone(_JST)
                if dt.date() == today and dt.hour == 9 and temp_max is None:
                    temp_max = int(temp_str)   # 今日の最高気温
                elif dt.date() > today and dt.hour == 0 and temp_min is None:
                    temp_min = int(temp_str)   # 今夜の最低気温

        logger.info(
            "天気取得完了（気象庁）: %s %s°/%s°",
            condition,
            temp_max if temp_max is not None else "--",
            temp_min if temp_min is not None else "--",
        )
        return {
            "condition": condition,
            "condition_emoji": emoji,
            "temp_max": temp_max,
            "temp_min": temp_min,
            "hourly_precip": hourly_precip,
        }

    except (KeyError, IndexError, ValueError, StopIteration):
        logger.error("気象庁APIのレスポンス解析に失敗しました", exc_info=True)
        return None
