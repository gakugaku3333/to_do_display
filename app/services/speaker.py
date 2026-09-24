from __future__ import annotations

"""ブリーフィング音声を生成し、Google Home（Cast対応スピーカー）で再生する。

Gemini for Home には外部サーバーの任意テキストを読み上げさせる公開APIが無いため、
Mac mini から LAN 内の Cast プロトコルで「音声ファイルを再生させる」方式をとる。

- 音声合成: macOS 標準の `say`（日本語音声 Kyoko 等）で WAV を生成。外部サービス不要。
- 配信:     生成した WAV を推測不能な URL で FastAPI から配信する。
- 再生:     pychromecast で mDNS によりスピーカーを「名前」で探して再生させる。

スピーカーの IP も Mac mini の IP も固定しない。スピーカーは名前で発見し、
Mac mini 側の URL は再生の直前に自分の LAN IP を検出して組み立てる。
"""

import logging
import secrets
import socket
import subprocess
import tempfile
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

AUDIO_DIR = Path(tempfile.gettempdir()) / "family_dashboard_briefing"

# 最新の音声ファイル: nonce -> パス。古いものは生成のたびに捨てる。
_latest: tuple[str, Path] | None = None


def synthesize(text: str) -> str:
    """テキストを WAV に変換し、配信用の nonce を返す。"""
    global _latest
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    nonce = secrets.token_urlsafe(16)
    path = AUDIO_DIR / f"{nonce}.wav"
    # 16bit PCM WAV は Cast のデフォルトレシーバーで確実に再生できる
    subprocess.run(
        ["say", "-v", settings.tts_voice, "--file-format=WAVE",
         "--data-format=LEI16@24000", "-o", str(path), text],
        check=True, timeout=60,
    )
    if _latest and _latest[1] != path:
        _latest[1].unlink(missing_ok=True)
    _latest = (nonce, path)
    return nonce


def get_audio_path(nonce: str) -> Path | None:
    if _latest and secrets.compare_digest(_latest[0], nonce) and _latest[1].exists():
        return _latest[1]
    return None


def local_ip() -> str:
    """Google Home から到達できる自分の LAN IP を検出する（パケットは送信しない）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def base_url() -> str:
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    return f"http://{local_ip()}:{settings.port}"


def cast_audio(url: str, device_name: str, volume: float | None = None) -> None:
    """LAN 内の Cast デバイスを名前で探し、音声 URL を再生させる。"""
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
        mc.play_media(url, "audio/wav", title="今日のブリーフィング")
        mc.block_until_active(timeout=15)
        logger.info("Google Home「%s」でブリーフィングを再生: %s", device_name, url)
    finally:
        browser.stop_discovery()


def speak(text: str) -> None:
    """テキストを合成して Google Home で再生する（同期関数。to_thread で呼ぶ）。"""
    if not settings.google_home_name:
        raise RuntimeError("GOOGLE_HOME_NAME が未設定です")
    nonce = synthesize(text)
    url = f"{base_url()}/api/briefing/audio/{nonce}.wav"
    volume = settings.google_home_volume if settings.google_home_volume >= 0 else None
    cast_audio(url, settings.google_home_name, volume)
