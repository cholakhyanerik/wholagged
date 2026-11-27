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
  Move it together with the `setup-uv` pin: `release.yml` builds `--offline`, so it fails once CI's uv is
  outside the range, rather than downloading a `uv_build` into the release.
- `uv_build` ignores `.gitignore`: `source-exclude` keeps secrets and junk out of the package.

## Names
- The UI and the User-Agent use `APP_NAME` from `__init__.py`; never hard-code the name.
- `wholagged` is the command. `dota-netcheck` is a deprecated alias for the same `main`: keep it working
  (`test_both_commands_are_installed`).

## PyPI
- Published by `.github/workflows/release.yml` (`.claude/rules/ci.md`). `[project.urls]` gives the PyPI
  page its links: the README's relative links don't work there.
- `wholagged` is on PyPI, so the name is ours; its publisher is `release.yml` + environment `pypi`, with no
  API token. To publish: `gh release create vX.Y.Z --verify-tag` on a task's tag. A tag alone uploads nothing.
- Docs may say `uv tool install wholagged` / `uvx wholagged`; the alias only as
  `uvx --from wholagged dota-netcheck` until `dota-netcheck` is reserved too (WL-102).

## Pitfalls
- After renaming the distribution or a script, `uv run` (inexact sync) installs the new one next to the old
  one, and the next `uv sync` (exact) removes the old one with every script both list.
  - Run `uv sync` before any `uv run` after such a rename.
  - Repair with `uv sync --reinstall-package wholagged`.
- This shell has `.venv\Scripts` on PATH, so `uv run <cmd>` in another checkout silently falls back to
  this venv's script. Take it off PATH when reproducing install problems elsewhere.
- uv 0.13 writes a normalised `pyproject.toml` into the sdist and keeps the original next to it as
  `pyproject.toml.orig` (like Cargo): expected, and only our own comments are in it.
