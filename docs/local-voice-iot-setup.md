# Local Voice and IoT Setup

## Smart Home Config

1. Copy `backend/data/iot_credentials.example.json` to `backend/data/iot_credentials.json`.
2. Set `"enabled": true` after you replace every placeholder value.
3. Use one of these local control styles:
   - `webhook`: local HTTP endpoints or Node-RED style flows
   - `home_assistant_service`: direct Home Assistant service calls
   - `mqtt`: local MQTT broker publishing
4. High-risk commands such as locks, doors, alarms, and disable actions should keep `requires_confirmation: true`.

## Piper Voice Setup

1. Put a `.onnx` Piper model in one of these folders:
   - `backend/data/piper`
   - `backend/data/voices`
   - `models/piper`
2. Put the matching `.json` config next to the model file.
3. Run one of these assistant commands:
   - `auto configure piper`
   - `use piper voice`
   - `piper setup status`

## Wake Word Tuning

Useful commands:

- `set wake threshold to 0.72`
- `enable strict wake word`
- `disable strict wake word`
- `set wake prefix words to 1`
- `enable continuous conversation`
- `disable continuous conversation`
- `set follow up timeout to 14 seconds`

## Recommended Local Stack

- Smart home: Home Assistant or MQTT broker on the same LAN
- Voice input: Whisper `base`
- Voice output: Piper with one English or Tamil voice model
- Wake tuning: strict wake word on, prefix words `1`, threshold `0.7` to `0.78`
