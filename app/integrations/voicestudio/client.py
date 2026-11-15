"""Small, synchronous client for the local VoiceStudio REST API.

Speech generation is deliberately not retried: a timed-out request may already
have produced an audio asset on the provider side.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests


class VoiceStudioError(RuntimeError):
    """A VoiceStudio request failed or returned an invalid response."""


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class VoiceStudioSettings:
    base_url: str = "http://host.docker.internal:3900"
    tts_enabled: bool = False
    stt_enabled: bool = False
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "VoiceStudioSettings":
        raw_timeout = os.getenv("VOICESTUDIO_TIMEOUT_SECONDS", "30")
        try:
            timeout = float(raw_timeout)
        except ValueError as exc:
            raise ValueError("VOICESTUDIO_TIMEOUT_SECONDS must be numeric") from exc
        if timeout <= 0:
            raise ValueError("VOICESTUDIO_TIMEOUT_SECONDS must be greater than zero")
        return cls(
            base_url=os.getenv(
                "VOICESTUDIO_BASE_URL", "http://host.docker.internal:3900"
            ).rstrip("/"),
            tts_enabled=_env_bool("VOICESTUDIO_TTS_ENABLED", False),
            stt_enabled=_env_bool("VOICESTUDIO_STT_ENABLED", False),
            timeout_seconds=timeout,
        )


class VoiceStudioClient:
    """VoiceStudio HTTP adapter; callers own persistence and job scheduling."""

    def __init__(
        self,
        settings: VoiceStudioSettings | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.settings = settings or VoiceStudioSettings.from_env()
        self.session = session or requests.Session()

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        try:
            response = self.session.request(
                method,
                f"{self.settings.base_url}/{path.lstrip('/')}",
                timeout=self.settings.timeout_seconds,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise VoiceStudioError(f"VoiceStudio request failed: {exc}") from exc

    def health(self) -> dict[str, Any]:
        response = self._request("GET", "/health")
        try:
            payload = response.json()
        except ValueError as exc:
            raise VoiceStudioError("VoiceStudio health endpoint returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise VoiceStudioError("VoiceStudio health response must be a JSON object")
        return payload

    def profiles(self) -> Any:
        response = self._request("GET", "/profiles")
        try:
            return response.json()
        except ValueError as exc:
            raise VoiceStudioError("VoiceStudio profiles endpoint returned invalid JSON") from exc

    def synthesize(
        self,
        text: str,
        voice: str,
        *,
        model: str = "omnivoice",
        language: str = "id",
        speed: float = 1.0,
        instructions: str | None = None,
    ) -> bytes:
        if not text.strip():
            raise ValueError("text must not be empty")
        if not voice.strip():
            raise ValueError("voice must not be empty")
        if not 0.25 <= speed <= 4.0:
            raise ValueError("speed must be between 0.25 and 4.0")
        payload: dict[str, Any] = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": "wav",
            "language": language,
            "speed": speed,
        }
        if instructions:
            payload["instructions"] = instructions
        response = self._request("POST", "/v1/audio/speech", json=payload)
        audio = response.content
        if len(audio) < 12 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
            raise VoiceStudioError("VoiceStudio did not return a valid WAV payload")
        return audio

    def transcribe(self, audio_path: str, *, mode: str = "accurate") -> dict[str, Any]:
        if mode not in {"fast", "accurate", "reference"}:
            raise ValueError("mode must be fast, accurate, or reference")
        try:
            with open(audio_path, "rb") as audio_file:
                response = self._request(
                    "POST",
                    "/transcribe",
                    data={"mode": mode},
                    files={"audio": (os.path.basename(audio_path), audio_file)},
                )
        except OSError as exc:
            raise VoiceStudioError(f"Unable to read audio file: {exc}") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise VoiceStudioError("VoiceStudio transcription returned invalid JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            raise VoiceStudioError("VoiceStudio transcription response is missing text")
        return payload
