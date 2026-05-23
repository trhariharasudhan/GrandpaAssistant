# Cleanup Audit Report

Date: 2026-05-23

## Scope

This audit covers the local backend-only GrandpaAssistant checkout at `D:\GrandpaAssistant`.

Protected runtime path:

```text
python backend\desktop_backend_entry.py
```

The cleanup policy for this pass is conservative:

- Keep backend runtime code, safety/automation code, docs that describe current architecture, config/templates, and regression tests.
- Do not delete tests just because the feature is implemented.
- Delete only generated cache/build artifacts that can be recreated and are already ignored by git.
- Avoid broad `git clean` because it would remove local environments, local runtime data, model caches, credentials, and reference material.

## Inspection Summary

- `git status --short --branch`: clean, on `main`, aligned with `origin/main`.
- `git ls-files --others --exclude-standard`: no untracked non-ignored files.
- `.gitignore`: already ignores Python caches, `.venv`, `.python311`, runtime output, secrets, temp files, logs, databases, package outputs, and local reference prompt material.
- `tests/`: keep. The folder contains active regression tests for current APIs, command routing, safety, chat, personal assistant, project knowledge, startup, and local action behavior.
- `docs/`: keep current architecture, ownership, roadmap, checkpoint, release, audit, and setup docs. No docs are proposed for deletion.
- `scripts/dev/`: keep. The scripts are active diagnostics, smoke checks, inventory tools, status CLIs, and validation helpers.
- `runtime/`: contains a mix of generated build artifacts, caches/models, logs, local data, config, credentials, and user-state-like files. Only generated packaging artifacts are proposed for deletion.

## A. Safe To Delete Now

Generated Python bytecode/cache directories outside local Python installations:

```text
__pycache__
backend\__pycache__
backend\app\__pycache__
backend\app\agents\__pycache__
backend\app\api\__pycache__
backend\app\api\routes\__pycache__
backend\app\autonomous_agent\__pycache__
backend\app\browser_automation\__pycache__
backend\app\chat_integrations\__pycache__
backend\app\cli\__pycache__
backend\app\config\__pycache__
backend\app\core\__pycache__
backend\app\core\chatbot\__pycache__
backend\app\core\chatbot\providers\__pycache__
backend\app\core\commands\__pycache__
backend\app\core\commands\handlers\__pycache__
backend\app\core\commands\summaries\__pycache__
backend\app\core\jarvis_voice\__pycache__
backend\app\core\llm\__pycache__
backend\app\core\llm\providers\__pycache__
backend\app\core\personal_assistant\__pycache__
backend\app\core\prompts\__pycache__
backend\app\features\__pycache__
backend\app\features\automation\__pycache__
backend\app\features\integrations\__pycache__
backend\app\features\intelligence\__pycache__
backend\app\features\modules\__pycache__
backend\app\features\productivity\__pycache__
backend\app\features\security\__pycache__
backend\app\features\system\__pycache__
backend\app\features\ui_analysis\__pycache__
backend\app\features\vision\__pycache__
backend\app\features\voice\__pycache__
backend\app\integrations\__pycache__
backend\app\local_action_orchestrator\__pycache__
backend\app\project_knowledge\__pycache__
backend\app\security\__pycache__
backend\app\services\__pycache__
backend\app\services\browser_automation\__pycache__
backend\app\shared\__pycache__
backend\app\shared\brain\__pycache__
backend\app\shared\cognition\__pycache__
backend\app\shared\controls\__pycache__
backend\app\shared\utils\__pycache__
backend\app\visual_desktop\__pycache__
plugins\__pycache__
scripts\__pycache__
scripts\dev\__pycache__
tests\__pycache__
```

Generated packaging artifacts under ignored runtime output:

```text
runtime\artifacts\backend
runtime\artifacts\build
runtime\artifacts\dist
```

Measured size for `runtime\artifacts`: 694 files, about 322,867,286 bytes.

## B. Keep

Keep these areas intact:

```text
backend\app\**
backend\desktop_backend_entry.py
backend\desktop_backend_boot.py
backend\fastapi_chat.py
backend\main.py
tests\**
scripts\dev\startup_smoke_check.py
scripts\dev\personal_assistant_status.py
scripts\dev\*.py
scripts\windows\**
docs\ARCHITECTURE.md
docs\FEATURE_AUDIT.md
docs\API_OWNERSHIP_PLAN.md
docs\COMPLETION_ROADMAP.md
docs\PERSONAL_ASSISTANT_CHECKPOINT.md
docs\PERSONAL_ASSISTANT_RELEASE_SNAPSHOT.md
docs\STATUS_ENDPOINT_OWNERSHIP.md
docs\project_knowledge\**
docs\prompt_runtime\**
backend\assets\**
backend\data\knowledge\basic_math.json
backend\data\knowledge\basic_science.json
backend\data\knowledge\thirukkural_sample.json
plugins\**
```

Keep local environment/runtime areas:

```text
.venv
.python311
runtime\config
runtime\data
runtime\models
runtime\cache
runtime\logs
runtime\browser_automation
reference\system_prompts_leaks
```

Reason: these are ignored, local-only, or large, but they may contain active local environment dependencies, user/local assistant state, credentials, model assets, useful caches, logs for debugging, or prompt research reference material.

## C. Review Manually

These are ignored/local files that may be stale, but they can contain useful local data or state, so this pass will not delete them:

```text
backend\data\last_backend_validation.json
backend\data\terminal_chat.sqlite3
backend\data\knowledge\review_queue.jsonl
runtime\data\exports\*.txt
runtime\logs\*.jsonl
runtime\cache\tts_audio\*.wav
runtime\cache\model_download\yolov8n.pt
runtime\cache\coqui\**
runtime\config\*.json
runtime\data\*.json
runtime\data\*.db
runtime\data\*.key
runtime\models\**
reference\system_prompts_leaks\**
```

Manual review questions:

- Are the `runtime\data\exports\daily_recap_*.txt` files still useful?
- Should old runtime logs be rotated rather than deleted?
- Should duplicated model/cache files be rebuilt on demand, or kept for offline use?
- Should ignored `backend\data\terminal_chat.sqlite3` be migrated or archived before deletion?

## D. Move To `docs/archive` Instead Of Delete

No tracked docs are proposed for archive in this cleanup pass.

Candidate areas for a future documentation archive review, not this pass:

```text
docs\RELEASE_NOTES_*.md
docs\RELEASE_CANDIDATE_*.md
docs\V1_*.md
docs\prompt_runtime\PHASE_*.md
docs\project_knowledge\RAG_PHASE_*.md
```

Reason: these may be historical rather than current, but they still explain architecture and rollout decisions.

## Exact Deletion Plan

Delete only:

1. The `__pycache__` directories listed in section A.
2. `runtime\artifacts\backend`
3. `runtime\artifacts\build`
4. `runtime\artifacts\dist`

Do not delete:

- `.venv`
- `.python311`
- `runtime` as a whole
- `runtime\data`
- `runtime\config`
- `runtime\models`
- `runtime\cache`
- `backend\data\terminal_chat.sqlite3`
- `backend\data\knowledge\review_queue.jsonl`
- `reference`

## Post-Cleanup Validation Plan

Run:

```powershell
python -m unittest discover -s tests -v
python scripts/dev/startup_smoke_check.py
python -m compileall backend
python scripts/dev/personal_assistant_status.py --check
git diff --check
```

If validation fails, restore deleted files only if the failure is caused by the cleanup. Generated caches should normally be recreated automatically.
