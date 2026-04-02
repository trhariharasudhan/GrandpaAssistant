# Features Folder Guide

`backend/app/features/` is organized by domain so each area has clear ownership:

- `productivity/` - tasks, reminders, notes, calendar, dashboard, briefings
- `system/` - OS/system controls and desktop context actions
- `automation/` - startup helpers, messaging automations, notifications, dictation helpers
- `intelligence/` - browser/file intelligence workflows
- `voice/` - listen/speak and voice profile logic
- `vision/` - OCR, object detection, hand mouse, camera helpers
- `integrations/` - external service integrations (weather, IoT, Google links)
- `security/` - emergency and face-verification flows
- `modules/` - compatibility aliases for older imports (do not add new logic here)

If you are adding a new capability, place it in the correct domain folder above and keep
`modules/` as forwarding-only wrappers.
