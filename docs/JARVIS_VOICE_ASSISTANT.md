# GrandpaAssistant Jarvis Voice Assistant

This document describes the new real-time voice layer for GrandpaAssistant. The implementation is local-first, Windows-optimized, and designed to wrap existing voice/chat/personal-assistant capabilities without replacing them.

## Architecture

Core package:

- `backend/app/core/jarvis_voice/settings.py`
- `backend/app/core/jarvis_voice/wake_word.py`
- `backend/app/core/jarvis_voice/speech_pipeline.py`
- `backend/app/core/jarvis_voice/streaming_router.py`
- `backend/app/core/jarvis_voice/conversation_state.py`
- `backend/app/core/jarvis_voice/manager.py`

Runtime flow:

```text
microphone / transcript
  -> WakeWordEngine
  -> SpeechPipeline
  -> VoiceManager
  -> StreamingVoiceRouter
  -> chat_service / personal_assistant
  -> SpeechPipeline TTS
  -> ConversationStateManager
```

## Capabilities

- Wake word support for `Hey Grandpa`.
- Continuous managed background loop, disabled unless configured.
- Push-to-talk API mode.
- Whisper-first STT setting with existing local voice listener integration.
- Piper-first TTS setting with XTTS fallback metadata.
- Interruptible speech through `stop_speaking`.
- Voice activity detection hook using local RMS.
- Noise suppression hook kept local and testable.
- Streaming response events over WebSocket.
- Conversation state for follow-up continuity.
- Multi-language and emotion-aware response metadata.
- Auto mute/unmute control.
- Settings persistence in local runtime data.

## API Surface

Added to `backend/app/api/web_api.py`:

- `GET /api/jarvis/status`
- `POST /api/jarvis/start`
- `POST /api/jarvis/stop`
- `POST /api/jarvis/interrupt`
- `POST /api/jarvis/mute`
- `GET /api/jarvis/settings`
- `POST /api/jarvis/settings`
- `POST /api/jarvis/push-to-talk`
- `WS /api/jarvis/ws`

The WebSocket accepts JSON events:

```json
{"type": "transcript", "transcript": "Hey Grandpa reduce volume", "session_id": "voice"}
```

It returns JSON events such as:

```json
{"type": "start", "source": "websocket"}
{"type": "token", "text": "Reduced "}
{"type": "done", "ok": true, "reply": "Reduced the system volume."}
```

## Safety

- The manager is off by default unless settings/env enable it.
- Unit tests use fake STT/TTS adapters; no microphone or speaker is required.
- The status path does not capture audio or call LLM providers.
- WebSocket execution still routes through `chat_service` and the personal-assistant tool registry.
- Risky actions continue to require the existing confirmation and permission flow.
- The streaming router does not return raw chat history in normal payloads.

## Settings

Persistent settings are stored locally through `GRANDPA_JARVIS_VOICE_SETTINGS_PATH` when set, otherwise under runtime data.

Relevant environment variables:

- `GRANDPA_JARVIS_VOICE_ENABLED`
- `GRANDPA_JARVIS_VOICE_SETTINGS_PATH`

Key settings:

- `wake_words`
- `continuous_listening`
- `push_to_talk_enabled`
- `stt_backend`
- `tts_backend`
- `fallback_tts_backend`
- `voice_profile`
- `language`
- `vad_enabled`
- `noise_suppression_enabled`
- `auto_mute`
- `interruptible`
- `streaming_enabled`
- `emotion_aware`

## Validation

Focused tests:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_jarvis_voice_system -v
```

Compile:

```powershell
.venv\Scripts\python.exe -m py_compile backend/app/core/jarvis_voice/*.py tests/test_jarvis_voice_system.py
```

Full validation should also include the existing personal assistant and startup smoke suites.

## Limitations

- True low-latency audio streaming depends on the installed local microphone, Whisper, Piper, or XTTS stack.
- Noise suppression is currently a local hook, not a heavy DSP dependency.
- WebSocket audio-frame ingestion is not enabled yet; the current endpoint accepts transcript/control events.
- Background startup remains opt-in through local settings or environment.
