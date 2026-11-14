"""Read-only VoiceStudio connectivity and profile endpoints."""

from fastapi import Depends, HTTPException

from app.controllers import base
from app.controllers.v1.base import new_router
from app.integrations.voicestudio import (
    VoiceStudioClient,
    VoiceStudioError,
    VoiceStudioSettings,
)

router = new_router(dependencies=[Depends(base.verify_token)])
router.tags = ["TeknoSoup - VoiceStudio"]


@router.get("/teknosoup/voice-studio/health")
def voice_studio_health():
    settings = VoiceStudioSettings.from_env()
    if not settings.tts_enabled and not settings.stt_enabled:
        return {
            "enabled": False,
            "tts_enabled": False,
            "stt_enabled": False,
            "reachable": None,
        }
    try:
        health = VoiceStudioClient(settings).health()
    except VoiceStudioError as exc:
        raise HTTPException(status_code=503, detail="VoiceStudio is unavailable") from exc
    return {
        "enabled": True,
        "tts_enabled": settings.tts_enabled,
        "stt_enabled": settings.stt_enabled,
        "reachable": True,
        "provider": health,
    }


@router.get("/teknosoup/voice-studio/profiles")
def voice_studio_profiles():
    settings = VoiceStudioSettings.from_env()
    if not settings.tts_enabled:
        raise HTTPException(status_code=503, detail="VoiceStudio TTS is disabled")
    try:
        return {"profiles": VoiceStudioClient(settings).profiles()}
    except VoiceStudioError as exc:
        raise HTTPException(status_code=503, detail="Unable to load VoiceStudio profiles") from exc
