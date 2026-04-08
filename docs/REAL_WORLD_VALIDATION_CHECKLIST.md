# Real-World Validation Checklist

Date: 04 April 2026

Use this checklist after the build is complete and the assistant is running on the target Windows machine.

## Core Startup

- [ ] Run `scripts\windows\final_release_check.cmd`
- [ ] Confirm startup doctor reports `0 warning, 0 error`
- [ ] Confirm desktop artifact exists in `frontend\release`
- [ ] Launch the desktop app and confirm the dashboard loads

## Voice

- [ ] Say the wake word and confirm the assistant wakes up
- [ ] Ask a short general question and confirm speech output works
- [ ] Say `stop` while it is speaking and confirm interruption works
- [ ] Check `tts backend status` and confirm Piper is active

## Hardware Events

- [ ] Run `scripts\windows\watch_hardware_changes.cmd`
- [ ] Insert a pendrive and confirm a `storage` connected event appears
- [ ] Remove the pendrive and confirm a disconnect event appears
- [ ] Connect or disconnect a microphone/headset and confirm event detection
- [ ] If available, connect a webcam and confirm camera detection

## Local AI

- [ ] Run `ollama list` and confirm required models are installed
- [ ] Send a general prompt and confirm it routes to `mistral:7b`
- [ ] Send a coding prompt and confirm it routes to `deepseek-coder:6.7b`
- [ ] Send a fast/simple prompt and confirm it can use `phi3:mini`

## Smart Home

- [ ] Run `scripts\windows\validate_iot_setup.cmd`
- [ ] Ask `iot status` and confirm Smart Home is enabled
- [ ] Trigger one safe Smart Home command and confirm success
- [ ] If using real Home Assistant or MQTT, verify one real device action

## Release Readiness

- [ ] Run `scripts\windows\export_release_manifest.cmd`
- [ ] Save the SHA256 checksum for the portable `.exe`
- [ ] Confirm the artifact starts on a second Windows machine
- [ ] Confirm private files under `runtime/data/` are still ignored by git

## Finish Line

The release is ready for normal daily use when:

- voice works reliably
- hardware hotplug events are visible
- local AI replies work
- the desktop build launches
- Smart Home control works in either demo mode or your real local setup
