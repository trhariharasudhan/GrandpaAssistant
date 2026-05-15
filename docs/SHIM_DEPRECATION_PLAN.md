# Shim Deprecation Plan

Phase 3 compatibility shim audit for `backend/app/features/modules`.

## Current Shim Purpose

`backend/app/features/modules` keeps legacy imports such as `from modules.task_module import ...` working while active backend code uses the newer domain modules under `automation`, `intelligence`, `integrations`, `productivity`, and `system`.

Most shim files forward directly to the real domain module with `importlib` and `sys.modules`. `desktop_launch_module` is the only special case: desktop UI launchers were removed from the backend-only build, so that shim now imports successfully and exposes disabled backend-only no-op launch functions.

## Remaining Repo-Wide References

| Area | References | Status | Action |
| --- | --- | --- | --- |
| Active backend Python | No external `from modules` / `import modules` callers outside shim tests | Resolved | None |
| Dev scripts | `scripts/dev/productivity_smoke_check.py` previously used `from modules`; now migrated to `from productivity` | Resolved | Keep direct import |
| Tests | `tests/test_compatibility_shims.py` intentionally imports `modules.*` to prove compatibility still works | Intentional | Keep while shims exist |
| Inventory tooling | `scripts/dev/inventory_backend.py` scans and reports `modules` / `features.modules` risks | Intentional | Keep |
| Docs and generated inventory | Architecture, audit, legacy-risk, inventory reports, and shim README mention `modules.*` | Intentional documentation | Keep until removal phase |
| Batch/PowerShell/legacy launchers | No direct shim imports found | No dependency | None |
| Root-level Python/config files | No direct shim imports found | No dependency | None |

## External Compatibility Risks

The repository no longer has active runtime callers that require `modules.*`, but external users may still have local scripts, shortcuts, plugins, or old automation snippets that import from `modules`. Removing the shim package without a deprecation window could break those private callers even though in-repo validation passes.

## What Can Be Migrated Now

- New code should import domain modules directly.
- Dev scripts should use direct domain imports. `scripts/dev/productivity_smoke_check.py` has already been migrated.
- Documentation should keep examples clear that `modules.*` is compatibility-only, not the preferred path.

## What Must Stay Temporarily

- `backend/app/features/modules/*.py` must stay until the deprecation criteria below pass.
- `desktop_launch_module` must stay as a disabled compatibility shim so old imports fail gracefully in the backend-only build.
- The shim regression test must stay while the compatibility layer exists.

## Deprecation Window

Start date: 2026-05-14.

Minimum window before removal: 30 days or two successful backend cleanup phases, whichever is longer.

During the window:

- Keep running repo-wide shim reference scans.
- Keep `tests/test_compatibility_shims.py` passing.
- Do not add new active runtime imports from `modules.*`.
- Record any external/local caller that still depends on the shim package.

## Removal Criteria

Shims are safe to remove only when all criteria pass in the same cleanup phase:

- Repo-wide scan has no active runtime, script, test, plugin, launcher, or config dependency on `modules.*` except planned removal tests/docs.
- `scripts/dev/inventory_backend.py` reports no `NEEDS_RUNTIME_REVIEW` legacy imports.
- Terminal chatbot smoke passes without importing shim modules.
- Desktop backend startup smoke passes.
- A temporary removal branch can delete `backend/app/features/modules` and still pass full validation.
- A rollback commit or patch is prepared before deletion.

## Rollback Plan

If removal causes a runtime or external compatibility regression:

1. Restore `backend/app/features/modules` from the previous commit.
2. Restore `tests/test_compatibility_shims.py`.
3. Re-run inventory, unit tests, startup smoke, and terminal chatbot smoke.
4. Document the failing external caller in this plan before attempting removal again.

## Recommendation

Keep the shims for now. The in-repo active dependency risk is resolved, but the compatibility layer should remain through the deprecation window because it is cheap, tested, and protects unknown external callers.
