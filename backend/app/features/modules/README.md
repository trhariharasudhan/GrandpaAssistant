# Compatibility Alias Modules

This folder exists for backward compatibility with legacy imports like:

`from modules.task_module import ...`

Each file here should remain a thin alias that forwards to the real domain module
inside `backend/app/features/<domain>/`.

## Rule

- Do not add new business logic in this folder.
- Add or update real implementation in domain folders such as
  `productivity/`, `system/`, `automation/`, `intelligence/`, etc.
