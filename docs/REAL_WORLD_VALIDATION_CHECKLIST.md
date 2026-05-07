# Real-World Backend Validation Checklist

Date: 04 April 2026

Use this checklist after the backend assistant is running on the target Windows machine.

## Core Startup

- [ ] Run `python backend\desktop_backend_entry.py`
- [ ] Run `python scripts\dev\startup_smoke_check.py`
- [ ] Confirm startup doctor has no hard errors
- [ ] Confirm `GET /api/health` responds while the backend is running

## Voice

- [ ] Say the wake word and confirm the assistant wakes up
- [ ] Ask a short general question and confirm speech output works
- [ ] Say `stop` while it is speaking and confirm interruption works
- [ ] Check `tts backend status` and confirm the selected TTS backend is ready

## Hardware Events

- [ ] Run `scripts\windows\watch_hardware_changes.cmd`
- [ ] Insert a storage device and confirm a `storage` connected event appears
- [ ] Remove the device and confirm a disconnect event appears
- [ ] Connect or disconnect a microphone/headset and confirm event detection
- [ ] If available, connect a webcam and confirm camera detection

## Local AI

- [ ] Run `ollama list` and confirm required models are installed
- [ ] Send a general prompt and confirm it routes to `mistral:7b`
- [ ] Send a coding prompt and confirm it routes to `deepseek-coder:6.7b`
- [ ] Send a fast/simple prompt and confirm it can use `phi3:mini`

## Smart Home

- [ ] Run `scripts\windows\validate_iot_setup.cmd`
- [ ] Ask `iot status` and confirm Smart Home status is clear
- [ ] Trigger one safe Smart Home command and confirm success
- [ ] If using real Home Assistant or MQTT, verify one real device action

## Finish Line

The backend is ready for daily use when voice, local AI, startup health, hardware events, memory, productivity, and Smart Home control all behave as expected.
