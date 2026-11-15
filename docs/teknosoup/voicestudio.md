# VoiceStudio adapter

## Configuration

Set these variables on the API and any worker that calls VoiceStudio:

| Variable | Default | Meaning |
|---|---|---|
| VOICESTUDIO_BASE_URL | http://host.docker.internal:3900 | Base URL reachable from the container |
| VOICESTUDIO_TTS_ENABLED | false | Enable speech generation |
| VOICESTUDIO_STT_ENABLED | false | Enable transcription |
| VOICESTUDIO_TIMEOUT_SECONDS | 30 | Per-request HTTP timeout |

For Docker Desktop on macOS, host.docker.internal resolves to the host. VoiceStudio must listen on an interface reachable from Docker and be allowed by the macOS firewall. For Linux Docker Engine, add host-gateway mapping if needed.

## Implemented adapter operations

- GET /health
- GET /profiles
- POST /v1/audio/speech (WAV only)
- POST /transcribe (fast, accurate or reference mode)

The adapter deliberately does not retry speech-generation requests after ambiguous network failures because the provider may already have completed synthesis. Persistence, job scheduling, manifest updates and sentence-level idempotency belong to the TeknoSoup production service and worker layer, not this HTTP adapter.

## API endpoints

- GET /api/v1/teknosoup/voice-studio/health
- GET /api/v1/teknosoup/voice-studio/profiles

Both endpoints use the existing MoneyPrinterTurbo API-key dependency. The profile endpoint requires TTS to be enabled. The health endpoint reports the feature flags and provider reachability; it does not claim that every model is loaded or ready.
