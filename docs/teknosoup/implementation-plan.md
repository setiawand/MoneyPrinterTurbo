# TeknoSoupTV Implementation Plan

## Delivery approach
Implement incrementally on feature/teknosoup-foundation. Preserve existing MoneyPrinterTurbo routes, Streamlit UI and short-video behavior. Each milestone should be independently reviewable and tested.

## M0 — Repository and contract audit
- [x] Confirm repository, default branch and write access.
- [x] Inspect root Docker Compose, dependency manifest, FastAPI router and existing video API conventions.
- [ ] Complete audit of task manager, renderer, voice service and storage before worker/database design.
- [ ] Record baseline test commands and run the test suite in a local checkout.

## M1 — Foundation
- [x] Add initial TeknoSoup package and register VoiceStudio routes without changing existing endpoints.
- [x] Define VoiceStudio URL, TTS/STT feature flags and request timeout through environment configuration. Media-root configuration remains open.
- [ ] Add PostgreSQL integration and migrations using the repository's established dependency/migration conventions (audit before choosing).
- [ ] Add project CRUD and project settings API.
- [ ] Scaffold Next.js dashboard with server-side API proxy; do not expose internal service URLs or keys.
- [ ] Extend Docker Compose with opt-in frontend and database services; preserve existing default behavior where practical.

Acceptance:
- Existing API and Streamlit entry points continue to start.
- New API router is registered and protected consistently with existing API routes.
- Project CRUD is covered by automated tests.
- Browser never receives VoiceStudio secrets or private service configuration.

## M2 — Script and Voice Producer
- [ ] Model script versions, chapters and stable sentence identifiers.
- [x] Implement initial VoiceStudio HTTP adapter, health/profile discovery, WAV synthesis and STT request methods. Worker orchestration and persistence remain open.
- [ ] Implement sentence-level WAV generation and validation.
- [ ] Persist voice manifest with chapter, sentence ID, sequence, source/spoken text, voice profile, script version, path, duration, content hash and status.
- [ ] Implement selective regeneration based on dependency fingerprint.
- [ ] Add STT-based QA using VoiceStudio transcription.
- [ ] Add UI for voice profile selection, sentence preview, regeneration and approval.

Acceptance:
- One voice profile is used consistently for a project unless explicitly changed.
- A changed sentence regenerates only its own audio asset.
- Unchanged sentence audio is reused.
- WAV artifacts are validated before manifest status becomes complete.
- Original text and spoken-normalized text are both retained.
- Tests cover provider errors, timeouts, invalid audio, retry behavior and selective regeneration.

## M3 — Storyboard and assets
- [ ] Model scenes and storyboard versions.
- [ ] Associate each scene with chapter/sentence timing and media assets.
- [ ] Implement asset upload/import and storage validation.
- [ ] Add storyboard and media library UI.

Acceptance:
- Scene IDs remain stable across unrelated edits.
- Asset references are validated and confined to the media storage root.
- Storyboard changes invalidate only dependent artifacts.

## M4 — Rendering, review and export
- [ ] Audit and wrap the existing revision-aware renderer; do not rewrite it.
- [ ] Implement render worker job contract and cancellation/status handling.
- [ ] Assemble narration, visuals, subtitles, music and transitions.
- [ ] Add preview, revision comparison and export UI.

Acceptance:
- A long-form project can render end-to-end.
- Unchanged upstream assets and scene artifacts are reused.
- Failed/cancelled jobs have recoverable, explicit states.
- Export does not trigger publishing.

## E2E acceptance scenario
Create a 15–25 minute cartoon-style video project about DNS with multiple chapters and scenes.
1. Generate and review the script.
2. Generate sentence WAVs for the selected voice profile.
3. Confirm manifest completeness and audio duration metadata.
4. Edit three sentences and regenerate only those three WAVs.
5. Change one scene and confirm unrelated voice assets and scene artifacts remain reusable.
6. Render and export a reviewable video.
7. Verify that no publishing action occurs without explicit approval.

## Engineering guardrails
- Do not modify main directly.
- Do not replace the existing task manager or introduce Celery in the first milestone without evidence from the audit.
- Do not perform long-running media work in FastAPI request handlers.
- Do not store media binaries in PostgreSQL.
- Do not make VoiceStudio a hard dependency for existing MoneyPrinterTurbo workflows; gate it behind configuration and feature flags.
- Add tests alongside each implementation slice.
- Keep publishing disabled until a separate approval workflow is designed and accepted.


## Current implementation slice
- Added architecture and implementation-plan documents.
- Added a feature-flagged VoiceStudio adapter and read-only health/profile API endpoints.
- Added adapter unit tests; they have not yet been executed in a local checkout.
- PostgreSQL, migrations, project CRUD, Next.js dashboard, dedicated workers, sentence manifest persistence and Docker Compose changes are not implemented yet.
