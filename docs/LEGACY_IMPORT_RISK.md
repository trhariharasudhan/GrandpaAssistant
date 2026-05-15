# Legacy Import Risk

Phase 2 backend import cleanup. This pass did not move modules, delete shims, add UI code, or change the backend run paths.

## Summary

Initial categorized inventory before direct replacements:

| Category | Count |
| --- | ---: |
| KEEP_COMPAT_NOW | 54 |
| NEEDS_RUNTIME_REVIEW | 351 |
| NO_LEGACY_RISK | 1694 |
| GENERATED_ARTIFACT_ONLY | 7 paths |

Inventory after Phase 2 replacements:

| Category | Count |
| --- | ---: |
| KEEP_COMPAT_NOW | 54 |
| NEEDS_RUNTIME_REVIEW | 0 |
| NO_LEGACY_RISK | 2045 |
| GENERATED_ARTIFACT_ONLY | 7 paths |

Inventory after Phase 3 shim audit:

| Category | Count |
| --- | ---: |
| KEEP_COMPAT_NOW | 52 |
| NEEDS_RUNTIME_REVIEW | 0 |
| NO_LEGACY_RISK | 2045 |
| GENERATED_ARTIFACT_ONLY | 7 paths |

The remaining legacy import risks are internal compatibility shim imports in `backend/app/features/modules/*.py`. They are intentional and should stay until external callers and run paths no longer rely on `modules.*` compatibility.

Phase 3 repo-wide scan resolved the last in-repo external script caller: `scripts/dev/productivity_smoke_check.py` now imports from `productivity` directly. Active backend external legacy imports remain resolved. Do not remove the shim package before the deprecation criteria in `docs/SHIM_DEPRECATION_PLAN.md` pass.

## Import Risk Table

