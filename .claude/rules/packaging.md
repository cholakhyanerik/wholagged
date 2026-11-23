---
paths:
  - "pyproject.toml"
  - "uv.lock"
  - ".python-version"
  - "src/wholagged/__init__.py"
---

# Packaging, version and names

## Version and dependencies
- The version lives in `pyproject.toml` and `__init__.__version__`; a test fails if they differ.
- Bump with `uv version --bump patch|minor`, then set the same `__version__`.
- Dependencies: `uv add <pkg>` / `uv add --dev <pkg>`. Never hand-edit the lists.
- The `[build-system]` range (`uv_build>=<uv>,<next minor>`) is the one table edited by hand (`update-deps`).
- `uv_build` ignores `.gitignore`: `source-exclude` keeps secrets and junk out of the package.

## Names
- The UI and the User-Agent use `APP_NAME` from `__init__.py`; never hard-code the name.
- `wholagged` is the command. `dota-netcheck` is a deprecated alias for the same `main`: keep it working
  (`test_both_commands_are_installed`).

## Pitfalls
- After renaming the distribution or a script, `uv run` (inexact sync) installs the new one next to the old
  one, and the next `uv sync` (exact) removes the old one with every script both list.
  - Run `uv sync` before any `uv run` after such a rename.
  - Repair with `uv sync --reinstall-package wholagged`.
- This shell has `.venv\Scripts` on PATH, so `uv run <cmd>` in another checkout silently falls back to
  this venv's script. Take it off PATH when reproducing install problems elsewhere.
