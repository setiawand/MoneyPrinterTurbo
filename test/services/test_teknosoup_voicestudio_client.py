from unittest.mock import Mock

import pytest
import requests

from app.integrations.voicestudio.client import (
    VoiceStudioClient,
    VoiceStudioError,
    VoiceStudioSettings,
)


def client_with_response(response):
    session = Mock()
    session.request.return_value = response
    settings = VoiceStudioSettings(
        base_url="http://host.docker.internal:3900",
        tts_enabled=True,
        stt_enabled=True,
        timeout_seconds=12,
    )
    return VoiceStudioClient(settings, session), session


def test_synthesize_requests_wav_and_returns_binary_payload():
    response = Mock()
    response.content = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"audio"
    client, session = client_with_response(response)

    audio = client.synthesize("Halo TeknoSoup", "profile-1", language="id")

    assert audio == response.content
    args, kwargs = session.request.call_args
    assert args == ("POST", "http://host.docker.internal:3900/v1/audio/speech")
    assert kwargs["json"]["input"] == "Halo TeknoSoup"
    assert kwargs["json"]["voice"] == "profile-1"
    assert kwargs["json"]["response_format"] == "wav"
    assert kwargs["timeout"] == 12


@pytest.mark.parametrize("text,voice", [("", "voice"), ("hello", "")])
def test_synthesize_rejects_empty_text_or_voice(text, voice):
    client, session = client_with_response(Mock())
    with pytest.raises(ValueError):
        client.synthesize(text, voice)
    session.request.assert_not_called()


def test_synthesize_rejects_non_wav_response():
    response = Mock()
    response.content = b"not a wav file"
    client, _ = client_with_response(response)
    with pytest.raises(VoiceStudioError, match="valid WAV"):
        client.synthesize("hello", "voice")


def test_synthesize_does_not_retry_ambiguous_timeout():
    session = Mock()
    session.request.side_effect = requests.ReadTimeout("response lost")
    settings = VoiceStudioSettings(tts_enabled=True)
    client = VoiceStudioClient(settings, session)

    with pytest.raises(VoiceStudioError):
        client.synthesize("hello", "voice")

    assert session.request.call_count == 1


def test_transcribe_returns_documented_text_payload(tmp_path):
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"audio")
    response = Mock()
    response.json.return_value = {"text": "Halo", "language": "id", "segments": []}
    client, session = client_with_response(response)

    result = client.transcribe(str(audio), mode="accurate")

    assert result["text"] == "Halo"
    args, kwargs = session.request.call_args
    assert args[0] == "POST"
    assert args[1].endswith("/transcribe")
    assert kwargs["data"] == {"mode": "accurate"}
    assert "audio" in kwargs["files"]


def test_transcribe_rejects_unknown_mode(tmp_path):
    client, session = client_with_response(Mock())
    with pytest.raises(ValueError):
        client.transcribe(str(tmp_path / "missing.wav"), mode="invalid")
    session.request.assert_not_called()
