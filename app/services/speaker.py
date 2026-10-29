from __future__ import annotations

"""ブリーフィング音声を Google Home（Cast対応スピーカー）で再生する。

Gemini for Home には外部サーバーの任意テキストを読み上げさせる公開APIが無いため、
Mac mini から LAN 内の Cast プロトコルで「音声ファイルを再生させる」方式をとる。

- 音声合成: briefing.get_briefing_audio（macOS `say` → mp3、当日キャッシュ）を流用
- 配信:     音声を推測不能な URL で FastAPI から配信する（Cast は認証ヘッダー不可）
- 再生:     pychromecast で mDNS によりスピーカーを「名前」で探して再生させる

スピーカーの IP も Mac mini の IP も固定しない。スピーカーは名前で発見し、
Mac mini 側の URL は再生の直前に自分の LAN IP を検出して組み立てる。
"""

import logging
import secrets

from app.config import settings
from app.network import local_ip

logger = logging.getLogger(__name__)

# 最新の音声: (nonce, mp3バイト列)。公開のたびに古いものは捨てる。
_latest: tuple[str, bytes] | None = None


def publish_audio(audio: bytes) -> str:
    """音声を配信対象として登録し、URL 用の nonce を返す。"""
    global _latest
    nonce = secrets.token_urlsafe(16)
    _latest = (nonce, audio)
    return nonce


def get_published_audio(nonce: str) -> bytes | None:
    if _latest and secrets.compare_digest(_latest[0], nonce):
        return _latest[1]
    return None


def base_url() -> str:
    # Cast デバイスは .local 名を解決できないことがあるため、既定では
    # 再生のたびに現在の LAN IP を検出して使う（IP が変わっても追従する）。
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    return f"http://{local_ip()}:{settings.port}"


def audio_url(nonce: str) -> str:
    return f"{base_url()}/api/briefing/cast/{nonce}.mp3"


def cast_audio(url: str, device_name: str, volume: float | None = None) -> None:
    """LAN 内の Cast デバイスを名前で探し、音声 URL を再生させる（同期・to_thread で呼ぶ）。"""
    import pychromecast  # macOS 以外のテスト環境で import を強制しない

    casts, browser = pychromecast.get_listed_chromecasts(
        friendly_names=[device_name], timeout=15,
    )
    try:
        if not casts:
            raise RuntimeError(f"Google Home「{device_name}」が見つかりません")
        cast = casts[0]
        cast.wait(timeout=15)
        if volume is not None:
            cast.set_volume(volume)
        mc = cast.media_controller
        mc.play_media(url, "audio/mpeg", title="今日のブリーフィング")
        mc.block_until_active(timeout=15)
        logger.info("Google Home「%s」でブリーフィングを再生: %s", device_name, url)
    finally:
        browser.stop_discovery()


def play(audio: bytes) -> None:
    """音声を公開して Google Home で再生する（同期関数。to_thread で呼ぶ）。"""
    if not settings.google_home_name:
        raise RuntimeError("GOOGLE_HOME_NAME が未設定です")
    url = audio_url(publish_audio(audio))
    volume = settings.google_home_volume if settings.google_home_volume >= 0 else None
    cast_audio(url, settings.google_home_name, volume)
