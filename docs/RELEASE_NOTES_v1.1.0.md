# Grandpa Assistant Release Notes v1.1.0

Date: 02 April 2026

## Overview

This release adds the NextGen productivity feature pack on top of the V1 stabilization baseline.

## Highlights

- AI day planner with focused time blocks from tasks/reminders.
- Habit tracker with check-ins, streaks, and dashboard summary.
- Goals and milestones board with completion tracking.
- Smart reminder priority ranking (P1/P2/P3 style).
- Voice trainer presets for quiet/normal/noisy environments.
- Language mode controls (`auto`, `english`, `tamil`) with preview.
- Meeting capture with extracted action items.
- RAG library metadata tools (document tags and folders).
- Lightweight automation rule manager (create/list/enable/disable).
- Mobile companion setup and queued update feed.

## API and UI Improvements

- New NextGen status snapshot included in API UI state payload.
- Dashboard now includes a dedicated NextGen card with quick actions.
- Command router now supports direct natural commands for all 10 features.

## Verification Summary

The following checks were run successfully on `main` before tagging:

- `cmd /c ".venv\Scripts\activate.bat && python scripts\dev\nextgen_smoke_check.py"` -> `overall_ok=True`
- `cmd /c npm run build` (frontend Vite production build)

## Notes

- This release is focused on feature expansion while preserving the V1 stable core.
- Runtime local data remains under `backend/data/` and is intentionally not part of release commits.
