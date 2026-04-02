# Grandpa Assistant V1 Release Candidate Notes

Date: 02 April 2026  
Branch: `codex/stabilize-refactor-build`  
Commit: `fb8073f`

## Status

V1 stabilization work is complete and ready for pull request review.

## Release Scope

- V1 scope remains limited to stable daily-use features from [`docs/V1_SCOPE.md`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\docs\V1_SCOPE.md)
- Phase 1 to Phase 10 checklist is complete (`51/51`) in [`docs/PROJECT_COMPLETION_CHECKLIST.md`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\docs\PROJECT_COMPLETION_CHECKLIST.md)

## Key Changes Included

- Chat/RAG flow stabilization, session management polish, and citation reliability.
- Voice baseline hardening and settings/tuning completion.
- Productivity/planner reliability improvements.
- Frontend UX cleanup across chat, dashboard, settings, and panel consistency.
- Smoke test automation scripts added under `scripts/dev/`.
- Startup smoke check added and validated.
- Repository cleanup, temp artifact handling, and ignore rule improvements.
- Documentation moved and consolidated under `docs/` with updated setup guidance.

## Validation Summary

All major validation commands passed:

- `cmd /c npm run build` (frontend)
- `cmd /c ".venv\Scripts\activate.bat && python scripts\dev\chat_rag_smoke_check.py"`
- `cmd /c ".venv\Scripts\activate.bat && python scripts\dev\voice_smoke_check.py"`
- `cmd /c ".venv\Scripts\activate.bat && python scripts\dev\productivity_smoke_check.py"`
- `cmd /c ".venv\Scripts\activate.bat && python scripts\dev\planner_focus_smoke_check.py"`
- `cmd /c ".venv\Scripts\activate.bat && python scripts\dev\startup_smoke_check.py"`
- `cmd /c npm run desktop:build` (frontend)

Smoke details are tracked in [`docs/V1_SMOKE_CHECKLIST.md`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\docs\V1_SMOKE_CHECKLIST.md).

## Final Pre-Merge Checks

1. Confirm pull request is open from `codex/stabilize-refactor-build` into `main`.
2. Run one final manual sanity pass:
   - `python main.py`
   - `scripts\windows\start_react_desktop.cmd`
3. Confirm expected desktop artifact exists: `frontend\release\Grandpa Assistant 0.1.0.exe`.
4. Merge PR and create release tag.

## Notes

- Object detection extras remain out of V1 and stay in V2 roadmap bucket.
