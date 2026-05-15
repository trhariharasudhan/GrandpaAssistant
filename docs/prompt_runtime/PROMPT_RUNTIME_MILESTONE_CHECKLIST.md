# Prompt Runtime Milestone Checklist

## Release Candidate Checks

- [x] Prompt runtime tests passing.
- [x] `py_compile` passing for prompt runtime modules.
- [x] CLI checks passing.
- [x] Legacy mode verified.
- [x] Runtime mode verified.
- [x] No prompt body exposure in status/CLI.
- [x] Reference folder ignored.
- [x] Docs updated.
- [x] Feature flag documented.
- [x] Rollback documented.
- [x] No accidental API exposure.

## Pre-Commit Checks

- [ ] Review `git status --short`.
- [ ] Confirm staged files do not include `reference/system_prompts_leaks`.
- [ ] Confirm no frontend/mobile files are staged.
- [ ] Confirm no unintended `command_router.py` diff.
- [ ] Confirm no prompt bodies are copied into diagnostics docs.
- [ ] Confirm `.gitignore` contains `reference/system_prompts_leaks/`.

## Pre-Push Checks

- [ ] Run the prompt-runtime unittest suite.
- [ ] Run the prompt runtime CLI in pretty mode.
- [ ] Run the prompt runtime CLI in compact mode.
- [ ] Run the prompt runtime CLI with `--check`.
- [ ] Run legacy terminal smoke.
- [ ] Run runtime-flag terminal smoke.
- [ ] Run `py_compile` for prompt-runtime modules.

## Go / No-Go

Go when:

- tests and CLI checks pass
- runtime prompts are off by default
- rollback is documented
- review confirms no public API exposure

No-go when:

- any prompt body appears in status/CLI output
- reference prompt files are staged
- command routing or automation behavior changes unexpectedly
- runtime prompts become default-on
