# Grandpa Assistant Release Notes

Date: 04 April 2026  
Branch: `main`  
Release: `v1.0.0`

## Status

Grandpa Assistant is in a release-ready local state.

## Release Scope

- Stable local AI assistant flow is complete.
- Release readiness checks now pass with `11 ready, 0 warning, 0 error`.
- Desktop portable build, Piper TTS, hardware-aware backend, and local Smart Home demo mode are all verified.

## Key Changes Included

- Offline Ollama routing for general, fast, and coding prompts.
- Hardware detection for storage, microphones, cameras, USB, and local network devices.
- Piper TTS setup with a tested local voice model.
- Smart Home validation and local demo control flow.
- Final release checks, health checks, manifest export, and manual validation checklist.
- Portable Electron desktop build and launcher helpers.

## Validation Summary

Primary validation commands now pass:

- `scripts\windows\check_assistant_health.cmd`
- `scripts\windows\final_release_check.cmd`
- `scripts\windows\validate_iot_setup.cmd`
- `scripts\windows\setup_piper_voice.ps1`
- `cmd /c npm run desktop:build` (frontend)

## Current Desktop Artifact

- Expected artifact: `frontend\release\Grandpa Assistant 1.0.0.exe`
- Export manifest with: `scripts\windows\export_release_manifest.cmd`

## Final Real-World Checks

1. Run the manual checklist in `docs\REAL_WORLD_VALIDATION_CHECKLIST.md`.
2. Replace demo Smart Home URLs with your real local Home Assistant, MQTT, or webhook config if needed.
3. Confirm the desktop artifact starts on a second Windows machine.

## Notes

- The repo currently ships with a local Smart Home demo configuration for safe local testing.
- For real-device automation, replace the localhost demo URLs in your ignored `backend/data/iot_credentials.json`.
