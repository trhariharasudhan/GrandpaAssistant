# Structure Audit Report

Date: 2026-05-23

Protected primary run path:

```text
python backend\desktop_backend_entry.py
```

Scope: inspection only. No files were deleted, renamed, refactored, staged, committed, or pushed.

## 1. Current Structure Summary

GrandpaAssistant is currently structured as a backend/API/CLI-first Windows assistant.

Top-level structure:

```text
GrandpaAssistant/
|-- .github/        GitHub Actions workflow
|-- .python311/     ignored local Python runtime
|-- .venv/          ignored local virtual environment
|-- .vscode/        tracked local editor config
|-- backend/        active backend runtime, APIs, assistant logic, assets, seed data
|-- docs/           architecture, audit, roadmap, setup, release, and validation docs
|-- plugins/        simple local plugin examples
|-- reference/      ignored local prompt/reference material
|-- runtime/        ignored local state, logs, cache, config, models, artifacts
|-- scripts/        dev diagnostics/smoke tools and Windows helper scripts
|-- tests/          backend regression suite
|-- README.md
|-- main.py
|-- requirements.txt
```

Backend structure:

```text
backend/
|-- app/                         main Python package
|   |-- agents/
|   |-- api/
|   |-- autonomous_agent/
|   |-- browser_automation/
|   |-- chat_integrations/
|   |-- cli/
|   |-- config/
|   |-- core/
|   |-- features/
|   |-- integrations/
|   |-- local_action_orchestrator/
|   |-- project_knowledge/
|   |-- prompts/
|   |-- security/
|   |-- services/
|   |-- shared/
|   |-- visual_desktop/
|-- assets/
|-- data/
|-- desktop_backend_boot.py
|-- desktop_backend_entry.py
|-- fastapi_chat.py
|-- main.py
|-- requirements.txt
```

Other observed counts and layout:

- `tests/`: 127 tracked test files.
- `docs/`: 127 top-level tracked doc files plus organized subfolders.
- `scripts/dev/`: 26 tracked developer diagnostics/smoke/status scripts.
- `.github/workflows`: one tracked workflow, `backend.yml`.
- `runtime/`: local-only folders for artifacts, browser automation, cache, config, data, logs, and models.
- `reference/`: local-only `system_prompts_leaks` material.

## 2. What Is Correct

- The repository is correctly backend-only at the workspace level: no tracked `frontend/` or `mobile/` app-client directories exist.
- `.venv` and `.python311` are ignored and not tracked.
- The protected primary entrypoint, `backend/desktop_backend_entry.py`, is present and tracked.
- `backend/app/` is organized by runtime concerns: API, CLI, core logic, shared services, feature modules, security, prompts, project knowledge, and automation systems.
- Tests are extensive and map to current behavior: API routes, command router handlers, safety checks, personal assistant, project knowledge, prompt runtime, LLM providers, startup, and Windows/local controls.
- `docs/` contains current architecture and ownership documents that explain why some duplication remains intentional.
- `scripts/dev/` contains useful developer tooling, including protected `startup_smoke_check.py` and `personal_assistant_status.py`.
- Runtime state, logs, local model files, credentials, databases, and caches are under ignored local paths.
- CI is backend-focused. `.github/workflows/backend.yml` runs on Windows, installs `backend/requirements.txt`, runs tests, and then runs `scripts/dev/full_backend_validation.py`.

## 3. What Is Confusing

- There are several legitimate but confusing entrypoints:
  - `backend/desktop_backend_entry.py`: primary protected runtime.
  - `backend/main.py`: backend launcher helper.
  - root `main.py`: root launcher/helper.
  - `backend/fastapi_chat.py`: alternate chat API entrypoint.
  - `backend/app/api/web_api.py`: active desktop API app.
  - `backend/app/api/chat_api.py`: alternate chat/runtime API app.
- `web_api.py` and `chat_api.py` overlap. This is documented and tested, but it is still a structural complexity.
- `backend/app/features/modules/` is an intentional compatibility shim layer. It can look duplicate to a new maintainer.
- Docs are numerous. Most are useful, but historical release/phase docs make the docs folder feel heavy.
- `reference/system_prompts_leaks/` is ignored local reference material. It should stay out of git, but its presence can confuse structure audits unless called out as local-only.
- Root has an untracked generated tree dump: `repo_tree_project_only.txt`, about 6 MB.
- `runtime/artifacts/` exists as an ignored generated folder. It is safe local output, but if packaging is not actively needed it can be periodically cleared.

## 4. Safe Cleanup Recommendations

No cleanup was performed in this inspection pass.

Recommended safe cleanup actions for a future cleanup pass:

- Delete the untracked generated tree file:

```text
repo_tree_project_only.txt
```

- Add these generated tree dumps to `.gitignore` if they may be regenerated:

```text
repo_tree.txt
repo_tree_full.txt
repo_tree_project_only.txt
```

- Periodically delete generated Python caches outside `.venv` and `.python311`:

```text
__pycache__/
*.pyc
```

- Periodically clear generated packaging output if no local build artifact is needed:

```text
runtime/artifacts/
```

- Consider archiving older release/phase docs under a future `docs/archive/` only after confirming they are no longer current. Do not delete them.

## 5. Do-Not-Touch Files/Folders

Do not delete or rename these in routine cleanup:

