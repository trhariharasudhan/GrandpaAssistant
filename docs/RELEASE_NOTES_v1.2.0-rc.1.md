# GrandpaAssistant v1.2.0-rc.1 Release Notes

## Release Status
Release Candidate 1

## Highlights
- Backend-only cleanup completed.
- Frontend and mobile tracked files removed.
- Backend stability dashboard added.
- `GET /api/backend/stability` added.
- Stability API secured for localhost/admin full access.
- Remote unauthenticated access receives restricted payload.
- Full backend validation script added.
- Backend CI workflow added.
- Command-router confirmation flow improved.
- Voice/chat echo guard improved.
- Optional dependency guards improved.

## Validation
- Unit tests: PASS, 37 tests
- Startup smoke check: PASS
- Full backend validation: PASS
- Backend py_compile: PASS, 146 files

## Known Warnings
- Ollama not running is treated as optional warning.
- Custom settings paths are preserved by startup diagnostics.

## Tag
`v1.2.0-rc.1`

## Commit
`9807d75d151f4c5adaea91be426a4bec40c8947c`