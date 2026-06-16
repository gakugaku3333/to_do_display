from __future__ import annotations

import base64
import json
import logging
import re
from datetime import date

import google.generativeai as genai

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """この画像は学校からの配布物です。画像内の文字を読み取り、行事・提出物・イベントなどの予定情報をすべて抽出してください。

以下のJSON形式のみで返答してください（説明文・コードブロックは不要）:
{{
  "events": [
    {{
      "title": "行事名または提出物名",
      "date": "YYYY-MM-DD",
      "time_start": "HH:MM または null",
      "time_end": "HH:MM または null",
      "location": "場所 または null",
      "description": "備考 または null"
    }}
  ]
}}

今日の日付: {today}
「来週」「今月末」などの相対的な日付は今日の日付を基準にYYYY-MM-DD形式に変換してください。
予定が見つからない場合は events を空配列にしてください。"""


def analyze_image(image_bytes: bytes, mime_type: str, api_key: str) -> list[dict]:
    """画像をGeminiで解析してイベント候補リストを返す"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    today = date.today().isoformat()
    prompt = PROMPT_TEMPLATE.format(today=today)

    image_part = {
        "inline_data": {
            "mime_type": mime_type,
            "data": base64.b64encode(image_bytes).decode(),
        }
    }

    response = model.generate_content([prompt, image_part])
    text = response.text.strip()

    # コードブロックが含まれる場合は除去
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("```").strip()

    try:
        data = json.loads(text)
        return data.get("events", [])
    except json.JSONDecodeError:
        logger.warning("Gemini のレスポンスをJSONとして解析できませんでした: %s", text[:200])
        return []
