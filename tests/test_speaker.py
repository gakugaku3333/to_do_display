from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services import speaker


def _fake_say(args, **kwargs):
    out = args[args.index("-o") + 1]
    with open(out, "wb") as f:
        f.write(b"RIFF")


def test_synthesize_serves_only_latest(tmp_path, monkeypatch):
    monkeypatch.setattr(speaker, "AUDIO_DIR", tmp_path)
    with patch("subprocess.run", side_effect=_fake_say):
        first = speaker.synthesize("一回目")
        second = speaker.synthesize("二回目")
    assert speaker.get_audio_path(first) is None
    assert speaker.get_audio_path(second).exists()
    assert speaker.get_audio_path("guess") is None


def test_speak_builds_url_and_casts(tmp_path, monkeypatch):
    monkeypatch.setattr(speaker, "AUDIO_DIR", tmp_path)
    monkeypatch.setattr(speaker.settings, "google_home_name", "リビング")
    monkeypatch.setattr(speaker.settings, "public_base_url", "http://mac.local:8080/")
    with patch("subprocess.run", side_effect=_fake_say), \
         patch.object(speaker, "cast_audio") as cast:
        speaker.speak("おはようございます")
    url, name, volume = cast.call_args.args
    assert url.startswith("http://mac.local:8080/api/briefing/audio/")
    assert url.endswith(".wav")
    assert name == "リビング"
    assert volume is None


def test_speak_requires_device_name(monkeypatch):
    monkeypatch.setattr(speaker.settings, "google_home_name", "")
    with pytest.raises(RuntimeError):
        speaker.speak("x")


@pytest.mark.asyncio
async def test_audio_endpoint(client, tmp_path, monkeypatch):
    monkeypatch.setattr(speaker, "AUDIO_DIR", tmp_path)
    with patch("subprocess.run", side_effect=_fake_say):
        nonce = speaker.synthesize("テスト")
    r = await client.get(f"/api/briefing/audio/{nonce}.wav")
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert (await client.get("/api/briefing/audio/wrong.wav")).status_code == 404
