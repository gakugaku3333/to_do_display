from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services import speaker


def test_publish_serves_only_latest():
    first = speaker.publish_audio(b"one")
    second = speaker.publish_audio(b"two")
    assert speaker.get_published_audio(first) is None
    assert speaker.get_published_audio(second) == b"two"
    assert speaker.get_published_audio("guess") is None


def test_play_builds_url_and_casts(monkeypatch):
    monkeypatch.setattr(speaker.settings, "google_home_name", "リビング")
    monkeypatch.setattr(speaker.settings, "public_base_url", "http://mac.local:8080/")
    monkeypatch.setattr(speaker.settings, "google_home_volume", -1.0)
    with patch.object(speaker, "cast_audio") as cast:
        speaker.play(b"mp3")
    url, name, volume = cast.call_args.args
    assert url.startswith("http://mac.local:8080/api/briefing/cast/")
    assert url.endswith(".mp3")
    assert name == "リビング"
    assert volume is None
    nonce = url.rsplit("/", 1)[1].removesuffix(".mp3")
    assert speaker.get_published_audio(nonce) == b"mp3"


def test_play_requires_device_name(monkeypatch):
    monkeypatch.setattr(speaker.settings, "google_home_name", "")
    with pytest.raises(RuntimeError):
        speaker.play(b"x")


@pytest.mark.asyncio
async def test_cast_audio_endpoint(client):
    nonce = speaker.publish_audio(b"mp3data")
    r = await client.get(f"/api/briefing/cast/{nonce}.mp3")
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/mpeg"
    assert r.content == b"mp3data"
    assert (await client.get("/api/briefing/cast/wrong.mp3")).status_code == 404
