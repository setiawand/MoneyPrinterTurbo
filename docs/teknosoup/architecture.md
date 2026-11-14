# TeknoSoupTV Production Platform Architecture

## Status
Proposed target architecture. This describes the implementation direction; it does not claim the listed services or modules already exist.

## Goals
Extend this MoneyPrinterTurbo fork into a long-form production workflow for TeknoSoupTV (initial target: 15–25 minute videos) while preserving the existing short-video workflow and engine contracts.

## Architectural decisions
1. Keep MoneyPrinterTurbo as the core FastAPI and media-processing codebase.
2. Use Next.js as the primary production dashboard. Keep Streamlit available during migration.
3. Integrate the local VoiceStudio REST API through a dedicated adapter. Docker Desktop for Mac default: http://host.docker.internal:3900.
4. Use PostgreSQL for production-domain metadata and Redis for asynchronous job coordination.
5. Store media binaries (sentence WAVs, images, footage, renders) on shared filesystem/object storage; store metadata, paths, hashes and status in PostgreSQL.
6. Keep voice generation sentence-granular and chapter-organized. A project uses one voice profile unless an explicit user-approved change is made.
7. Reuse immutable assets and render artifacts when dependency fingerprints have not changed.
8. Publishing is out of scope for initial milestones. No automatic publishing; export/release remains an explicit human approval.

## Logical components
- Next.js dashboard: projects, script editor/version history, Voice Studio, storyboard, media library, render review and settings.
- FastAPI API: authentication boundary, request validation, production-domain services and orchestration.
- MoneyPrinterTurbo core: existing script/video/audio/subtitle/task capabilities and FFmpeg-based media processing.
- VoiceStudio adapter: typed HTTP client, TTS, STT, profile discovery, timeout/retry policy and health checks.
- Workers: voice generation, asset processing and rendering. Long-running work must not execute inside request handlers.
- PostgreSQL: projects, script versions, chapters, sentences, voice assets, storyboards, scenes, media assets, revisions, render artifacts and job metadata.
- Redis: queue/task state and worker coordination, reusing the existing task manager where its contract fits.
- Media storage: shared persistent volume initially; object storage can be introduced behind a storage interface later.

## Production flow
1. Create project and choose long-form format, visual style and production settings.
2. Create/edit script; split it into chapters and stable sentence IDs; preserve script versions.
3. Generate sentence WAV files through VoiceStudio; persist a manifest with sentence ID, chapter, sequence, text, voice profile, script version, duration, file path, content hash and generation status.
4. Run STT-based quality checks and review selected sentences.
5. Build storyboard scenes and associate media assets and timing.
6. Render using existing media-processing capabilities through an adapter/worker.
7. Review preview, selectively regenerate changed dependencies, then export.
8. Publishing is not automatic and requires explicit approval.

## VoiceStudio integration contract
- Base URL is configurable with VOICESTUDIO_BASE_URL; Docker Desktop for Mac default: http://host.docker.internal:3900.
- Feature flags: VOICESTUDIO_TTS_ENABLED and VOICESTUDIO_STT_ENABLED.
- Preferred speech endpoint: POST /v1/audio/speech, WAV response format.
- Transcription endpoint: POST /transcribe (or OpenAI-compatible transcription endpoint where appropriate).
- Profile discovery: GET /profiles.
- Do not expose VoiceStudio credentials or internal host details to the browser.
- Health/readiness checks must distinguish API availability from model readiness.
- Add bounded timeouts, clear error mapping, and no blind retries for non-idempotent generation requests.

## Proposed repository layout
    app/
      integrations/voicestudio/
        client.py
        tts.py
        stt.py
        profiles.py
        schemas.py
      services/teknosoup/
        project_service.py
        script_service.py
        voice_producer.py
        voice_manifest.py
        storyboard_service.py
        asset_service.py
        production_service.py
      controllers/v1/teknosoup/
        projects.py
        scripts.py
        chapters.py
        voices.py
        storyboards.py
        assets.py
        renders.py
      workers/
        voice_worker.py
        asset_worker.py
        render_worker.py
    frontend/
      app/
      components/
      features/
      lib/
    migrations/

This is a target layout, not a requirement to create every module in the first change. Existing module names and patterns must be inspected before adding or moving code.

## API namespace
Use /api/v1/teknosoup for new production-domain endpoints. Initial resources:
- /projects
- /projects/{project_id}/scripts
- /projects/{project_id}/chapters
- /projects/{project_id}/voices
- /projects/{project_id}/storyboards
- /projects/{project_id}/assets
- /projects/{project_id}/renders

Use the repository's existing API response and authentication conventions; do not silently change existing /api/v1 contracts.

## Data and revision rules
- Stable IDs for chapters, sentences and scenes must survive text edits where possible.
- A sentence asset is reusable only when normalized spoken text, voice profile, synthesis parameters and relevant pronunciation rules match.
- Keep original script text separately from spoken/normalized text.
- Regeneration is scoped to changed sentence IDs.
- Scene/render cache keys include all relevant upstream dependency fingerprints.
- File writes are atomic; manifest/database state must not claim success before the audio artifact is durably written and validated.
- Track generation and render attempts, errors and timestamps.

## Deployment
Docker Compose target services: frontend, existing api, voice-worker, asset-worker, render-worker, redis, postgres, plus a shared persistent media volume. VoiceStudio remains external on the Mac host during local development.

Do not introduce Kubernetes or a new queue framework in the first milestone. Reuse Redis/task infrastructure first, then split workers behind explicit job contracts.

## Security and operations
- Keep API keys and VoiceStudio configuration server-side.
- Restrict CORS to the dashboard origin.
- Do not expose PostgreSQL or Redis publicly.
- Add health checks, structured job events, bounded concurrency and storage retention policies.
- Validate media paths against the configured storage root.
- Require human approval before any future publishing integration.

## Non-goals for the first release
- Automatic publishing to YouTube or social platforms.
- Analytics ingestion.
- Multi-voice dialogue production.
- Kubernetes deployment.
- Replacing the existing MoneyPrinterTurbo renderer before proving an adapter-based integration.