| Import Path | Used By | Target Module | Risk Level | Safe Replacement | Action |
| --- | --- | --- | --- | --- | --- |
| `modules.app_scan_module` | `backend/app/core/assistant.py`, `backend/app/core/command_router.py` | `system.app_scan_module` | SAFE_TO_REPLACE_NOW | `system.app_scan_module` | Replaced |
| `modules.briefing_module` | `backend/app/core/command_router.py`, `backend/app/core/intent_router.py` | `productivity.briefing_module` | SAFE_TO_REPLACE_NOW | `productivity.briefing_module` | Replaced |
| `modules.browser_automation_module` | `backend/app/core/intent_router.py` | `intelligence.browser_automation_module` | SAFE_TO_REPLACE_NOW | `intelligence.browser_automation_module` | Replaced |
| `modules.calendar_module` | `backend/app/core/command_router.py`, `backend/app/core/intent_router.py` | `productivity.calendar_module` | SAFE_TO_REPLACE_NOW | `productivity.calendar_module` | Replaced |
| `modules.dashboard_module` | `backend/app/core/intent_router.py` | `productivity.dashboard_module` | SAFE_TO_REPLACE_NOW | `productivity.dashboard_module` | Replaced |
| `modules.dictation_module` | `backend/app/core/assistant.py`, `backend/app/core/command_router.py` | `automation.dictation_module` | SAFE_TO_REPLACE_NOW | `automation.dictation_module` | Replaced |
| `modules.event_module` | `backend/app/api/web_api.py`, `backend/app/core/assistant.py`, `backend/app/core/intent_router.py` | `productivity.event_module` | SAFE_TO_REPLACE_NOW | `productivity.event_module` | Replaced |
| `modules.export_module` | `backend/app/core/intent_router.py` | `productivity.export_module` | SAFE_TO_REPLACE_NOW | `productivity.export_module` | Replaced |
| `modules.file_intelligence_module` | `backend/app/core/intent_router.py` | `intelligence.file_intelligence_module` | SAFE_TO_REPLACE_NOW | `intelligence.file_intelligence_module` | Replaced |
| `modules.google_calendar_module` | `backend/app/core/command_router.py` | `integrations.google_calendar_module` | SAFE_TO_REPLACE_NOW | `integrations.google_calendar_module` | Replaced |
| `modules.google_contacts_module` | `backend/app/api/web_api.py`, `backend/app/core/assistant.py`, `backend/app/core/command_router.py`, `backend/app/shared/brain/memory_engine.py` | `integrations.google_contacts_module` | SAFE_TO_REPLACE_NOW | `integrations.google_contacts_module` | Replaced |
| `modules.health_module` | `backend/app/api/web_api.py`, `backend/app/core/intent_router.py` | `system.health_module` | SAFE_TO_REPLACE_NOW | `system.health_module` | Replaced |
| `modules.media_module` | `backend/app/core/command_router.py` | `system.media_module` | SAFE_TO_REPLACE_NOW | `system.media_module` | Replaced |
| `modules.messaging_automation_module` | `backend/app/core/assistant.py`, `backend/app/core/command_router.py`, `backend/app/core/intent_router.py` | `automation.messaging_automation_module` | SAFE_TO_REPLACE_NOW | `automation.messaging_automation_module` | Replaced |
| `modules.nextgen_module` | `backend/app/agents/catalog.py`, `backend/app/api/web_api.py`, `backend/app/core/command_router.py` | `productivity.nextgen_module` | SAFE_TO_REPLACE_NOW | `productivity.nextgen_module` | Replaced |
| `modules.notes_module` | `backend/app/api/web_api.py`, `backend/app/core/command_router.py`, `backend/app/core/intent_router.py` | `productivity.notes_module` | SAFE_TO_REPLACE_NOW | `productivity.notes_module` | Replaced |
| `modules.notification_module` | `backend/app/core/assistant.py`, `backend/app/core/command_router.py`, `backend/app/core/intent_router.py` | `automation.notification_module` | SAFE_TO_REPLACE_NOW | `automation.notification_module` | Replaced |
| `modules.profile_module` | `backend/app/core/assistant.py`, `backend/app/core/command_router.py`, `backend/app/core/intent_router.py` | `productivity.profile_module` | SAFE_TO_REPLACE_NOW | `productivity.profile_module` | Replaced |
| `modules.routine_module` | `backend/app/core/intent_router.py` | `productivity.routine_module` | SAFE_TO_REPLACE_NOW | `productivity.routine_module` | Replaced |
| `modules.startup_module` | `backend/app/api/web_api.py`, `backend/app/core/assistant.py`, `backend/app/core/command_router.py` | `automation.startup_module` | SAFE_TO_REPLACE_NOW | `automation.startup_module` | Replaced |
| `modules.system_module` | `backend/app/core/command_router.py` | `system.system_module` | SAFE_TO_REPLACE_NOW | `system.system_module` | Replaced |
| `modules.task_module` | `backend/app/agents/catalog.py`, `backend/app/api/web_api.py`, `backend/app/core/assistant.py`, `backend/app/core/command_router.py`, `backend/app/core/intent_router.py`, `backend/app/shared/cognition/graph_engine.py` | `productivity.task_module` | SAFE_TO_REPLACE_NOW | `productivity.task_module` | Replaced |
| `modules.weather_module` | `backend/app/api/web_api.py`, `backend/app/core/intent_router.py` | `integrations.weather_module` | SAFE_TO_REPLACE_NOW | `integrations.weather_module` | Replaced |
| `modules.web_module` | `backend/app/core/command_router.py` | `integrations.web_module` | SAFE_TO_REPLACE_NOW | `integrations.web_module` | Replaced |
| `modules.window_context_module` | `backend/app/core/command_router.py`, `backend/app/core/intent_router.py`, `backend/app/shared/window_awareness.py` | `system.window_context_module` | SAFE_TO_REPLACE_NOW | `system.window_context_module` | Replaced |
| `modules.windows_voice_control_module` | `backend/app/core/command_router.py` | `system.windows_voice_control_module` | SAFE_TO_REPLACE_NOW | `system.windows_voice_control_module` | Replaced |
| `backend/app/features/modules/*.py` | Compatibility shim package | Domain modules under `automation`, `intelligence`, `integrations`, `productivity`, and `system`; `desktop_launch_module` stays as a disabled backend-only compatibility shim | KEEP_COMPAT_NOW | Keep shim internals until compatibility is retired | Added shim warning docstrings and Phase 3 regression coverage |
| `backend/app/brain/**/__pycache__` | Compiled artifacts only | Active source under `backend/app/shared/brain` and `backend/app/agents` | GENERATED_ARTIFACT_ONLY | None | Document only |
| `backend/app/services/integrations/**/__pycache__` | Compiled artifacts only | Active source under `backend/app/features/integrations` | GENERATED_ARTIFACT_ONLY | None | Document only |
| `backend/app/services/iot/**/__pycache__` | Compiled artifacts only | Active source under shared IoT-related helpers | GENERATED_ARTIFACT_ONLY | None | Document only |
| `backend/app/services/llm/**/__pycache__` | Compiled artifacts only | Active source under shared LLM/provider modules | GENERATED_ARTIFACT_ONLY | None | Document only |
| `backend/app/core/knowledge_engine/**/__pycache__` | Compiled artifacts only | Active local knowledge source is `backend/app/shared/local_knowledge.py` | GENERATED_ARTIFACT_ONLY | None | Document only |
| `backend/app/core/math_engine/**/__pycache__` | Compiled artifacts only | Active math handling is in chatbot intent routing and command modules | GENERATED_ARTIFACT_ONLY | None | Document only |
| `backend/app/core/security/**/__pycache__` | Compiled artifacts only | Active source under `backend/app/security` and shared auth modules | GENERATED_ARTIFACT_ONLY | None | Document only |

## Shim Documentation

Each Python file under `backend/app/features/modules/` now starts with:

```python
"""Compatibility shim. Do not remove until imports are migrated."""
```

The package `__init__.py` has the equivalent package-level warning.

## Future Action

Keep the shims for now. Active in-repo external callers have been migrated, but the shim package should not be removed before `docs/SHIM_DEPRECATION_PLAN.md` passes its deprecation window, removal criteria, and rollback check.