```text
backend/app/**
backend/desktop_backend_entry.py
backend/desktop_backend_boot.py
backend/fastapi_chat.py
backend/main.py
backend/assets/**
backend/data/knowledge/*.json
tests/**
scripts/dev/startup_smoke_check.py
scripts/dev/personal_assistant_status.py
scripts/dev/full_backend_validation.py
scripts/windows/**
docs/ARCHITECTURE.md
docs/FEATURE_AUDIT.md
docs/API_OWNERSHIP_PLAN.md
docs/STATUS_ENDPOINT_OWNERSHIP.md
docs/COMPLETION_ROADMAP.md
docs/PERSONAL_ASSISTANT_CHECKPOINT.md
docs/PERSONAL_ASSISTANT_RELEASE_SNAPSHOT.md
docs/CLEANUP_AUDIT_REPORT.md
.github/workflows/backend.yml
.env.example
backend/assets/iot_credentials.example.json
```

Keep local-only but do not track:

```text
.venv/
.python311/
runtime/
reference/system_prompts_leaks/
```

## 6. Test Folder Explanation

The test folder is large, but it is useful rather than wasteful.

The tracked `test_*.py` files protect:

- active and alternate API route behavior
- chat service behavior
- prompt runtime and project knowledge integration
- route ownership and duplication boundaries
- command router extraction and read-only handlers
- safety confirmation paths
- local actions and UI/screen/visual desktop safety
- debug assistant flows
- contact/calling behavior
- personal assistant memory, tools, voice, scheduler, startup, and e2e behavior
- backend startup and CORS/security behavior

No tests should be removed simply because their feature is currently implemented. They are regression guards.

## 7. Runtime/Local Data Explanation

`runtime/` is correctly local-only and ignored. It contains:

```text
runtime/artifacts/           generated packaging/build output
runtime/browser_automation/  local browser automation memory/state
runtime/cache/               local caches, TTS audio, model downloads, project knowledge cache
runtime/config/              local config and credential-like files
runtime/data/                local assistant data, databases, histories, audit/debug state
runtime/logs/                local JSONL logs
runtime/models/              local model files
```

These files are safe to keep local only and should not be tracked. Some can be deleted manually if they are known stale, but `runtime/data`, `runtime/config`, and `runtime/models` may contain useful local state, credentials, or offline assets.

## 8. Git Tracking Issues

Requested command results:

```text
git status --short
?? docs/CLEANUP_AUDIT_REPORT.md
?? repo_tree_project_only.txt
```

After this report is created, `docs/STRUCTURE_AUDIT_REPORT.md` is also expected to appear as untracked until staged.

```text
git ls-files .python311 .venv
(no output)
```

`.python311` and `.venv` are not tracked.

```text
git ls-files repo_tree.txt repo_tree_full.txt repo_tree_project_only.txt
(no output)
```

Tree dump files are not tracked. However, `repo_tree_project_only.txt` exists untracked at the root and should be deleted or ignored.

```text
git ls-files frontend mobile
(no output)
```

No tracked frontend/mobile workspace exists.

```text
git ls-files | findstr /I "desktop_backend_entry web_api chat_api"
backend/app/api/chat_api.py
backend/app/api/web_api.py
backend/desktop_backend_entry.py
tests/test_chat_api_prompt_behavior.py
tests/test_chat_api_regressions.py
tests/test_web_api_prompt_behavior.py
tests/test_web_api_routes.py
```

This confirms the primary entrypoint and both API apps are tracked, with regression tests for both API surfaces.

```text
git ls-files | findstr /I "test_"
```

This returns the tracked backend regression suite plus `scripts/smoke_test_terminal_chat.py` and `docs/PERSONAL_ASSISTANT_E2E_TEST_PACK.md`. The test inventory is expected and useful.

Frontend/mobile search notes:

- No tracked `frontend/` or `mobile/` folders.
- Backend mobile companion code exists under `backend/app/shared/mobile_companion.py` and `/mobile` routes in `web_api.py`; this is documented compatibility backend runtime logic, not a mobile app workspace.

## 9. Validation Result

Requested validation commands:

```text
python -m unittest discover -s tests -v
PASS, exit code 0
```

The command produced no captured stdout in this shell session, but exited successfully.

```text
python scripts/dev/startup_smoke_check.py
PASS
overall_ok=True
```

Startup smoke confirmed:

- no pre-existing API server
- main process stayed alive
- `/api/health` became ready
- graceful shutdown worked

```text
python scripts/dev/personal_assistant_status.py --check
PASS, exit code 0
```

Personal assistant status result:

- `ok: true`
- `critical_failures: []`
- `tool_count: 34`
- optional warnings only: missing screen/OCR adapter, STT adapter, and Windows toast adapter

```text
git diff --check
PASS, exit code 0
```

No whitespace/diff formatting errors were reported.

## 10. Final Verdict

Verdict: **clean, with minor cleanup recommended**.

The folder structure is correct and professional for the current backend-only, Windows-first, API/CLI-focused GrandpaAssistant project.

Not risky:

- Backend code organization is coherent.
- Tests are useful and should remain.
- Docs are broad but mostly current and explanatory.
- Runtime data/log/cache/model files are correctly local-only.
- `.venv` and `.python311` are ignored and untracked.
- No frontend/mobile app-client leftovers are tracked.

Needs minor cleanup:

- Delete or ignore `repo_tree_project_only.txt`.
- Consider adding all `repo_tree*.txt` generated tree dumps to `.gitignore`.
- Keep documenting duplicate entrypoint ownership until `web_api.py` and `chat_api.py` are further split/consolidated.
- Consider a future docs archive pass for older phase/release docs, but do not delete them blindly.
