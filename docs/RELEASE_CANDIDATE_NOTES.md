# Grandpa Assistant Backend Release Notes

Date: 04 April 2026
Branch: `main`
Release: `v1.0.0`

## Status

Grandpa Assistant is maintained as a Windows-first backend assistant.

## Release Scope

- Stable local AI assistant flow
- Backend API health and chat surfaces
- Hardware-aware backend services
- Piper/voice setup support
- Local Smart Home validation and demo-safe control flow
- Backend diagnostics and manual validation checklist

## Validation Summary

Primary backend validation commands:

- `python -m unittest discover -s tests -v`
- `python scripts\dev\startup_smoke_check.py`
- `scripts\windows\check_assistant_health.cmd`
- `scripts\windows\validate_iot_setup.cmd`
- `scripts\windows\setup_piper_voice.ps1`

## Final Real-World Checks

1. Run the manual checklist in `docs\REAL_WORLD_VALIDATION_CHECKLIST.md`.
2. Replace demo Smart Home URLs with your real local Home Assistant, MQTT, or webhook config if needed.
3. Confirm `python backend\desktop_backend_entry.py` starts on the target Windows machine.

## Notes

- Real-device automation should use ignored local config files.
- Runtime data remains under ignored local data paths.
